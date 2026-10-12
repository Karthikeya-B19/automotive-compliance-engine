"""Export inspectable, same-query corpus interventions without changing app data."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis.static_analyzer import analyze_source
from src.rag.automotive_retrieval import load_cards, ground_findings, validate_model_citation


def run():
    source = 'int rpm_rate(int rpm) { return rpm / 0; }'
    findings = analyze_source(source)[1]
    cards = load_cards()
    variants = {
        'relevant_present': cards,
        'relevant_deleted': [c for c in cards if c['rule_id'] != 'AUTO-DIV-ZERO'],
        'unrelated_only': [c for c in cards if c['rule_id'] == 'AUTO-NULL'],
    }
    cases = []
    for name, corpus in variants.items():
        grounded, trace = ground_findings(findings, cards=corpus, dense=False)
        cases.append(dict(case=name, input_findings=findings, grounded_findings=grounded, trace=trace))
    card = next(c for c in cards if c['rule_id'] == 'AUTO-DIV-ZERO')
    context = [dict(rule_id=card['rule_id'], content=card['title']+'. '+card['text'],
                    applicability='supported-candidate')]
    proposals = {
        'valid_quote': dict(rule_reference=card['rule_id'], source_evidence=[card['text']]),
        'forged_id': dict(rule_reference='MISRA 999', source_evidence=[card['text']]),
        'invented_quote': dict(rule_reference=card['rule_id'], source_evidence=['Invented guidance absent from context.']),
        'empty_evidence': dict(rule_reference=card['rule_id'], source_evidence=[]),
    }
    citation_cases = []
    for name, proposed in proposals.items():
        validated, decision = validate_model_citation(proposed, context)
        citation_cases.append(dict(case=name, proposal=proposed, context=context,
                                    decision=decision, validated_output=validated))
    checks = dict(
        relevant_present_supports=cases[0]['trace']['supported_count'] == 1,
        relevant_deleted_abstains=cases[1]['trace']['abstained_count'] == 1,
        unrelated_only_abstains=cases[2]['trace']['abstained_count'] == 1,
        same_query= len({c['trace']['per_finding'][0]['query'] for c in cases}) == 1,
        same_input_findings=all(c['input_findings'] == findings for c in cases),
        valid_quote_accepted=citation_cases[0]['decision']['accepted'],
        forged_id_rejected=not citation_cases[1]['decision']['accepted'],
        invented_quote_rejected=not citation_cases[2]['decision']['accepted'],
        empty_evidence_rejected=not citation_cases[3]['decision']['accepted'],
    )
    evidence = dict(generated_at=datetime.now(timezone.utc).isoformat(), source=source,
        strategy='bm25 in every corpus variant to isolate the corpus intervention',
        checks=checks, corpus_cases=cases, citation_cases=citation_cases,
        implementation_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in ['src/analysis/static_analyzer.py','src/rag/automotive_retrieval.py']},
        scope='Programmatic retrieval/validator controls. These proposals do not claim actual LLM generation.')
    destination=ROOT/'Evaluation_Results/rag_evidence/control_interventions.json'
    destination.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2))
    assert all(checks.values())


if __name__ == '__main__':
    run()
