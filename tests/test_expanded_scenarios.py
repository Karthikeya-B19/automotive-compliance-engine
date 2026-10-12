import io
import json
import zipfile
import pytest
from src.analysis.static_analyzer import analyze_source
from src.analysis.automotive_checks import RULES
from src.analysis.repository_analyzer import analyze_repository_zip, RepositoryArchiveError
from src.rag.automotive_retrieval import default_cards, ground_findings, retrieve, validate_model_citation


POSITIVE_CASES = [
    ('AUTO-DIV-ZERO', 'int f(int rpm) { return rpm / 0; }'),
    ('AUTO-ARRAY-BOUND', 'int f(void) { int a[4]; a[4] = 1; return 0; }'),
    ('AUTO-SHIFT-WIDTH', 'int f(void) { uint32_t a = 1; return a << 32; }'),
    ('AUTO-ASSIGN-COND', 'int f(int state) { if (state = 2) return 1; return 0; }'),
    ('AUTO-FORMAT', 'void f(char *input) { printf(input); }'),
    ('AUTO-DOUBLE-FREE', 'void f(void) { char *p=malloc(8); free(p); free(p); }'),
    ('AUTO-USE-AFTER-FREE', 'void f(void) { char *p=malloc(8); free(p); p[0]=1; }'),
    ('AUTO-ISR-HEAP', 'void CAN_IRQHandler(void) { void *p=malloc(8); free(p); }'),
    ('AUTO-ISR-BLOCK', 'void timer_ISR(void) { HAL_Delay(10); }'),
    ('AUTO-RECURSION', 'int f(int a) { return f(a); }'),
    ('AUTO-CAN-DLC', 'void f(void) { struct can_frame frame; frame.can_dlc=12; }'),
    ('AUTO-BUSY-WAIT', 'void f(void) { while (1) {} }'),
    ('AUTO-SHELL', 'void f(char *cmd) { system(cmd); }'),
]
NEGATIVE_CASES = [
    ('AUTO-DIV-ZERO', 'int f(int rpm) { return rpm / 2; }'),
    ('AUTO-ARRAY-BOUND', 'int f(void) { int a[4]; a[3] = 1; return 0; }'),
    ('AUTO-SHIFT-WIDTH', 'int f(void) { uint32_t a = 1; return a << 31; }'),
    ('AUTO-ASSIGN-COND', 'int f(int state) { if (state == 2) return 1; return 0; }'),
    ('AUTO-FORMAT', 'void f(char *input) { printf("%s", input); }'),
    ('AUTO-DOUBLE-FREE', 'void f(void) { char *p=malloc(8); free(p); p=malloc(8); free(p); }'),
    ('AUTO-USE-AFTER-FREE', 'void f(void) { char *p=malloc(8); p[0]=1; free(p); }'),
    ('AUTO-ISR-HEAP', 'void background(void) { void *p=malloc(8); free(p); }'),
    ('AUTO-ISR-BLOCK', 'void background(void) { HAL_Delay(10); }'),
    ('AUTO-RECURSION', 'int f(int a) { return a; }'),
    ('AUTO-CAN-DLC', 'void f(void) { struct can_frame frame; frame.can_dlc=8; }'),
    ('AUTO-BUSY-WAIT', 'void f(void) { while (ready) { ready=0; } }'),
    ('AUTO-SHELL', 'void f(char *cmd) { validate(cmd); }'),
]


@pytest.mark.parametrize('rule,source', POSITIVE_CASES)
@pytest.mark.parametrize('prefix', ['', '// example strcpy(x,y);\n/* gets(p); */\n'])
def test_positive_rule_and_line_mapping(rule, source, prefix):
    _, findings = analyze_source(prefix + source)
    matched = [f for f in findings if f.get('rule_id') == rule]
    assert matched
    assert all(f['line'] == len(prefix.splitlines()) + 1 for f in matched)


@pytest.mark.parametrize('rule,source', NEGATIVE_CASES)
def test_corrected_counterexample(rule, source):
    assert rule not in {f.get('rule_id') for f in analyze_source(source)[1]}


@pytest.mark.parametrize('source', [
    '// strcpy(a,b);\nint f(void){return 0;}',
    '/* gets(p);\nstrcat(x,y); */\nint f(void){return 0;}',
    'void f(void) { const char *s="strcpy(x,y); while(1){}"; }',
    'void first(void) { int *p=NULL; }\nvoid second(int *p) { *p=1; }',
    'void f(void) { int *p=NULL; p=get_pointer(); *p=1; }',
])
def test_comments_strings_and_pointer_scope_do_not_create_candidates(source):
    assert analyze_source(source)[1] == []


