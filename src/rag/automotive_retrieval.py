"""Local rule-card retrieval with an auditable applicability gate.

Synthetic rules are project guidance, never represented as MISRA/ISO clauses.
Dense retrieval is optional. Reciprocal rank fusion combines independent ranks.
"""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
from src.analysis.automotive_checks import RULES

ROOT = Path(__file__).resolve().parents[2]
CARD_PATH = ROOT / 'data' / 'standards' / 'automotive_rule_cards.json'
LEGACY_IDS = {
    'Unbounded input function': 'AUTO-GETS',
    'Potential unbounded string copy': 'AUTO-STRCPY',
    'Potential unbounded string concatenation': 'AUTO-STRCAT',
    'Potential unbounded formatted write': 'AUTO-SPRINTF',
    'Possible null-pointer dereference': 'AUTO-NULL',
    'Allocated resource may not be released': 'AUTO-LEAK',
    'Switch statement has no default branch': 'AUTO-DEFAULT',
}


def default_cards():
    cards = []
    for rule, (title, category, severity, cwe, action) in RULES.items():
        cards.append(dict(rule_id=rule, title=title, category=category, text=action,
                          cwe=cwe, severity=severity))
    for title, rule in LEGACY_IDS.items():
        cards.append(dict(rule_id=rule, title=title, category='C/C++ safety',
                          text={
                              'AUTO-GETS': 'Avoid gets because it cannot enforce a destination bound.',
                              'AUTO-STRCPY': 'For strcpy, prove destination capacity and source length including the terminator.',
                              'AUTO-STRCAT': 'For strcat, prove remaining destination capacity before appending.',
                              'AUTO-SPRINTF': 'Use a bounded formatted write and inspect the return value for truncation.',
                              'AUTO-NULL': 'Do not dereference a null pointer. Check validity and define failure behaviour.',
                              'AUTO-LEAK': 'Define allocation ownership and release resources on all applicable exit paths.',
                              'AUTO-DEFAULT': 'Give a switch a defined default or documented handling of unexpected state.',
                          }[rule]))
    for card in cards:
        card.update(origin='synthetic-project-guidance', version='2.0', language=['C', 'C++'],
                    domain='automotive-embedded', authority='Advisory project rule, not a MISRA or ISO clause',
                    assumptions=['32-bit int target for shift checks', 'Heuristic candidate requires human confirmation'])
        if card['rule_id'] == 'AUTO-CAN-DLC':
            card['assumptions'] = ['Field can_dlc denotes classical CAN length', 'CAN FD needs a separate protocol profile']
    return cards


def load_cards():
    cards = json.loads(CARD_PATH.read_text(encoding='utf-8')) if CARD_PATH.exists() else default_cards()
    ids = [c['rule_id'] for c in cards]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate rule card IDs')
    for card in cards:
        if card.get('origin') != 'synthetic-project-guidance' or not card.get('text'):
            raise ValueError('Invalid or unlabelled project rule card')
    return cards


def tokens(text):
    return re.findall(r'[a-z][a-z0-9_]+', text.casefold())


def lexical_scores(query, cards):
    docs = [tokens(c['title'] + ' ' + c['text'] + ' ' + c['category']) for c in cards]
    avg = sum(map(len, docs)) / max(len(docs), 1)
    query_tokens = set(tokens(query))
    document_frequencies = Counter(token for doc in docs for token in set(doc))
    scores = []
    for doc in docs:
        counts = Counter(doc); score = 0.0
        for token in query_tokens:
            freq = counts[token]
            df = document_frequencies[token]
            idf = math.log(1 + (len(docs) - df + .5)/(df + .5))
            score += idf * freq * 2.5 / (freq + 1.5 * (.25 + .75 * len(doc)/max(avg, 1)))
        scores.append(score)
    return scores


@lru_cache(maxsize=2)
def dense_index(corpus_json):
    # Cache both success and unavailability. Review never downloads a model.
    try:
        from src.ingestion.ingest import LocalSentenceTransformerEmbeddings
        model = LocalSentenceTransformerEmbeddings()
        cards = json.loads(corpus_json)
        vectors = model.embed_documents([c['title'] + ' ' + c['text'] for c in cards])
        return model, vectors, None
    except Exception as exc:
        return None, None, type(exc).__name__


