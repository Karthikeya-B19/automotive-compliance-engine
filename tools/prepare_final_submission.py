"""Build, verify and seal the final individual submission; never overwrite prior releases."""
from datetime import datetime, timezone
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
REG='CB.AI.U4AID23109'
VERSION='3.1'
NAME='AmritaVishwaVidyapeetham_KarthikeyaBellapukonda_CB.AI.U4AID23109_CS4_AIML'
PACKAGE=ROOT/f'submission_v{VERSION}'/NAME
FOLDERS=['Synopsis','Input_Data','Code','Model_Prompts_Config','Evaluation_Results','Documentation','Video','Declarations']
PENDING=[]
COMPLIANCE_NOTES=[
    'Student reports an approved synopsis is held separately; that approval was not independently inspected or bundled.',
    'At the student\'s explicit direction, signature collection/verification is outside this packaging task; supplied forms remain unsigned.',
    'At the student\'s explicit direction, the existing October 7 recording is retained. It shows the earlier implementation, not the revised RAG/UI.',
    'The assessment instructions require signed declarations and a submitted-version demonstration. User packaging choices do not establish compliance with those requirements.',
    'Encrypted storage, network isolation and evaluator arrangements remain institutional/student responsibilities, not checks completed by this package.',
]
CURRENT_EVIDENCE=['component_evidence.json','tests_v2.0.xml','CB.AI.U4AID23109_TestLog_v2.0.txt',
    'automotive_ecu_demo_v2.0.sarif','clean_speed_monitor_v2.0.sarif','CB.AI.U4AID23109_EvidenceAudit_v3.0.json']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')


def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,destination)


def copy_tree(source,destination):
    def ignore(directory,names):
        return [n for n in names if n in {'__pycache__','.pytest_cache','.venv','.git','reviews.db','VIDEO_PLACEHOLDER.txt'}
                or n.endswith(('.pyc','.db','.sqlite3')) or (n.startswith('.env') and n!='.env.example')]
    shutil.copytree(source,destination,ignore=ignore)


def archive_tree(source,destination):
    if destination.exists(): raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(source.rglob('*')):
            if path.is_file(): z.write(path,path.relative_to(source).as_posix())
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None: raise ValueError('Archive CRC failure')


