from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.analysis.static_analyzer import analyze_source
from src.rag.automotive_retrieval import ground_findings

APP=Path(__file__).resolve().parents[1]/'src'/'ui'/'app.py'


def test_workspace_renders_all_review_areas():
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not app.exception
    assert [t.label for t in app.tabs]==['Repository ZIP review','Single-file review','Review history & metrics','Verification lab']
    assert app.selectbox[0].value=='uploaded-repository'


def test_review_renders_findings_and_retrieval_proof():
    summary,findings=analyze_source('int f(int rpm){return rpm / 0;}')
    findings,trace=ground_findings(findings)
    app=AppTest.from_file(str(APP),default_timeout=30)
    app.session_state['last_review']=dict(review_id='ui-test',review_summary='Test review',code_summary=summary,
        findings=findings,retrieval_trace=trace,rule_reference='AUTO-DIV-ZERO',review_mode='retrieval-grounded-template')
    app.run()
    assert not app.exception
    assert any(m.label=='Supported candidates' and m.value=='1' for m in app.metric)
    assert any(e.label=='Inspect queries, scores and citation decisions' for e in app.expander)
    assert any(m.label=='Severity' for m in app.multiselect)


def test_theme_text_pairs_meet_wcag_aa_normal_text():
    def luminance(color):
        values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(c*w for c,w in zip(linear,[.2126,.7152,.0722]))
    pairs=[('#182e35','#f4f7f8'),('#182e35','#ffffff'),('#f7fbfb','#102b32'),
           ('#087f75','#ffffff'),('#c7d5d8','#164b50'),('#52676e','#e9f1f2')]
    for foreground,background in pairs:
        values=sorted([luminance(foreground),luminance(background)])
        assert (values[1]+.05)/(values[0]+.05)>=4.5,(foreground,background)