@lru_cache(maxsize=1024)
def _retrieve_cached(query, corpus_json, dense, k):
    cards = json.loads(corpus_json)
    lexical = lexical_scores(query, cards)
    ranks = [sorted(range(len(cards)), key=lambda i: (-lexical[i], cards[i]['rule_id']))]
    dense_scores = None; dense_error = None
    if dense and cards:
        model, vectors, dense_error = dense_index(json.dumps(cards, sort_keys=True))
        if model:
            q = model.embed_query(query)
            dense_scores = [sum(a*b for a,b in zip(q, vector)) for vector in vectors]
            ranks.append(sorted(range(len(cards)), key=lambda i: (-dense_scores[i], cards[i]['rule_id'])))
    fused = {i: sum(1/(60 + rank.index(i) + 1) for rank in ranks) for i in range(len(cards))}
    order = sorted(fused, key=lambda i: (-fused[i], cards[i]['rule_id']))[:k]
    results = []
    for i in order:
        card = cards[i]
        results.append(dict(card, lexical_score=round(lexical[i], 6),
                            dense_score=round(dense_scores[i], 6) if dense_scores else None,
                            fusion_score=round(fused[i], 8),
                            source='automotive_rule_cards.json', chunk_index=i,
                            content=card['title'] + '. ' + card['text'],
                            content_sha256=hashlib.sha256(json.dumps(card, sort_keys=True).encode()).hexdigest()))
    return dict(query=query, strategy='bm25+dense-rrf' if dense_scores else 'bm25',
                dense_error=dense_error, candidates=results)


def retrieve(query, *, cards=None, dense=False, k=5):
    cards = load_cards() if cards is None else cards
    # Round trip prevents a caller modifying a cached evidence trace.
    return json.loads(json.dumps(_retrieve_cached(query, json.dumps(cards, sort_keys=True), dense, k)))


def ground_findings(findings, *, cards=None, dense=False):
    cards = load_cards() if cards is None else cards
    traces = []; grounded = []
    for finding in findings:
        rule = finding.get('rule_id') or LEGACY_IDS.get(finding['title'])
        query = f"{finding['title']} {finding['category']} {finding.get('recommendation', '')}"
        trace = retrieve(query, cards=cards, dense=dense)
        # Applicability requires the detector's typed rule ID. Similarity alone cannot cite a card.
        match = next((c for c in trace['candidates'] if c['rule_id'] == rule), None)
        trace.update(finding_id=finding['finding_id'], expected_rule_id=rule,
                     decision='supported-candidate' if match else 'abstain',
                     cited_rule_id=match['rule_id'] if match else None)
        item = dict(finding)
        if match:
            item['rule_reference'] = match['rule_id'] + ' (synthetic project guidance)'
            item['grounding'] = dict(rule_id=match['rule_id'], source=match['source'],
                                      excerpt=match['text'], content_sha256=match['content_sha256'],
                                      assumptions=match['assumptions'], authority=match['authority'])
        else:
            item['grounding'] = dict(decision='abstain', reason='No retrieved applicable typed rule')
        traces.append(trace); grounded.append(item)
    return grounded, dict(architecture='automotive-evidence-gated-retrieval-v2',
                          corpus_sha256=hashlib.sha256(json.dumps(cards, sort_keys=True).encode()).hexdigest(),
                          corpus_rule_count=len(cards), per_finding=traces,
                          supported_count=sum(t['decision']=='supported-candidate' for t in traces),
                          abstained_count=sum(t['decision']=='abstain' for t in traces),
                          limitations=['Card applicability confirms guidance relevance, not that the candidate is a true defect',
                                       'Synthetic rule cards do not establish MISRA or ISO compliance'])


def validate_model_citation(parsed, context_docs):
    """Fail closed unless a citation and evidence can be found in the supplied context."""
    reference = str(parsed.get('rule_reference', '')).strip()
    evidence = parsed.get('source_evidence') or []
    normalize = lambda s: ' '.join(str(s).casefold().split())
    applicable = [d for d in context_docs if d.get('applicability') == 'supported-candidate']
    matching = [d for d in applicable if normalize(reference) in {normalize(d.get('rule_id', '')), normalize(d.get('citation', ''))}]
    valid = bool(reference and matching and evidence and all(normalize(e) and any(normalize(e) in normalize(d['content']) for d in matching) for e in evidence))
    if not valid:
        parsed = dict(parsed, rule_reference='No applicable rule found', source_evidence=[], confidence='Low',
                      review_summary='Model response failed citation validation. Use the independently reported deterministic candidates.',
                      candidate_root_causes=[], suggested_remediation='No model remediation passed evidence validation.')
    return parsed, dict(accepted=valid, reason='Exact applicable citation and extractive evidence' if valid else 'Unsupported citation or evidence rejected',
                        proposed_rule_reference=reference,
                        proposed_evidence=[str(item)[:1500] for item in evidence[:5]],
                        applicable_rule_ids=[d.get('rule_id') for d in applicable])
