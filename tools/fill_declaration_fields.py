"""Fill only the student-requested entries on the preserved v1.6-package PDF."""
from pathlib import Path
import hashlib
import json
import fitz

ROOT=Path(__file__).resolve().parents[1]
NAME='AmritaVishwaVidyapeetham_KarthikeyaBellapukonda_CB.AI.U4AID23109_CS4_AIML'
REG='CB.AI.U4AID23109'
SOURCE=ROOT/'submission_v1.6'/NAME/'Declarations'/f'{REG}_Declarations_v1.1.pdf'
DEST=ROOT/'deliverables'/f'{REG}_Declarations_v1.2.pdf'


def main():
    if DEST.exists(): raise FileExistsError(DEST)
    document=fitz.open(SOURCE)
    assert len(document)==2 and not list(document[1].widgets() or [])
    assert document.get_sigflags() in (-1,0), 'Do not alter a cryptographically signed PDF.'
    cover=document[0]
    replacements=[('06 October 2026','16 October 2026'),('1.1','1.2')]
    for old,new in replacements:
        rectangles=cover.search_for(old)
        assert len(rectangles)==1,(old,rectangles)
        rect=rectangles[0]
        cover.add_redact_annot(rect,fill=(1,1,1))
        cover.apply_redactions(images=0,graphics=0)
        cover.insert_text((rect.x0,rect.y1-1.8),new,fontname='helv',fontsize=8.8,color=(.07,.15,.19))
    page=document[1]
    check_rectangles=[]
    for y in [462.0,475.0,488.0,501.5]:
        rect=fitz.Rect(74.9,y-.5,83.5,y+7.8)
        page.draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
        page.draw_rect(fitz.Rect(75.4,y,82.7,y+7.0),color=(0.06,.13,.17),width=.55,overlay=True)
        shape=page.new_shape()
        shape.draw_polyline([fitz.Point(76.3,y+3.7),fitz.Point(78.5,y+5.6),fitz.Point(82.0,y+1.0)])
        shape.finish(color=(.02,.12,.18),width=1.0);shape.commit(overlay=True)
        check_rectangles.append(list(rect))
    page.insert_text((145,525.5),'Karthikeya Bellapukonda',fontname='helv',fontsize=10.0,color=(.06,.13,.17))
    page.insert_text((86,577),'16 October 2026',fontname='helv',fontsize=10.0,color=(.06,.13,.17))
    metadata=document.metadata
    metadata['title']='Academic Integrity and AI Usage Declaration - completed student fields'
    document.set_metadata(metadata)
    document.save(DEST,garbage=4,deflate=True)
    document.close()
    saved=fitz.open(DEST)
    assert '16 October 2026' in saved[0].get_text() and '16 October 2026' in saved[1].get_text()
    assert 'Karthikeya Bellapukonda' in saved[1].get_text()
    proof=dict(source_package='submission_v1.6',source_pdf=SOURCE.name,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),filled_pdf=DEST.name,
        filled_sha256=hashlib.sha256(DEST.read_bytes()).hexdigest(),
        requested_changes=['Four student-confirmation checkboxes ticked','Typed student name: Karthikeya Bellapukonda',
            'Date: 16 October 2026; cover submission date updated','Place left unchanged and blank','Revision field updated to 1.2'],
        signature_description='Typed name entered at student request, not a drawn or cryptographic signature.',
        original_word='Unmodified v1.1 Word file retained separately as reference; Word renderer unavailable.',
        allowed_visual_change_rectangles={'1':[[310,565,490,607]],
            '2':check_rectangles+[[142,513,399,529],[82,563,230,580]]})
    (ROOT/'deliverables'/f'{REG}_DeclarationFieldUpdates_v1.2.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    out=ROOT/'.build/declaration_fill/filled_render';out.mkdir(parents=True,exist_ok=True)
    for i,p in enumerate(saved):
        p.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(out/f'page-{i+1}.png')
    print(DEST)


def verify_visual_changes():
    from PIL import Image, ImageChops, ImageDraw
    import math
    proof_path=ROOT/'deliverables'/f'{REG}_DeclarationFieldUpdates_v1.2.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    original=fitz.open(SOURCE); filled=fitz.open(DEST)
    results=[]
    for index in range(2):
        a=original[index].get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False)
        b=filled[index].get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False)
        left=Image.frombytes('RGB',[a.width,a.height],a.samples)
        right=Image.frombytes('RGB',[b.width,b.height],b.samples)
        difference=ImageChops.difference(left,right)
        draw=ImageDraw.Draw(difference)
        for x0,y0,x1,y1 in proof['allowed_visual_change_rectangles'][str(index+1)]:
            draw.rectangle([math.floor(x0*1.4)-2,math.floor(y0*1.4)-2,math.ceil(x1*1.4)+2,math.ceil(y1*1.4)+2],fill=(0,0,0))
        results.append(dict(page=index+1,unexpected_difference_bbox=difference.getbbox()))
    proof['visual_change_verification']=results
    proof_path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(results))
    assert all(x['unexpected_difference_bbox'] is None for x in results)


if __name__=='__main__': main(); verify_visual_changes()
