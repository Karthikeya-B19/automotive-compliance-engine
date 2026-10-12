"""Create a new v2 submission without replacing previous packages or student artifacts."""
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAME='AmritaVishwaVidyapeetham_KarthikeyaBellapukonda_CB.AI.U4AID23109_CS4_AIML'
REGISTER='CB.AI.U4AID23109'
VERSION='2.0'
PACKAGE=ROOT/f'submission_v{VERSION}'/NAME
PREVIOUS=ROOT/'submission_v1.6'/NAME
REQUIRED=['Synopsis','Input_Data','Code','Model_Prompts_Config','Evaluation_Results','Documentation','Video','Declarations']


def copy_filtered(source,dest):
    def ignore(directory,names):
        return [name for name in names if name in {'__pycache__','.pytest_cache','.venv','.git','reviews.db'} or name.endswith('.pyc')]
    shutil.copytree(source,dest,ignore=ignore,dirs_exist_ok=True)


def main():
    if PACKAGE.exists(): raise FileExistsError('Version 2 package already exists; create a new version rather than overwriting it.')
    for name in REQUIRED: (PACKAGE/name).mkdir(parents=True,exist_ok=True)
    for name in ['Synopsis','Declarations']:
        if (PREVIOUS/name).exists():
            copy_filtered(PREVIOUS/name,PACKAGE/name)
        else:
            (PACKAGE/name/f'{REGISTER}_RequiredStudentDocument_v2.0.txt').write_text('Attach the required student/faculty document here before submission.\n',encoding='utf-8')
    code=PACKAGE/'Code'
    for name in ['src','tests','evaluation','tools','demo','docker','docs','.streamlit','.github']:
        copy_filtered(ROOT/name,code/name)
    for name in ['run.py','requirements.txt','pytest.ini','.env.example','README.md','USER_GUIDE.md','create_dummy_data.py']:
        shutil.copy2(ROOT/name,code/name)
    copy_filtered(ROOT/'data'/'standards',code/'data'/'standards')
    copy_filtered(ROOT/'Evaluation_Results',PACKAGE/'Evaluation_Results')
    for path in (ROOT/'demo').glob('*.zip'): shutil.copy2(path,PACKAGE/'Input_Data'/path.name)
    for path in (ROOT/'Evaluation_Results'/'ecu_mutations').glob('*.zip'):
        shutil.copy2(path,PACKAGE/'Input_Data'/f'{REGISTER}_{path.stem}_v2.0.zip')
    shutil.copy2(ROOT/'demo'/'compiler_warnings.txt',PACKAGE/'Input_Data'/f'{REGISTER}_CompilerWarnings_v2.0.txt')
    docs={'USER_GUIDE.md':'UserGuide','docs/TECHNICAL_REPORT_v2.md':'TechnicalReport',
          'docs/EVALUATION_GUIDE.md':'EvaluationGuide','docs/FILE_REFERENCE.md':'FileReference',
          'docs/GUIDELINE_TRACEABILITY.md':'GuidelineTraceability','docs/SUBMISSION_CHECKLIST.md':'SubmissionChecklist'}
    for source,artifact in docs.items(): shutil.copy2(ROOT/source,PACKAGE/'Documentation'/f'{REGISTER}_{artifact}_v2.0.md')
    for name in ['CB.AI.U4AID23109_TechnicalReport_v2.0.pdf','CB.AI.U4AID23109_RAGEvidencePresentation_v2.0.pptx']:
        shutil.copy2(ROOT/'deliverables'/name,PACKAGE/'Documentation'/name)
    for source,artifact in [('MODEL_CONFIG.md','ModelConfig'),('PROMPT_GUARDRAILS.md','PromptGuardrails')]:
        shutil.copy2(ROOT/'docs'/source,PACKAGE/'Model_Prompts_Config'/f'{REGISTER}_{artifact}_v2.0.md')
    shutil.copy2(ROOT/'data'/'standards'/'automotive_rule_cards.json',PACKAGE/'Model_Prompts_Config'/f'{REGISTER}_AdvisoryRuleCorpus_v2.0.json')
    shutil.copy2(ROOT/'docs'/'VIDEO_SCRIPT.md',PACKAGE/'Video'/f'{REGISTER}_VideoScript_v2.0.md')
    shutil.copy2(ROOT/'docs'/'VIDEO_PLACEHOLDER.txt',PACKAGE/'Video'/f'{REGISTER}_VideoPlaceholder_v2.0.txt')
    shutil.copy2(ROOT/'docs'/'SYNOPSIS_ADDENDUM_v2.md',PACKAGE/'Synopsis'/f'{REGISTER}_SynopsisAddendum_v2.0.md')
    shutil.copy2(ROOT/'docs'/'THIRD_PARTY_NOTICE.md',PACKAGE/'Declarations'/f'{REGISTER}_ThirdPartyNotice_v2.0.md')
    shutil.copy2(ROOT/'docs'/'PACKAGE_README.md',PACKAGE/'README.md')
    manifest=dict(version=VERSION,generated_at=datetime.now(timezone.utc).isoformat(),required_folders=REQUIRED,
                  student='Karthikeya Bellapukonda',register_number=REGISTER,submission_type='Individual',
                  repository='https://github.com/Karthikeya-B19/automotive-compliance-engine',
                  pending_student_actions=['Obtain required faculty signature','Review and sign declaration','Record and add actual demonstration MP4'],
                  naming_note='Evaluator-facing artifacts use register-prefixed versions; importable source and internal machine-readable evidence retain functional filenames.',
                  files=[dict(path=str(p.relative_to(PACKAGE)).replace('\\','/'),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                         for p in sorted(PACKAGE.rglob('*')) if p.is_file()])
    (PACKAGE/f'{REGISTER}_SubmissionManifest_v2.0.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(PACKAGE)


def archive():
    destination=PACKAGE.parent/(NAME+f'_v{VERSION}.zip')
    if destination.exists(): raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(PACKAGE.rglob('*')):
            if path.is_file() and path.suffix not in {'.db','.pyc'} and not any(part in {'__pycache__','.pytest_cache','.venv'} for part in path.parts):
                z.write(path,NAME+'/'+str(path.relative_to(PACKAGE)).replace('\\','/'))
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert {n.split('/')[0] for n in names}=={NAME}
        assert all(any(n.startswith(NAME+'/'+folder+'/') for n in names) for folder in REQUIRED)
        assert not any('__pycache__' in n or n.endswith(('.pyc','.db')) or '/.venv/' in n for n in names)
    print(destination)
    print('SHA256 '+hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--archive',action='store_true');parser.add_argument('--version',default='2.0');args=parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',args.version): parser.error('Version must be numeric, for example 2.0.1')
    VERSION=args.version
    PACKAGE=ROOT/f'submission_v{VERSION}'/NAME
    archive() if args.archive else main()