def build():
    if PACKAGE.exists(): raise FileExistsError('Final release already exists. Preserve it and choose a new version.')
    for folder in FOLDERS: (PACKAGE/folder).mkdir(parents=True)
    code=PACKAGE/'Code'
    for folder in ['src','tests','evaluation','tools','demo','docker','docs','.streamlit','.github']:
        copy_tree(ROOT/folder,code/folder)
    for name in ['run.py','requirements.txt','pytest.ini','.env.example','.gitignore','.gitattributes','README.md','USER_GUIDE.md','create_dummy_data.py']:
        copy(ROOT/name,code/name)
    copy_tree(ROOT/'data/standards',code/'data/standards')
    for name in CURRENT_EVIDENCE: copy(ROOT/'Evaluation_Results'/name,code/'Evaluation_Results'/name)
    for folder in ['public_benchmark','rag_evidence','ecu_mutations']:
        copy_tree(ROOT/'Evaluation_Results'/folder,code/'Evaluation_Results'/folder)
    # Source docs keep their native relative links. Evaluator-facing copies receive artifact names.
    documentation={'USER_GUIDE.md':'UserGuide','docs/RAG_PROOF_GUIDE.md':'RAGProofGuide',
        'docs/FILE_REFERENCE.md':'SourceFileReference','docs/EVALUATION_GUIDE.md':'EvaluationGuide',
        'docs/FINAL_SUBMISSION_REPORT_ADDENDUM.md':'RubricAndReleaseSupplement','docs/SETUP_AND_DEPENDENCIES.md':'SetupAndDependencies'}
    for original,label in documentation.items():
        copy(ROOT/original,PACKAGE/'Documentation'/f'{REG}_{label}_v3.0.md')
    report=(ROOT/'docs/TECHNICAL_REPORT_v2.md').read_text(encoding='utf-8').replace(
        'Version 2.0, 12 October 2026.','Report version 3.0, 16 October 2026; retained benchmark/model observations are dated 12 October.')
    report += '\n\n'+(ROOT/'docs/FINAL_SUBMISSION_REPORT_ADDENDUM.md').read_text(encoding='utf-8')
    (PACKAGE/'Documentation'/f'{REG}_TechnicalReportSource_v3.0.md').write_text(report,encoding='utf-8')
    artifacts={'TechnicalReport_v3.0.pdf':'Documentation','Synopsis_v3.0.pdf':'Synopsis',
        'AcademicIntegrityDeclaration_v3.0.pdf':'Declarations','AIToolUsageDeclaration_v3.0.pdf':'Declarations',
        'RAGEvidencePresentation_v2.0.pptx':'Documentation','RAGProof_v2.1.pptx':'Documentation'}
    for artifact,folder in artifacts.items():
        filename=f'{REG}_{artifact}'
        copy(ROOT/'deliverables'/filename,PACKAGE/folder/filename)
        copy(ROOT/'deliverables'/filename,code/'deliverables'/filename)
    for original,label in [('MODEL_CONFIG.md','ModelConfig'),('PROMPT_GUARDRAILS.md','PromptGuardrails')]:
        copy(ROOT/'docs'/original,PACKAGE/'Model_Prompts_Config'/f'{REG}_{label}_v3.0.md')
    copy(ROOT/'data/standards/automotive_rule_cards.json',PACKAGE/'Model_Prompts_Config'/f'{REG}_AdvisoryRuleCorpus_v3.0.json')
    copy(ROOT/'docs/THIRD_PARTY_NOTICE.md',PACKAGE/'Declarations'/f'{REG}_ThirdPartyNotice_v3.0.md')
    copy(ROOT/'docs/FINAL_SUBMISSION_GUIDE.md',PACKAGE/f'{REG}_SubmissionGuide_v{VERSION}.md')
    for original,label in [('Instructions1.pdf','AssessmentInstructionsPart1'),('Instructions2.pdf','FacultyEvaluationChecklist'),
                           ('Evaluation_Rubrics.pdf','EvaluationRubric'),('Automotive_Engineering_AI_Project_Case_Studies.pdf','CaseStudyBrief')]:
        copy(ROOT/original,PACKAGE/'Documentation/Reference_Guidelines'/f'{REG}_{label}_v1.0.pdf')
    catalog=[]
    for original in sorted((ROOT/'demo').glob('*.zip')):
        copy(original,PACKAGE/'Input_Data'/original.name)
        catalog.append(dict(file=original.name,kind='synthetic-demonstration',sha256=sha(original)))
    for original in sorted((ROOT/'Evaluation_Results/ecu_mutations').glob('*.zip')):
        filename=f'{REG}_{original.stem}_v2.0.zip'
        copy(original,PACKAGE/'Input_Data'/filename)
        catalog.append(dict(file=filename,kind='controlled-mutant' if '_mutant' in filename else 'upstream-baseline',sha256=sha(original)))
    copy(ROOT/'demo/compiler_warnings.txt',PACKAGE/'Input_Data'/f'{REG}_CompilerWarnings_v1.0.txt')
    write_json(PACKAGE/'Input_Data'/f'{REG}_InputCatalog_v3.0.json',dict(
        scope='Authorized static-analysis educational examples. Never flash to hardware.',archives=catalog))
    evidence_map={'component_evidence.json':'ComponentEvidence','public_benchmark/summary.json':'PublicBenchmarkSummary',
        'rag_evidence/retrieval_results.json':'RAGRetrievalResults','rag_evidence/live_generation.json':'RAGActualGeneration',
        'rag_evidence/control_interventions.json':'RAGControlInterventions','ecu_mutations/results.json':'ECUMutationResults',
        'CB.AI.U4AID23109_EvidenceAudit_v3.0.json':'EvidenceAudit'}
    for original,label in evidence_map.items():
        copy(ROOT/'Evaluation_Results'/original,PACKAGE/'Evaluation_Results'/f'{REG}_{label}_v3.0.json')
    archive_tree(code/'Evaluation_Results',PACKAGE/'Evaluation_Results'/f'{REG}_RawEvaluationEvidence_v3.0.zip')
    copy(ROOT/'docs/VIDEO_SCRIPT.md',PACKAGE/'Video'/f'{REG}_RecordingScript_v3.0.md')
    historical=ROOT/'.build/submission_audit/CB.AI.U4AID23109_HistoricalDemo_v1.0.mp4'
    copy(historical,PACKAGE/'Video'/historical.name)
    write_json(PACKAGE/'Video'/f'{REG}_RecordingProvenance_v3.0.json',dict(
        source_file='Tata recording.mp4',source_sha256=sha(ROOT/'Tata recording.mp4'),
        packaged_file=historical.name,packaged_sha256=sha(historical),duration_seconds=435.77,
        source_created_at='2026-10-07T15:04:04Z',dimensions=[2558,1388],fps=30,
        processing='Whole recording re-encoded H.264 CRF20 and AAC128k, no cuts, same resolution/fps; original unchanged.',
        review='Sampled frames at 25, 120, 260 and 410 seconds show the older three-tab UI.',
        current_version_demonstrated=False,student_direction='Use this existing recording; no replacement requested.',
        guideline_exception='The recording predates the submitted RAG/UI revision.'))
    (PACKAGE/'Video'/f'{REG}_RecordingReview_v3.0.md').write_text(
        '# Recording review\n\nThe included historical recording is 7 minutes 15.77 seconds and meets duration only. '
        'Its October 7 UI predates the submitted RAG pipeline and Verification lab. It must not be presented as current-version evidence. '
        'The student explicitly chose to retain this recording, with no replacement requested. '
        'This choice does not demonstrate the updated RAG/UI or satisfy the submitted-version video requirement by itself. '
        'The recording script remains as optional reference. The original file remains untouched outside the package.\n',encoding='utf-8')
    print(PACKAGE)