@pytest.mark.parametrize('rule,source', POSITIVE_CASES)
def test_each_new_detector_can_retrieve_applicable_guidance(rule, source):
    findings = analyze_source(source)[1]
    grounded, trace = ground_findings(findings)
    item = next(f for f in grounded if f.get('rule_id') == rule)
    assert item['grounding']['rule_id'] == rule
    assert trace['supported_count'] >= 1


def test_missing_corpus_rule_abstains():
    findings = analyze_source('int f(int a){return a / 0;}')[1]
    cards = [c for c in default_cards() if c['rule_id'] != 'AUTO-DIV-ZERO']
    grounded, trace = ground_findings(findings, cards=cards)
    assert trace['abstained_count'] == len(findings)
    assert grounded[0]['grounding']['decision'] == 'abstain'


@pytest.mark.parametrize('reference,evidence,accepted', [
    ('AUTO-DIV-ZERO', ['Validate denominator.'], True),
    ('MISRA 999.9', ['Validate denominator.'], False),
    ('AUTO-DIV-ZERO', ['Invented text.'], False),
    ('AUTO-DIV-ZERO', [], False),
    ('AUTO-DIV-ZERO', [''], False),
    ('', ['Validate denominator.'], False),
    ('AUTO-NULL', ['Validate denominator.'], False),
])
def test_model_citation_gate(reference, evidence, accepted):
    doc = dict(rule_id='AUTO-DIV-ZERO', content='Validate denominator.', applicability='supported-candidate')
    parsed, trace = validate_model_citation(dict(rule_reference=reference, source_evidence=evidence, confidence='High'), [doc])
    assert trace['accepted'] == accepted
    if not accepted:
        assert parsed['rule_reference'] == 'No applicable rule found'
        assert parsed['source_evidence'] == []


@pytest.mark.parametrize('path', ['../bad.c', '/bad.c', 'C:/bad.c', 'repo/../../bad.c', 'repo\\..\\bad.c'])
def test_hostile_archive_paths(path):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z: z.writestr(path, 'int f(void){return 0;}')
    with pytest.raises(RepositoryArchiveError): analyze_repository_zip(buffer.getvalue(), 'bad.zip')


def test_cached_retrieval_cannot_be_mutated_by_caller():
    first = retrieve('null pointer validity')
    first['candidates'][0]['text'] = 'POISON'
    assert retrieve('null pointer validity')['candidates'][0]['text'] != 'POISON'


def test_rule_corpus_has_unique_explicit_synthetic_authority():
    cards=default_cards()
    assert len({c['rule_id'] for c in cards}) == len(cards) == 20
    assert all(c['origin']=='synthetic-project-guidance' for c in cards)


def test_real_fallback_preserves_retrieval_evidence(monkeypatch):
    from src.rag import orchestrator
    monkeypatch.setenv('REVIEW_DENSE_RETRIEVAL', 'false')
    def unavailable(): raise ConnectionError('Simulated local model outage')
    monkeypatch.setattr(orchestrator,'_get_orchestrator',unavailable)
    result=orchestrator.review_code('int f(int rpm){return rpm / 0;}')
    assert result['review_mode']=='retrieval-grounded-template'
    assert result['retrieval_trace']['supported_count']==1
    assert result['findings'][0]['grounding']['rule_id']=='AUTO-DIV-ZERO'
    assert 'LLM generation is unavailable' in result['review_summary']


def test_api_preserves_real_grounding_trace(monkeypatch,tmp_path):
    from src.api import main
    from src.rag import orchestrator
    from src.storage.review_store import ReviewStore
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main,'review_store',ReviewStore(tmp_path/'reviews.db'))
    monkeypatch.setenv('REVIEW_DENSE_RETRIEVAL','false')
    monkeypatch.setattr(orchestrator,'_get_orchestrator',lambda: (_ for _ in ()).throw(ConnectionError()))
    client=TestClient(main.app)
    response=client.post('/api/v1/review',json={'code_snippet':'int f(int rpm){return rpm / 0;}'})
    assert response.status_code==200
    body=response.json()
    assert body['retrieval_trace']['supported_count']==1
    stored=client.get('/api/v1/reviews/'+body['review_id']).json()
    assert stored['response']['retrieval_trace']==body['retrieval_trace']


def test_corpus_removal_changes_guidance_but_not_detector():
    source='int f(int rpm){return rpm / 0;}'
    _,findings=analyze_source(source)
    supported,_=ground_findings(findings)
    missing,_=ground_findings(findings,cards=[])
    assert supported[0]['grounding']['rule_id']=='AUTO-DIV-ZERO'
    assert missing[0]['grounding']['decision']=='abstain'
    assert supported[0]['title']==missing[0]['title']
