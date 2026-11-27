"""Render review PDFs from the versioned manuscript and measured evidence only.
Documentation dependency: ReportLab 4.4.9. Runtime application does not need it.
"""
import hashlib
import json
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"docs/v4-delivery"
EVIDENCE=ROOT/"docs/v4-evidence/continuation"
NAVY=colors.HexColor("#102d46")
TEAL=colors.HexColor("#007c83")
GREY=colors.HexColor("#536477")
PALE=colors.HexColor("#edf5f8")


def pstyle(name="body", **kw):
    options=dict(fontName="Helvetica",fontSize=10,leading=14,
                 textColor=NAVY,spaceAfter=8,splitLongWords=True)
    options.update(kw)
    return ParagraphStyle(name,**options)


def measure():
    # Verify the exported inventory before typesetting any measured value.
    manifest=json.loads((EVIDENCE/"MANIFEST.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        raw=(EVIDENCE/f["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==f["sha256"] and len(raw)==f["bytes"]
    unit=(EVIDENCE/"unit-tests.txt").read_text(encoding="utf-8-sig")
    tests=int(re.search(r"(\d+) passed",unit).group(1))
    browser=json.loads((EVIDENCE/"browser/report.json").read_text(encoding="utf-8"))
    external=json.loads((EVIDENCE/"external/summary.json").read_text(encoding="utf-8"))
    vertical=json.loads((EVIDENCE/"reproduction/vertical.json").read_text(encoding="utf-8"))
    assert browser["status"]=="passed" and all(x["passed"] for x in vertical.values())
    assert (tests,len(browser["checks"]),len(vertical),external["fault_detected"],external["control_accusations"])==(182,19,5,7,0)
    return tests,len(browser["checks"]),len(vertical),external


def header(c, doc):
    w,h=A4;c.saveState();c.setFillColor(TEAL);c.setFont("Helvetica-Bold",8)
    c.drawString(42,h-25,"ALGOXRAY / V4 / AUTHOR REVIEW DRAFT")
    c.setStrokeColor(TEAL);c.line(42,h-31,w-42,h-31)
    c.setFillColor(GREY);c.setFont("Helvetica",8)
    c.drawString(42,23,"Experimental evidence; no independent accuracy or learning claim")
    c.drawRightString(w-42,23,str(doc.page));c.restoreState()


def manuscript():
    styles={"body":pstyle(),"title":pstyle("title",fontName="Helvetica-Bold",fontSize=19,leading=23,spaceAfter=14),
            "h":pstyle("heading",fontName="Helvetica-Bold",fontSize=12,leading=16,spaceBefore=10,keepWithNext=True),
            "small":pstyle("small",fontSize=8,leading=11)}
    story=[];lines=(DEST/"manuscript.md").read_text(encoding="utf-8").splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]),styles["title"]));i+=1;continue
        if line.startswith("## "):
            story.append(Paragraph(escape(line[3:]),styles["h"]));i+=1;continue
        if line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].startswith("|"):
                cells=[x.strip() for x in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r"[-:]+",x) for x in cells):
                    rows.append([Paragraph(escape(x),styles["small"]) for x in cells])
                i+=1
            table=Table(rows,colWidths=[105,160,A4[0]-84-265],repeatRows=1,hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PALE),("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LINEBELOW",(0,0),(-1,0),.8,TEAL),("LINEBELOW",(0,1),(-1,-1),.25,colors.HexColor("#d3dfe6")),
                ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
            story.extend([table,Spacer(1,8)]);continue
        group=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(("#","|")):
            group.append(lines[i]);i+=1
        story.append(Paragraph(escape(" ".join(group)),styles["small"] if line.startswith("[") else styles["body"]))
    SimpleDocTemplate(str(DEST/"manuscript.pdf"),pagesize=A4,rightMargin=42,leftMargin=42,
        topMargin=45,bottomMargin=42,title="AlgoX-Ray V4 experimental manuscript",author="Hussam Eddin Alwan").build(story,onFirstPage=header,onLaterPages=header)