def available_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def verify():
    import requests
    code=PACKAGE/'Code'
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),checks={},sample_uploads=[],pending_actions=PENDING,compliance_notes=COMPLIANCE_NOTES)
    with tempfile.TemporaryDirectory(prefix='techpulse-final-check-') as scratch:
        env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',REVIEW_DATABASE=str(Path(scratch)/'reviews.db'))
        tests=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider'],cwd=code,env=env,capture_output=True,text=True)
        (PACKAGE/'Evaluation_Results'/f'{REG}_PackagedTestLog_v3.0.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
        report['checks']['packaged_tests_pass']=tests.returncode==0
        report['pytest_summary']=next((line for line in tests.stdout.splitlines() if re.search(r'\d+ passed',line)),'No passing summary')
        api_port=available_port();ui_port=available_port()
        while ui_port==api_port: ui_port=available_port()
        key=secrets.token_urlsafe(32)
        env.update(REVIEW_API_KEY=key,REVIEW_AUTH_USER='final-evaluator',REVIEW_REQUIRE_AUTH='true',
            REVIEW_REPOSITORY_PERMISSIONS=json.dumps({'final-evaluator':{'repositories':{'uploaded-repository':['*']}}}),
            REVIEW_API_URL=f'http://127.0.0.1:{api_port}/api/v1/review')
        log_file=open(Path(scratch)/'services.log','w',encoding='utf-8')
        processes=[]
        try:
            for command in [[sys.executable,'-m','uvicorn','src.api.main:app','--host','127.0.0.1','--port',str(api_port)],
                [sys.executable,'-m','streamlit','run','src/ui/app.py','--server.address','127.0.0.1','--server.port',str(ui_port),'--server.headless','true','--browser.gatherUsageStats','false']]:
                processes.append(subprocess.Popen(command,cwd=code,env=env,stdout=log_file,stderr=subprocess.STDOUT))
            api=f'http://127.0.0.1:{api_port}'
            headers={'X-API-Key':key}
            def wait(url):
                for _ in range(150):
                    try:
                        response=requests.get(url,timeout=1)
                        if response.status_code==200: return True
                    except requests.RequestException: pass
                    if any(p.poll() is not None for p in processes): return False
                    time.sleep(.2)
                return False
            report['checks']['api_health']=wait(api+'/health')
            report['checks']['streamlit_health']=wait(f'http://127.0.0.1:{ui_port}/_stcore/health')
            report['checks']['authentication_rejects_missing_key']=requests.get(api+'/api/v1/reviews',timeout=10).status_code==401
            labels=json.loads((code/'Evaluation_Results/ecu_mutations/results.json').read_text(encoding='utf-8'))['cases']
            labels={f"{REG}_{x['case_id']}_mutant_v2.0.zip":x for x in labels}
            last=None
            for archive in sorted((PACKAGE/'Input_Data').glob('*.zip')):
                response=requests.post(api+'/api/v1/repository-review',headers=headers,json=dict(
                    repository_id='uploaded-repository',archive_name=archive.name,
                    archive_base64=base64.b64encode(archive.read_bytes()).decode(),use_rag=False),timeout=30)
                data=response.json()
                row=dict(file=archive.name,http_status=response.status_code,
                    source_files=data.get('repository_summary',{}).get('source_file_count'),
                    finding_count=len(data.get('findings',[])))
                if archive.name in labels:
                    label=labels[archive.name]
                    row['expected_mutation_at_injected_line']=any(f['title']==label['expected_title'] and f['line']==label['injected_line'] for f in data.get('findings',[]))
                report['sample_uploads'].append(row)
                if response.status_code==200: last=data
            report['checks']['all_19_manual_archives_pass_http']=len(report['sample_uploads'])==19 and all(x['http_status']==200 for x in report['sample_uploads'])
            mutations=[x for x in report['sample_uploads'] if 'expected_mutation_at_injected_line' in x]
            report['checks']['all_8_manual_mutations_match_expected_line']=len(mutations)==8 and all(x['expected_mutation_at_injected_line'] for x in mutations)
            pairs={}
            for row in report['sample_uploads']:
                if '_baseline_' in row['file'] or '_mutant_' in row['file']:
                    group=row['file'].replace('_baseline_','_pair_').replace('_mutant_','_pair_')
                    pairs.setdefault(group,{})['baseline' if '_baseline_' in row['file'] else 'mutant']=row['finding_count']
            report['checks']['all_8_pairs_add_one_candidate']=len(pairs)==8 and all(x['mutant']==x['baseline']+1 for x in pairs.values())
            if last:
                saved=requests.get(api+'/api/v1/reviews/'+last['review_id'],headers=headers,timeout=10)
                report['checks']['saved_review_retrievable']=saved.status_code==200
                disposition=requests.patch(api+'/api/v1/reviews/'+last['review_id']+'/disposition',headers=headers,
                    json=dict(status='Needs changes',reviewer='Automated smoke test',notes='Ephemeral verification only; not a real engineering approval.'),timeout=10)
                report['checks']['human_disposition_endpoint']=disposition.status_code==200
            unsafe=io.BytesIO()
            with zipfile.ZipFile(unsafe,'w') as z: z.writestr('../bad.c','int x;')
            rejected=requests.post(api+'/api/v1/repository-review',headers=headers,json=dict(repository_id='uploaded-repository',
                archive_name='traversal.zip',archive_base64=base64.b64encode(unsafe.getvalue()).decode(),use_rag=False),timeout=10)
            report['checks']['traversal_rejected_http']=rejected.status_code==422
            denied=requests.post(api+'/api/v1/repository-review',headers=headers,json=dict(
                repository_id='forbidden-repository',archive_name=archive.name,
                archive_base64=base64.b64encode(archive.read_bytes()).decode(),use_rag=False),timeout=10)
            report['checks']['unauthorized_repository_rejected']=denied.status_code==403
        finally:
            for process in processes:
                if process.poll() is None: process.terminate()
            for process in processes:
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()
            log_file.close()
        copy(Path(scratch)/'services.log',PACKAGE/'Evaluation_Results'/f'{REG}_HTTPServiceLog_v3.0.txt')
    report['checks']['required_folder_set']=set(p.name for p in PACKAGE.iterdir() if p.is_dir())==set(FOLDERS)
    invalid=[]
    for p in PACKAGE.rglob('*'):
        if not p.is_file(): continue
        if p.suffix in {'.pyc','.db','.sqlite3'} or any(x in {'.git','.venv','__pycache__','.pytest_cache'} for x in p.relative_to(PACKAGE).parts) or (p.name.startswith('.env') and p.name!='.env.example'):
            invalid.append(p.relative_to(PACKAGE).as_posix())
    report['checks']['no_private_runtime_artifacts']=not invalid
    report['invalid_runtime_files']=invalid
    bad_names=[]
    for p in PACKAGE.rglob('*'):
        if p.is_file() and p.relative_to(PACKAGE).parts[0]!='Code' and not re.fullmatch(re.escape(REG)+r'_[A-Za-z0-9_]+_v\d+(?:\.\d+)+\.[A-Za-z0-9]+',p.name):
            bad_names.append(p.relative_to(PACKAGE).as_posix())
    report['checks']['evaluator_artifact_names_valid']=not bad_names
    report['invalid_artifact_names']=bad_names
    write_json(PACKAGE/'Evaluation_Results'/f'{REG}_PackageVerification_v{VERSION}.json',report)
    print(json.dumps(report,indent=2))
    if not all(report['checks'].values()): raise SystemExit('Package verification failed; ZIP not sealed.')


def seal():
    verification=PACKAGE/'Evaluation_Results'/f'{REG}_PackageVerification_v{VERSION}.json'
    if not verification.exists() or not all(json.loads(verification.read_text())['checks'].values()):
        raise ValueError('Run and pass --verify before sealing.')
    manifest_path=PACKAGE/f'{REG}_SubmissionManifest_v{VERSION}.json'
    manifest=dict(version=VERSION,prepared_date='2026-10-16',student='Karthikeya Bellapukonda',
        university='Amrita Vishwa Vidyapeetham',register_number=REG,case_study='CS4',submission_type='Individual',
        folders=FOLDERS,status='TECHNICAL_CHECKS_PASSED_USER_ACKNOWLEDGED_EXCEPTIONS',pending_actions=PENDING,compliance_notes=COMPLIANCE_NOTES,
        naming_policy='Evaluator-facing artifacts use register_artifact_version. Native source and archive payload names remain functional.',
        files=[dict(path=p.relative_to(PACKAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
            for p in sorted(PACKAGE.rglob('*')) if p.is_file() and p!=manifest_path])
    write_json(manifest_path,manifest)
    mismatches=[item['path'] for item in manifest['files'] if sha(PACKAGE/item['path'])!=item['sha256']]
    if mismatches: raise ValueError(mismatches)
    destination=PACKAGE.parent/f'{REG}_Submission_v{VERSION}.zip'
    if destination.exists(): raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(PACKAGE.rglob('*')):
            if p.is_file(): z.write(p,NAME+'/'+p.relative_to(PACKAGE).as_posix())
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None: raise ValueError('CRC failure')
        if {n.split('/')[0] for n in z.namelist()}!={NAME}: raise ValueError('Wrong archive root')
        for item in manifest['files']:
            if hashlib.sha256(z.read(NAME+'/'+item['path'])).hexdigest()!=item['sha256']: raise ValueError(item['path'])
    print(json.dumps(dict(folder=str(PACKAGE),zip=str(destination),files=len(manifest['files']),zip_bytes=destination.stat().st_size,
        zip_sha256=sha(destination),status=manifest['status']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');parser.add_argument('--seal',action='store_true')
    args=parser.parse_args()
    if args.verify and args.seal: parser.error('Verify and seal are separate steps.')
    verify() if args.verify else seal() if args.seal else build()
