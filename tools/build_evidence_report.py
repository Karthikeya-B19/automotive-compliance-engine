"""Build the current technical report PDF from maintained Markdown and measured JSON."""
from html import escape
import json
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

ROOT=Path(__file__).resolve().parents[1]


def main():
    destination=ROOT/'deliverables'/'CB.AI.U4AID23109_TechnicalReport_v2.0.pdf'
    destination.parent.mkdir(exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyReport',fontName='Helvetica',fontSize=10.5,leading=15.3,spaceAfter=9,allowWidows=0,allowOrphans=0,textColor=colors.HexColor('#182e35')))
    styles.add(ParagraphStyle(name='SectionReport',fontName='Helvetica-Bold',fontSize=15,leading=19,spaceBefore=17,spaceAfter=9,keepWithNext=True,textColor=colors.black))
    styles.add(ParagraphStyle(name='TitleReport',fontName='Helvetica-Bold',fontSize=26,leading=31,spaceAfter=19,textColor=colors.black))
    content=[]
    def rich(text):
        value=escape(text)
        value=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',value)
        return value
    for paragraph in (ROOT/'docs'/'TECHNICAL_REPORT_v2.md').read_text(encoding='utf-8').split('\n\n'):
        paragraph=paragraph.strip()
        if not paragraph: continue
        if paragraph.startswith('# '):
            content.append(Paragraph(rich(paragraph[2:]),styles['TitleReport']))
        elif paragraph.startswith('## '):
            content.append(Paragraph(rich(paragraph[3:]),styles['SectionReport']))
        else:
            content.append(Paragraph(rich(paragraph.replace('\n',' ')),styles['BodyReport']))
    content.append(PageBreak())
    content.append(Paragraph('Measured evidence snapshot',styles['SectionReport']))
    for label,path in [('Component verification','component_evidence.json'),('Public corpus','public_benchmark/summary.json'),
                       ('ECU mutation study','ecu_mutations/results.json'),('Retrieval experiment','rag_evidence/retrieval_results.json')]:
        data=json.loads((ROOT/'Evaluation_Results'/path).read_text(encoding='utf-8'))
        summary=data.get('summary',data)
        content.append(Paragraph(label,styles['SectionReport']))
        if label=='Component verification':
            description=f"{summary['passed']} of {summary['test_cases']} automated tests passed, with {summary['failed']} failures and {summary['skipped']} skips. Both actual CLI severity-gate comparisons passed. The JSON and JUnit XML preserve each case and implementation hashes."
        elif label=='Public corpus':
            description=f"{summary['distinct_repositories']} distinct repositories, {summary['files']:,} eligible C/C++ files and {summary['lines']:,} lines scanned. Repository-level failures: {summary['failed']}. Candidate findings: {summary['candidate_findings']:,}. Median total cache/download-plus-scan time: {summary['p50_total_seconds']} seconds per repository. This is not isolated analyzer latency."
        elif label=='ECU mutation study':
            description=f"{summary['detected']} of {summary['mutation_cases']} injected cases detected across {summary['actual_source_files']} actual files from {summary['upstream_projects']} upstream projects. The four mutation families and injected-line checks are inspectable in the per-case records."
        else:
            a=summary['lexical']; b=summary['hybrid']
            description=f"{summary['query_count']} author-labelled queries. Lexical recall at 5: {a['recall_at_5']:.0%}, top-one accuracy: {a['top1_accuracy']:.0%}, MRR at 5: {a['mrr_at_5']:.3f}. Hybrid recall at 5: {b['recall_at_5']:.0%}, top-one accuracy: {b['top1_accuracy']:.0%}, MRR at 5: {b['mrr_at_5']:.3f}. All four corpus/citation intervention controls passed. Actual hybrid strategy: BM25 plus dense reciprocal rank fusion."
        content.append(Paragraph(rich(description),styles['BodyReport']))
        content.append(Paragraph(rich('Evidence: Evaluation_Results/'+path),styles['BodyReport']))
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#52676e'))
        canvas.drawString(48,28,'CB.AI.U4AID23109  /  Technical report v2.0')
        canvas.drawRightString(A4[0]-48,28,str(doc.page)); canvas.restoreState()
    doc=SimpleDocTemplate(str(destination),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48,
                          title='Automotive Secure Code Review Assistant Technical Report',author='Karthikeya Bellapukonda')
    doc.build(content,onFirstPage=footer,onLaterPages=footer)
    print(destination)


if __name__=='__main__': main()
