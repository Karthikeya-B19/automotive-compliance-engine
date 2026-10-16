"""Audit retained measurements and describe the benchmark without relabelling candidates."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Evaluation_Results'


def run():
    records = json.loads((OUT/'public_benchmark/results.json').read_text(encoding='utf-8'))
    summary = json.loads((OUT/'public_benchmark/summary.json').read_text(encoding='utf-8'))
    manifest = [f for r in records for f in r['file_manifest']]
    sizes = sorted(f['bytes'] for f in manifest)
    hashes = Counter(f['sha256'] for f in manifest)
    locations = defaultdict(set)
    for r in records:
        for f in r['file_manifest']:
            locations[f['sha256']].add(r['repository'])
    rag = json.loads((OUT/'rag_evidence/retrieval_results.json').read_text(encoding='utf-8'))
    checks = {
        'distinct_repositories_match': len({r['repository'] for r in records}) == summary['distinct_repositories'] == 100,
        'file_counts_match': len(manifest) == sum(r['files'] for r in records) == summary['files'],
        'line_counts_match': sum(r['lines'] for r in records) == summary['lines'],
        'candidate_counts_match': sum(r['findings'] for r in records) == summary['candidate_findings'],
        'all_repositories_scanned': all(r['status'] == 'scanned' for r in records),
        'source_hashes_present': all(len(f['sha256']) == 64 for f in manifest),
    }
    for label in ('lexical','hybrid'):
        ranks = [c['strategies'][label]['rank'] for c in rag['cases']]
        measured = dict(recall_at_5=sum(x is not None for x in ranks)/len(ranks),
            top1_accuracy=sum(x == 1 for x in ranks)/len(ranks),
            mrr_at_5=sum(1/x if x else 0 for x in ranks)/len(ranks))
        checks[label+'_metrics_recalculate'] = all(abs(v-rag['summary'][label][k]) < 1e-12 for k,v in measured.items())
    evidence_hash_checks = {}
    for name in ['component_evidence.json','public_benchmark/summary.json','rag_evidence/live_generation.json','rag_evidence/control_interventions.json']:
        report=json.loads((OUT/name).read_text(encoding='utf-8'))
        evidence_hash_checks[name] = [p for p,h in report.get('implementation_sha256',{}).items()
            if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != h]
    data = dict(generated_at=datetime.now(timezone.utc).isoformat(), checks=checks,
        implementation_hash_mismatches=evidence_hash_checks,
        corpus_eda=dict(repositories=len(records),source_files=len(manifest),
            extension_counts=dict(Counter(Path(f['path']).suffix.lower() for f in manifest)),
            source_bytes=sum(sizes),file_bytes_min=min(sizes),file_bytes_median=statistics.median(sizes),
            file_bytes_p95=sizes[max(0,round(.95*(len(sizes)-1)))],file_bytes_max=max(sizes),
            unique_content_hashes=len(hashes),duplicate_content_instances=sum(n-1 for n in hashes.values()),
            hashes_shared_between_repositories=sum(len(v)>1 for v in locations.values()),
            exclusion_reasons=dict(Counter(f['reason'] for r in records for f in r['excluded_files'])),
            license_metadata=dict(Counter(str(r.get('license')) for r in records))),
        interpretation=[
            'No supervised model training or train/test split occurs; pretrained models remain frozen.',
            'Duplicate contents remain in the robustness corpus and reduce statistical independence. No accuracy inference uses these counts.',
            'Retrieval queries and advisory rules have author-provided labels; independent expert adjudication and an unseen holdout are absent.',
            'Baseline and mutant files intentionally share source as paired controls, not independent samples.',
            'Embeddings are semantic representations; PCA and supervised feature selection were not used and are not claimed.',
            'The active vector index is an in-memory cached card matrix; persistent FAISS/Chroma integration is not active.',
        ])
    destination = OUT/'CB.AI.U4AID23109_EvidenceAudit_v3.0.json'
    destination.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
    assert all(checks.values()) and not any(evidence_hash_checks.values())


if __name__ == '__main__':
    run()
