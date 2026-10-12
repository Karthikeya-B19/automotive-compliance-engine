"""Controlled mutations inside real open-source ECU functions. Never flash or execute firmware."""
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis.static_analyzer import analyze_source, _function_ranges
from src.analysis.lexical import mask_non_code
from src.analysis.repository_analyzer import analyze_repository_zip

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Evaluation_Results'/'ecu_mutations'
CACHE=ROOT/'benchmark_cache'
PROJECTS=[('speeduino/speeduino','master','speeduino/'),
          ('rusefi/rusefi','master','firmware/controllers/')]
MUTATIONS=[
    ('division_zero','volatile int ecu_proof_division = 12 / 0;', 'Literal division or modulo by zero'),
    ('null_dereference','int *ecu_proof_pointer = NULL; *ecu_proof_pointer = 1;', 'Possible null-pointer dereference'),
    ('out_of_bounds','int ecu_proof_samples[4]; ecu_proof_samples[4] = 1;', 'Constant array index outside declared capacity'),
    ('unbounded_copy','char ecu_proof_name[4]; strcpy(ecu_proof_name, "diagnostic request too long");', 'Potential unbounded string copy'),
]


def main():
    OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(exist_ok=True)
    evidence=[]; provenance=[]
    for repository,branch,path_prefix in PROJECTS:
        cache=CACHE/(repository.replace('/','__')+'.zip')
        if not cache.exists():
            if repository == 'rusefi/rusefi':
                response=requests.get(f'https://api.github.com/repos/{repository}/git/trees/{branch}',params={'recursive':1},timeout=30)
                response.raise_for_status(); tree=response.json(); revision=tree['sha']
                candidates=[e['path'] for e in tree['tree'] if e['path'].startswith(path_prefix) and e['path'].endswith('.cpp') and e.get('size',100001)<50000]
                licenses=[e['path'] for e in tree['tree'] if '/' not in e['path'] and re.search(r'license|copying',e['path'],re.I)]
                buffer=io.BytesIO(); selected=0
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as scoped:
                    for path in candidates+licenses:
                        if path in candidates and selected>=5: continue
                        raw_response=requests.get(f'https://raw.githubusercontent.com/{repository}/{revision}/{path}',timeout=30)
                        raw_response.raise_for_status()
                        if path in candidates:
                            if not _function_ranges(mask_non_code(raw_response.text)): continue
                            selected+=1
                        scoped.writestr(repository.split('/')[0]+'-'+revision+'/'+path,raw_response.content)
                cache.write_bytes(buffer.getvalue())
            else:
                response=requests.get(f'https://codeload.github.com/{repository}/legacy.zip/refs/heads/{branch}',timeout=120)
                response.raise_for_status(); cache.write_bytes(response.content)
        raw=cache.read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as upstream:
            root=upstream.namelist()[0].split('/')[0]
            files=[]
            for info in sorted(upstream.infolist(),key=lambda i:i.filename):
                relative='/'.join(info.filename.split('/')[1:])
                if relative.startswith(path_prefix) and relative.endswith(('.c','.cpp')) and info.file_size<100000:
                    try: source=upstream.read(info).decode('utf-8')
                    except UnicodeDecodeError: continue
                    functions=_function_ranges(mask_non_code(source))
                    if functions:
                        files.append((relative,source,functions[0]))
                if len(files)==5: break
            licenses=[i for i in upstream.infolist() if len(i.filename.split('/'))==2 and re.search(r'(?:license|copying)',i.filename,re.I)]
            license_entries={i.filename.split('/')[-1]: upstream.read(i) for i in licenses}
            provenance.append(dict(repository=repository,url=f'https://github.com/{repository}',snapshot_root=root,
                                   archive_sha256=hashlib.sha256(raw).hexdigest(),source_files=[f[0] for f in files],
                                   license_files=list(license_entries),scope='Five actual ECU source files; controlled statements inserted into existing functions, not discovered upstream bugs'))
            for index,(path,baseline,function) in enumerate(files):
                masked=mask_non_code(baseline)
                match=next(m for m in re.finditer(r'\b'+re.escape(function['name'])+r'\s*\([^;{}]*\)\s*\{',masked))
                insertion=match.end()
                baseline_findings=analyze_source(baseline)[1]
                for label,statement,expected in MUTATIONS:
                    mutant=baseline[:insertion]+'\n    '+statement+'\n'+baseline[insertion:]
                    findings=analyze_source(mutant)[1]
                    insertion_line=mutant.count('\n',0,insertion)+2
                    detected=[f for f in findings if f['title']==expected and f['line']==insertion_line]
                    case_id=f"{repository.split('/')[0]}_{index+1:02}_{label}"
                    diff=''.join(difflib.unified_diff(baseline.splitlines(True),mutant.splitlines(True),fromfile='baseline/'+path,tofile='mutant/'+path))
                    (OUT/(case_id+'.patch')).write_text(diff,encoding='utf-8')
                    evidence.append(dict(case_id=case_id,repository=repository,file=path,function=function['name'],
                                         mutation=statement,expected_title=expected,injected_line=insertion_line,
                                         detected=bool(detected),baseline_candidate_count=len(baseline_findings),
                                         mutant_candidate_count=len(findings),matching_findings=detected,
                                         baseline_sha256=hashlib.sha256(baseline.encode()).hexdigest(),
                                         mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest()))
                    # A few small ZIPs are sufficient for manual upload; all 40 patches remain inspectable.
                    if index==0:
                        for variant,content in [('baseline',baseline),('mutant',mutant)]:
                            zip_path=OUT/(case_id+'_'+variant+'.zip')
                            if variant=='baseline' and zip_path.exists(): continue
                            with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
                                z.writestr(repository.split('/')[0]+'/'+path,content)
                                for license_name,data in license_entries.items(): z.writestr(license_name,data)
                                z.writestr('PROVENANCE.json',json.dumps(provenance[-1],indent=2))
                                z.writestr('MUTATION_NOTICE.txt','Educational static-analysis fixture only. Do not compile into or flash a vehicle.\n'+(statement if variant=='mutant' else 'Original source baseline.'))
                        # Exercise the same ZIP scanner used by the upload API.
                        scan=analyze_repository_zip((OUT/(case_id+'_mutant.zip')).read_bytes(),case_id+'.zip')
                        evidence[-1]['upload_path_detected']=any(f['title']==expected for f in scan['findings'])
    summary=dict(generated_at=datetime.now(timezone.utc).isoformat(),upstream_projects=len(provenance),
                 actual_source_files=sum(len(p['source_files']) for p in provenance),mutation_cases=len(evidence),
                 detected=sum(e['detected'] for e in evidence),
                 limitations=['Statements injected into real functions are controlled synthetic defects',
                              'No claim that upstream projects contain these injected defects',
                              'Mutation score measures only these four supported defect families',
                              'No hardware execution, firmware compilation, timing or safety certification'])
    (OUT/'results.json').write_text(json.dumps(dict(summary=summary,provenance=provenance,cases=evidence),indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return 0 if evidence and all(e['detected'] for e in evidence) else 1


if __name__=='__main__': raise SystemExit(main())