def poster(tests, journeys, demos, external):
    w,h=A3;c=canvas.Canvas(str(DEST/"poster.pdf"),pagesize=A3)
    c.setTitle("AlgoX-Ray V4 - experimental poster draft");c.setAuthor("Hussam Eddin Alwan")
    c.setFillColor(NAVY);c.rect(0,h-162,w,162,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont("Helvetica-Bold",38);c.drawString(36,h-58,"AlgoX-Ray V4")
    c.setFont("Helvetica",18);c.drawString(36,h-88,"Replayable debugging evidence + block-level profiling")
    c.setFont("Helvetica",11);c.drawString(36,h-115,"Hussam Eddin Alwan | Experimental author-review draft | 27 November 2026")
    c.setFont("Helvetica",10);c.drawString(36,h-139,"Bounded Python tasks. Real execution. Optional AI hypotheses. Explicit limits.")
    gap=12;card_w=(w-72-3*gap)/4
    for i,(number,label) in enumerate([(str(tests),"software tests passed"),(str(journeys),"browser journeys passed"),(str(demos),"authored demos passed"),("7 / 7","known faulty variants found")]):
        x=36+i*(card_w+gap);y=h-250
        c.setFillColor(PALE);c.roundRect(x,y,card_w,68,8,fill=1,stroke=0)
        c.setFillColor(TEAL);c.setFont("Helvetica-Bold",27);c.drawString(x+13,y+32,number)
        c.setFillColor(NAVY);c.setFont("Helvetica",10);c.drawString(x+13,y+13,label)
    col_w=(w-92)/2;left,right=36,56+col_w;top=h-278
    style=pstyle("poster",fontSize=11,leading=16,spaceAfter=0)
    def section(x,y,title,text):
        c.setFillColor(TEAL);c.setFont("Helvetica-Bold",15);c.drawString(x,y,title)
        paragraph=Paragraph(text,style);_,height=paragraph.wrap(col_w,900)
        paragraph.drawOn(c,x,y-14-height)
        return y-35-height
    y=section(left,top,"THE PROBLEM", "A wrong output proves a discrepancy on one input. It does not identify its cause. AlgoX-Ray exposes the input, replay and runtime states so the learner can inspect what happened.")
    y=section(left,y,"THE EXECUTABLE WORKFLOW", "1. Review a declarative problem package and references.<br/>2. Generate legal bounded inputs and compare outputs.<br/>3. Reduce a failure and compare three replays.<br/>4. Inspect observed events, frames, variables and source.<br/>5. Check optional model facts against recorded values.<br/>6. Review a separate patch and test named cases.")
    y=section(left,y,"TIME FOR EACH BLOCK", "Measure correct or incorrect code on a chosen legal input. Inspect wall and CPU time, visit counts, self and inclusive cost, and averages. Sort hotspots, jump to source, and export CSV/JSON.<br/><br/>Collection excludes our trace callback from attributed segments, but remains instrumented. Nested inclusive times overlap. Loop header visits are not always body iterations.")
    y=section(left,y,"LOCAL-FIRST EXECUTION", "Python stdin/stdout runs in a pinned, short-lived worker with no network or host mounts, read-only root and bounded resources. Ollama is local by default. Cloud calls require explicit consent. No public arbitrary-code service is enabled.")
    y=section(left,y,"REPRODUCIBLE EVIDENCE", "The public SHA-256 manifest includes synthetic traces, browser captures, model smoke, isolation probes and clean-checkout reports. Original source and repair candidates retain separate identities.")
    z=section(right,top,"WHAT WAS MEASURED", "Seven public QuixBugs families, each faulty/corrected: <b>7/7 faults found, 0/7 controls accused, 21 replay matches.</b> Five separate authored demonstrations passed. These are known examples, not unseen student submissions.")
    z=section(right,z,"ACTUAL PROFILING INTERFACE", "Synthetic factorial example measured in the real browser. Larger desktop and mobile captures are included in the evidence folder.")
    capture=EVIDENCE/"browser/profile-table.png"
    image=ImageReader(str(capture));iw,ih=image.getSize();height=col_w*ih/iw
    c.drawImage(image,right,z-height,width=col_w,height=height,mask="auto");z-=height+22
    z=section(right,z,"LOCAL MODEL SMOKE", "Qwen2.5-Coder 7B Q4_K_M, context 4096. Three schema-valid probes: fixed-candidate draft transport 10.594 s; diagnosis 4.391 s; empty-evidence abstention 0.421 s. This is a tiny smoke test, not comparative model accuracy.")
    z=section(right,z,"LIMITS THAT MATTER", "Timing is not Codeforces judge runtime or a Big-O estimate. Schema and snapshot checks do not prove causal prose. General constraints, alias/heap slicing, independent factuality ratings, larger matched AI ablations and learning effects remain unverified.")
    z=section(right,z,"PRIOR ART", "Python Tutor: execution visualization.<br/>Code Hunt/Pex4Fun: generated counterexamples.<br/>ITAP: personalized program-state hints.<br/>CodeHelp: LLM guardrails.<br/>No first-of-kind or superiority claim.")
    assert min(y,z)>65,(y,z)
    c.setStrokeColor(TEAL);c.line(36,51,w-36,51)
    c.setFillColor(GREY);c.setFont("Helvetica",9)
    c.drawString(36,34,"Runtime: b65f596 | Same-machine reproduction | Author/venue approval and independent human review pending")
    c.drawString(36,19,"github.com/Hussam-alwan/AlgoXRay | docs/v4-evidence/continuation/MANIFEST.json")
    c.showPage();c.save()


def main():
    measured=measure();manuscript();poster(*measured)
    report={name:dict(bytes=(DEST/name).stat().st_size,sha256=hashlib.sha256((DEST/name).read_bytes()).hexdigest()) for name in ("manuscript.pdf","poster.pdf")}
    (DEST/"pdf-build.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))


if __name__=="__main__":main()
