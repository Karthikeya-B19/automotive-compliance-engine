"""Generate current submission PDFs. Does not sign, approve or overwrite older artifacts."""
from html import escape
import json
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, Image
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables'
REG='CB.AI.U4AID23109'
VERSION='3.0'
NAVY=colors.HexColor('#102b32')
TEAL=colors.HexColor('#087f75')
PALE=colors.HexColor('#e9f1f2')
STYLES=getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='FinalTitle',fontName='Helvetica-Bold',fontSize=25,leading=30,spaceAfter=18,textColor=NAVY))
STYLES.add(ParagraphStyle(name='FinalH',fontName='Helvetica-Bold',fontSize=14,leading=18,spaceBefore=14,spaceAfter=8,textColor=NAVY,keepWithNext=True))
STYLES.add(ParagraphStyle(name='FinalBody',fontName='Helvetica',fontSize=10.2,leading=14.5,spaceAfter=8,allowWidows=0,allowOrphans=0))
STYLES.add(ParagraphStyle(name='FinalCell',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=0))
STYLES.add(ParagraphStyle(name='FinalHeadCell',fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=colors.white))


def clean(value):
    return str(value).replace('\u2014',' - ').replace('\u2013','-').replace('\u2011','-').replace('\u00b7',',').replace('\u2019',"'").replace('\u201c','"').replace('\u201d','"')


def para(value,style='FinalBody'):
    value=escape(clean(value))
    value=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',value)
    return Paragraph(value,STYLES[style])


def heading(value): return para(value,'FinalH')


def table(rows,widths):
    data=[[para(cell,'FinalHeadCell' if i==0 else 'FinalCell') for cell in row] for i,row in enumerate(rows)]
    result=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#ccdadd')),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return result


def build(kind,content):
    target=OUT/f'{REG}_{kind}_v{VERSION}.pdf'
    if target.exists(): raise FileExistsError(target)
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#52676e'))
        canvas.drawString(44,26,f'{REG} / {kind} v{VERSION}')
        canvas.drawRightString(A4[0]-44,26,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=44,bottomMargin=45,
        title=f'Automotive Secure Code Review Assistant - {kind}',author='Karthikeya Bellapukonda').build(content,onFirstPage=footer,onLaterPages=footer)
    print(target)


def identity(title):
    return [para(title,'FinalTitle'),para('Karthikeya Bellapukonda | CB.AI.U4AID23109'),
        para('Amrita Vishwa Vidyapeetham | TechPulse Digital Track | Individual Case Study 4'),
        para('Release 3.0 | 16 October 2026'),Spacer(1,10)]


def markdown(value):
    result=[]
    for block in value.split('\n\n'):
        block=block.strip()
        if not block: continue
        if block.startswith('# '): result.append(para(block[2:],'FinalTitle'))
        elif block.startswith('## '): result.append(heading(block[3:]))
        else: result.append(para(block.replace('\n',' ')))
    return result


def workflow():
    d=Drawing(500,410)
    labels=['Authorized C/C++ ZIP, snippet and diagnostics',
        'FastAPI validation, archive boundaries and path permissions',
        'Lexical masking, deterministic candidates and module map',
        'BM25 / local vectors, rank fusion and typed applicability',
        'Local llama3.1 explanation and exact citation validation',
        'Streamlit evidence, SQLite history and human disposition']
    for i,label in enumerate(labels):
        y=354-i*62
        d.add(Rect(5,y,490,44,fillColor=PALE,strokeColor=TEAL,strokeWidth=.7))
        d.add(String(250,y+17,label,fontName='Helvetica',fontSize=10,textAnchor='middle',fillColor=NAVY))
        if i<5:
            d.add(Line(250,y,250,y-14,strokeColor=TEAL,strokeWidth=1))
            d.add(Polygon([246,y-10,250,y-17,254,y-10],fillColor=TEAL,strokeColor=TEAL))
    return d


RUBRIC=[
    ('Problem and automotive context',5,'Purpose, scope, users and measurable review contracts. Human productivity reduction is not measured.'),
    ('AI/ML approach selection',5,'BM25 baseline versus hybrid ablation and frozen local model rationale. Multiple LLMs were not benchmarked.'),
    ('Dataset, preprocessing and EDA',15,'Source inventory, encodings, exclusions, duplicate hashes, license metadata and labelled-query limitations.'),
    ('Representations and feature choices',8,'Identifier tokens, semantic vectors and typed rule IDs. PCA/supervised feature selection do not apply to this unfitted index.'),
    ('Model development and techniques',18,'Implemented local RAG, deterministic analysis and BM25/hybrid comparison. No supervised training or scientific-novelty claim.'),
    ('Evaluation and optimization',15,'93 tests, 100-repo robustness, 40 mutations, ranking/control/model traces. No real-corpus precision estimate.'),
    ('Completeness and demonstration',15,'Runnable source and packaged tests. Faculty approval, personal signatures and a current-version video remain required.'),
    ('Python quality',6,'Modular analysis/API/RAG/storage/UI, input validation and regression tests. Text heuristics remain limited.'),
    ('Deployment/MLOps',5,'Pinned requirements, model/corpus hashes and successful CI SARIF. Docker supplied but not built in this audit.'),
    ('Responsible AI',3,'Local processing, advisory authority labels, applicability/citation gates, human approval and declared privacy/encryption limits.'),
    ('Technical Q&A',3,'Detailed report and RAG proof guide explain formulas, alternatives, rejection examples, assumptions and boundaries.'),
    ('Communication',2,'Overview deck, dedicated RAG deck, report and 10/10/8/2-minute evaluation plan. Faculty awards actual scores.'),
]


