"""Run tests and independent CLI/compile checks, then preserve machine-readable proof."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Evaluation_Results'


def main():
    OUT.mkdir(exist_ok=True)
    test_run=subprocess.run([sys.executable,'-m','pytest','-q','--junitxml='+str(OUT/'tests_v2.0.xml')],cwd=ROOT,capture_output=True,text=True)
    (OUT/'CB.AI.U4AID23109_TestLog_v2.0.txt').write_text(test_run.stdout+test_run.stderr,encoding='utf-8')
    tree=ET.parse(OUT/'tests_v2.0.xml')
    cases=[dict(name=c.get('name'),module=c.get('classname'),seconds=c.get('time'),
                passed=c.find('failure') is None and c.find('error') is None,
                skipped=c.find('skipped') is not None) for c in tree.iter('testcase')]
    cli=[]
    for sample,expected in [('automotive_ecu_demo',1),('clean_speed_monitor',0)]:
        dest=OUT/(sample+'_v2.0.sarif')
        run=subprocess.run([sys.executable,'tools/ci_review.py','demo/repository/'+sample,'--format','sarif','--output',str(dest),'--fail-on','High'],cwd=ROOT,capture_output=True,text=True)
        parsed=json.loads(dest.read_text())
        cli.append(dict(sample=sample,expected_exit=expected,actual_exit=run.returncode,
                        result_count=len(parsed['runs'][0]['results']),passed=run.returncode==expected))
    # An independent compiler warning supports one isolated synthetic C defect.
    compiler=shutil.which('gcc')
    compile_proof=dict(status='unavailable')
    if compiler:
        run=subprocess.run([compiler,'-x','c','-fsyntax-only','-Wall','-Wextra','-'],
                           input='int rpm_rate(int rpm){return rpm / 0;}\n',capture_output=True,text=True)
        compile_proof=dict(compiler=compiler,status='executed',exit_code=run.returncode,
                           diagnostic=run.stderr,division_warning='division by zero' in run.stderr.lower(),
                           scope='Isolated synthetic host snippet, not a build of ECU firmware')
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'src').rglob('*.py')}
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),
                summary=dict(test_cases=len(cases),passed=sum(c['passed'] and not c['skipped'] for c in cases),
                             failed=sum(not c['passed'] for c in cases),skipped=sum(c['skipped'] for c in cases),
                             cli_gates_passed=all(c['passed'] for c in cli)),
                test_cases=cases,cli_checks=cli,compiler_cross_check=compile_proof,
                implementation_sha256=hashes,
                evidence_scope=['Component tests and API integration','Actual CLI SARIF and severity exit codes',
                                'Independent compiler warning','Live LLM and public corpus results are separate evidence files'])
    (OUT/'component_evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],indent=2)); print(test_run.stdout)
    return 0 if test_run.returncode==0 and all(c['passed'] for c in cli) else 1


if __name__=='__main__': raise SystemExit(main())
