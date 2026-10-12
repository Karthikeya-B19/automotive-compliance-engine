"""Capture an actual Ollama generation through the production orchestrator."""
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import sys
import time
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rag.orchestrator import review_code


def main():
    output=Path(__file__).resolve().parents[1]/'Evaluation_Results'/'rag_evidence'
    output.mkdir(parents=True,exist_ok=True)
    try:
        response=requests.get('http://localhost:11434/api/tags',timeout=5)
        response.raise_for_status(); models=response.json()
    except Exception as exc:
        models=dict(unavailable=type(exc).__name__)
    cases=[]
    for name,source in [
        ('division_zero','int rpm_rate(int rpm) { return rpm / 0; }'),
        ('unbounded_copy','void diagnostic_name(const char *request) { char name[8]; strcpy(name, request); }'),
        ('no_supported_candidate','int rpm_rate(int rpm) { return rpm / 2; }'),
    ]:
        start=time.perf_counter(); result=review_code(source,file_name=name+'.c')
        cases.append(dict(case=name,source=source,duration_seconds=round(time.perf_counter()-start,3),
                          actual_llm_generation=result['review_mode']=='rag-assisted',result=result))
        print(f"{name}: {result['review_mode']} citation={result.get('citation_validation')}",flush=True)
        (output/'live_generation.json').write_text(json.dumps(dict(generated_at=datetime.now(timezone.utc).isoformat(),
            local_models=models,cases=cases,
            implementation_sha256={name:hashlib.sha256((output.parents[1]/name).read_bytes()).hexdigest()
                for name in ['src/rag/orchestrator.py','src/rag/automotive_retrieval.py']}),indent=2),encoding='utf-8')
    return 0 if any(c['actual_llm_generation'] for c in cases) else 1


if __name__=='__main__': raise SystemExit(main())