def main():
    OUT.mkdir(exist_ok=True)
    assert sum(x[1] for x in RUBRIC)==100
    body=(ROOT/'docs/TECHNICAL_REPORT_v2.md').read_text(encoding='utf-8')
    body=body.replace('Version 2.0, 12 October 2026.','Report version 3.0, 16 October 2026. Original benchmark/retrieval/model observations were recorded 12 October; component checks were rerun 16 October.')
    content=markdown(body)
    content += [PageBreak(),para('Implementation workflow','FinalTitle'),workflow(),
        para('No applicable card: abstain from rule support. Local model unavailable: labelled template/fallback. A citation rejection clears the unsupported model evidence. No automatic merge or release approval occurs.'),
        para('The active vector matrix is local and cached in memory. The legacy persistent Chroma index does not supply this path.')]
    content += [PageBreak()]+markdown((ROOT/'docs/FINAL_SUBMISSION_REPORT_ADDENDUM.md').read_text(encoding='utf-8'))
    content += [PageBreak(),para('Rubric-to-evidence map','FinalTitle'),
        para('The provided rubric totals 100 marks across 12 criteria. This map identifies evidence and limits; it does not assign or imply faculty scores.'),
        table([['Criterion','Max','Evidence and boundary']]+[[a,str(b),c] for a,b,c in RUBRIC],[155,38,314])]
    testlog=(ROOT/'Evaluation_Results/CB.AI.U4AID23109_TestLog_v2.0.txt').read_text(encoding='utf-8')
    content += [PageBreak(),para('Retained execution evidence','FinalTitle'),
        heading('Current component test log'),para('Actual captured output, 16 October 2026. Full JUnit and machine-readable results remain in Code/Evaluation_Results.'),
        Preformatted(clean(testlog),ParagraphStyle(name='CodeFinal',fontName='Courier',fontSize=8,leading=11),maxLineLength=96),
        heading('Actual model citation outcomes'),
        table([['Case','Actual model call','Citation result'],['Unsafe strcpy','Yes; 4.991 seconds','AUTO-STRCPY and exact advisory quote accepted'],['Zero division','Yes; 8.282 seconds','Source-code quote rejected; deterministic finding retained'],['Clean rpm / 2','No; 0.001 seconds observed','No applicable candidate context; deterministic-only']],[130,155,222]),
        para('These model observations are retained 12 October results, not freshly generated on 16 October. Durations are individual calls, not throughput estimates.')]
    frame=ROOT/'.build/submission_audit/video_25.png'
    if frame.exists():
        content += [PageBreak(),para('Historical screenshot provenance','FinalTitle'),
            para('This real frame at 00:25 comes from the student-supplied recording created 7 October 2026. It documents the earlier UI only. It is not a screenshot of the final four-tab UI or evidence of the revised RAG path.'),
            Image(str(frame),width=507,height=275),Spacer(1,12),
            para('Current UI construction, findings and retrieval widgets pass Streamlit AppTest. A full current-version browser visual/accessibility certification is not claimed. A new recording of the submitted version remains a student completion action.')]
    build('TechnicalReport',content)

    content=identity('Project synopsis')+[
        heading('Problem and intended users'),para('Local engineering assistance for confidential automotive C/C++ review. Users are embedded developers, reviewers, technical leads and cybersecurity/quality engineers.'),
        heading('Scope and outputs'),para('Repository ZIP and snippet analysis; function/module/include summaries; warning/SARIF interpretation; candidate null, boundary, resource and state risks; advisory explanations, recommendations and saved structured reports with human status.'),
        heading('Implementation'),para('Python FastAPI, Streamlit, SQLite, deterministic rules, 20 synthetic automotive advisory cards, lexical BM25 and optional local all-MiniLM-L6-v2 vectors with reciprocal rank fusion. Local Ollama llama3.1 generates structured explanations that pass exact applicability/citation gates. The active card index is in memory; legacy Chroma ingestion is experimental.'),
        heading('Evaluation and expected outcomes'),para('93 component/API/UI tests, 100 actual public repositories, 40 controlled mutations in ten real ECU files, 20 labelled retrieval queries and retained actual-model decisions. Hybrid recall@5 is 19/20 versus 18/20 lexical. Outcomes are advisory and scoped, not certified defect detection.'),
        heading('Controls and exclusions'),para('No uploaded code execution, external hosted-source inference, automatic merge or release approval. Source is untrusted data. Path/archive controls, prompt separation, explicit fallback and human review apply. Full compiler semantics, licensed standard compliance, enterprise encryption/IAM, timing and vehicle validation are outside demonstrated scope.'),
        PageBreak(),para('Faculty approval record','FinalTitle'),
        para('This page must be completed by the authorized faculty member. The presence of a prepared form does not constitute approval.'),
        para('Case study: CS4. Project: Automotive Secure Code Debugging and Review Assistant.'),
        Spacer(1,20),para('Decision: [  ] Approved   [  ] Approved with revisions   [  ] Revisions required'),
        Spacer(1,20),para('Faculty comments:'),para('________________________________________________________________________'),
        para('________________________________________________________________________'),Spacer(1,25),
        para('Faculty name: __________________________________________________________'),
        para('Faculty signature: ______________________________  Date: _________________'),Spacer(1,25),
        para('Student acknowledgement: ________________________  Date: _________________'),
        Spacer(1,18),para('Status at packaging: no signed faculty approval record was located. Do not submit as approved until the authorized record is supplied.')]
    build('Synopsis',content)

    content=identity('Academic integrity declaration')+[
        para('UNSIGNED FORM - for student review and completion', 'FinalH'),
        para('I, Karthikeya Bellapukonda (CB.AI.U4AID23109), submit this as an individual capstone and accept responsibility for understanding and explaining all submitted work, including disclosed AI assistance and attributed third-party source.'),
        para('I declare, upon signing, that results, citations, evidence and approvals have not knowingly been fabricated; that external code, datasets, models and documents have been attributed; and that I do not present synthetic project guidance as licensed MISRA or ISO clauses.'),
        para('I understand that generated findings are advisory and require qualified review. Passing component tests, a 100-repository robustness scan and controlled mutations do not prove production accuracy or automotive safety certification.'),
        heading('Student confirmation'),
        para('[  ] I have personally reviewed the submitted source, report, evaluation records and limitations.'),
        para('[  ] I can explain my contribution and all disclosed assistance.'),
        para('[  ] I have checked the applicable upstream licenses and permitted use of data.'),
        para('[  ] My demonstration shows the submitted version, and I disclose dependencies and unresolved limitations.'),
        Spacer(1,26),para('Student signature: _____________________________________________________'),
        para('Date: __________________________  Place: ________________________________'),
        Spacer(1,12),para('Do not tick or sign until the statements are true. The assistant has not signed or verified these statements on behalf of the student.')]
    build('AcademicIntegrityDeclaration',content)

    content=identity('AI-tool and model-use declaration')+[
        para('UNSIGNED FORM - personal verification remains with the student','FinalH'),
        para('I disclose the following assistance and pretrained models. The Verified by student column must be completed Y/N only after personal review. An automated test result is not a substitute for my confirmation.'),
        table([['AI tool / model','Purpose and artifacts affected','Verification evidence','Student Y/N'],
            ['OpenAI Codex; exact session model version not captured','Coding, debugging, tests, analysis, documents, presentations and packaging','Source review, regression/CLI tests, recorded evaluations and rendered document inspection','____'],
            ['Ollama llama3.1:latest; 8B Q4_K_M','Optional local explanation of retrieved advisory context','Actual generation records, schema, citation gate, fallback labels and human review','____'],
            ['all-MiniLM-L6-v2','Local semantic representations for hybrid card ranking','BM25/hybrid comparison, recorded actual strategy and applicability controls','____'],
            ['OpenAI image generation (earlier drafts)','Conceptual imagery used in earlier project artifacts, potentially visible in historical materials','Conceptual imagery is not measured evidence or a real-vehicle photograph','____']],[116,171,166,54]),
        Spacer(1,15),para('The active 20 cards are synthetic advisory rules. No model fine-tuning or supervised training is claimed. Source/AI assistance does not transfer responsibility for correctness away from the student.'),
        para('Model digest and retained runtime metadata are in the actual-generation JSON. Any additional AI tool used by the student must be added before signing.'),
        Spacer(1,18),para('Additional tools / notes: __________________________________________________'),
        para('________________________________________________________________________'),Spacer(1,20),
        para('Student signature: _____________________________________________________'),
        para('Date: __________________________  Place: ________________________________')]
    build('AIToolUsageDeclaration',content)


if __name__=='__main__': main()
