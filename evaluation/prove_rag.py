"""Measure retrieval independently from detector-derived queries, plus grounding controls."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.automotive_retrieval import retrieve, default_cards, ground_findings, validate_model_citation
from src.analysis.static_analyzer import analyze_source

QUERIES = [
    ('received CAN payload says length 12 on a classical eight byte frame', 'AUTO-CAN-DLC'),
    ('engine RPM calculation denominator is the literal zero', 'AUTO-DIV-ZERO'),
    ('destination buffer copied with strcpy from a diagnostic request', 'AUTO-STRCPY'),
    ('uninitialised pointer set to NULL then dereferenced by controller', 'AUTO-NULL'),
    ('timer IRQHandler calls malloc and needs deterministic latency', 'AUTO-ISR-HEAP'),
    ('CAN ISR calls HAL_Delay which blocks servicing interrupts', 'AUTO-ISR-BLOCK'),
    ('table has four elements but code reads element four', 'AUTO-ARRAY-BOUND'),
    ('uint32_t value shifted left by 32 bits', 'AUTO-SHIFT-WIDTH'),
    ('pointer freed twice without allocating again', 'AUTO-DOUBLE-FREE'),
    ('sensor buffer accessed after free', 'AUTO-USE-AFTER-FREE'),
    ('heap allocation ownership has no release on exit', 'AUTO-LEAK'),
    ('state switch misses a default safe state', 'AUTO-DEFAULT'),
    ('printf receives untrusted text as its format argument', 'AUTO-FORMAT'),
    ('watchdog task spins forever in an empty while loop', 'AUTO-BUSY-WAIT'),
    ('function calls itself and consumes an unbounded stack', 'AUTO-RECURSION'),
    ('embedded service invokes shell using system', 'AUTO-SHELL'),
    ('if statement assigns a mode instead of comparing', 'AUTO-ASSIGN-COND'),
    ('sprintf writes formatted telemetry without destination capacity', 'AUTO-SPRINTF'),
    ('strcat appends external diagnostic string without checking remaining capacity', 'AUTO-STRCAT'),
    ('gets reads input without a destination bound', 'AUTO-GETS'),
]


def run():
    output=Path(__file__).resolve().parents[1]/'Evaluation_Results'/'rag_evidence'
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for query, expected in QUERIES:
        row=dict(query=query, expected_rule=expected, strategies={})
        for dense in (False,True):
            start=time.perf_counter(); result=retrieve(query,dense=dense,k=5)
            ids=[c['rule_id'] for c in result['candidates']]
            row['strategies']['hybrid' if dense else 'lexical']=dict(
                actual_strategy=result['strategy'], top_ids=ids,
                rank=ids.index(expected)+1 if expected in ids else None,
                seconds=round(time.perf_counter()-start,4), trace=result)
        rows.append(row)
    findings=analyze_source('int f(int rpm){return rpm / 0;}')[1]
    _, normal=ground_findings(findings,dense=True)
    _, removed=ground_findings(findings,cards=[c for c in default_cards() if c['rule_id']!='AUTO-DIV-ZERO'])
    _, unrelated=ground_findings(findings,cards=[c for c in default_cards() if c['rule_id']=='AUTO-NULL'])
    doc=dict(rule_id='AUTO-DIV-ZERO',content='Validate the denominator.',applicability='supported-candidate')
    _, forged=validate_model_citation(dict(rule_reference='MISRA 999',source_evidence=['invented']),[doc])
    summary=dict(generated_at=datetime.now(timezone.utc).isoformat(),query_count=len(rows),
                 labelled_by='Project author, synthetic advisory-rule applicability labels',
                 corpus_rule_count=len(default_cards()), controls=dict(
                     present_rule_supported=normal['supported_count']==1,
                     deleted_rule_abstains=removed['abstained_count']==1,
                     unrelated_rule_abstains=unrelated['abstained_count']==1,
                     forged_model_citation_rejected=not forged['accepted']))
    for strategy in ('lexical','hybrid'):
        ranks=[r['strategies'][strategy]['rank'] for r in rows]
        summary[strategy]=dict(recall_at_5=sum(r is not None for r in ranks)/len(ranks),
                               top1_accuracy=sum(r==1 for r in ranks)/len(ranks),
                               mrr_at_5=sum(1/r if r else 0 for r in ranks)/len(ranks),
                               actual_strategies=sorted({r['strategies'][strategy]['actual_strategy'] for r in rows}))
    (output/'retrieval_results.json').write_text(json.dumps(dict(summary=summary,cases=rows),indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__': run()
