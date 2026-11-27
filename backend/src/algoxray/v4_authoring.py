"""Bounded public Codeforces import; AI reference proposals are never auto-approved."""
from html.parser import HTMLParser
import re,urllib.request,urllib.error
from urllib.parse import urlsplit
from .v4_contracts import validate_manifest
from .v4_isolation import MAX_SOURCE
from .v4_provider import ProviderError

MAX_HTML=2*1024*1024
VOID={"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
BLOCK={"p","div","li","pre","h1","h2","h3","br","tr"}
def normalize_url(value):
    if type(value) is not str or len(value)>250:raise ValueError("Invalid Codeforces URL")
    u=urlsplit(value)
    if u.scheme!="https" or u.netloc!="codeforces.com" or u.query or u.fragment:raise ValueError("Only public HTTPS codeforces.com problem URLs are supported")
    m=re.fullmatch(r"/(?:problemset/problem/([1-9][0-9]{0,6})/([A-Z][A-Z0-9]{0,5})|contest/([1-9][0-9]{0,6})/problem/([A-Z][A-Z0-9]{0,5}))/?",u.path)
    if not m:raise ValueError("Unsupported Codeforces problem URL")
    contest,index=(m[1],m[2]) if m[1] else (m[3],m[4])
    return f"https://codeforces.com/problemset/problem/{contest}/{index}"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.parts=[];self.samples={"input":[],"output":[]};self.current=None
    def active(self,cls):return any(cls in c for _,c in self.stack)
    def inside(self):return self.active("problem-statement") and not any(t in ("script","style") for t,_ in self.stack)
    def handle_starttag(self,tag,attrs):
        classes=set(dict(attrs).get("class","").split())
        if tag=="pre" and self.inside():
            mode=next((x for x in ("input","output") if self.active(x)),None)
            if mode:self.current=(mode,[])
        if tag in BLOCK and self.inside():self.parts.append("\n")
        if self.current and tag in ("div","br"):self.current[1].append("\n")
        if tag not in VOID:self.stack.append((tag,classes))
    def handle_endtag(self,tag):
        if self.inside() and tag in BLOCK:self.parts.append("\n")
        if self.current and tag=="div":self.current[1].append("\n")
        if tag=="pre" and self.current:
            mode,parts=self.current;self.samples[mode].append("".join(parts).strip("\n"));self.current=None
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):
        if self.inside():
            self.parts.append(data)
            if self.current:self.current[1].append(data)
def parse_problem(html,url):
    p=Parser();p.feed(html)
    statement="\n".join(x.strip() for x in "".join(p.parts).splitlines() if x.strip())
    if not statement or len(statement)>8000:raise ValueError("Statement missing or exceeds supported 8000 characters; paste text manually")
    limitations=[]
    if len(p.samples["input"])!=len(p.samples["output"]):
        pairs=[]
        limitations.append("Sample input/output counts differ; supply reviewed pairs manually.")
    else:
        pairs=[{"stdin":a,"stdout":b} for a,b in zip(p.samples["input"],p.samples["output"])]
        if len(pairs)>8:limitations.append("Only the first 8 sample pairs are retained.")
        if not pairs:limitations.append("No complete sample pairs extracted.")
    return {"status":"imported_unreviewed","source_url":url,"statement":statement,"samples":pairs[:8],"limitations":limitations,
            "warning":"Review extracted text, especially math and formatting, against the original. Samples are not independent reference validation."}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError("Redirect blocked; paste text manually")
def import_problem(value):
    url=normalize_url(value)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request(url,headers={"User-Agent":"AlgoXRay/0.4 (manual public problem import)","Accept":"text/html"})
    try:
        with opener.open(req,timeout=12) as r:
            if "text/html" not in r.headers.get("Content-Type",""):raise ValueError("Not an HTML problem page")
            raw=r.read(MAX_HTML+1)
    except OSError:raise ValueError("Codeforces fetch unavailable; paste the problem text manually") from None
    if len(raw)>MAX_HTML:raise ValueError("Problem page too large")
    return parse_problem(raw.decode("utf-8",errors="replace"),url)
REFERENCE_SCHEMA={"type":"object","properties":{"reference":{"type":"string"},"rationale":{"type":"string"}},"required":["reference","rationale"],"additionalProperties":False}
def draft_reference(provider,manifest):
    validate_manifest(manifest)
    r=provider.propose("reference_draft",{"manifest":manifest,"instruction":"Propose complete ordinary Python stdin/stdout reference source. If uncertain leave reference empty. Do not invent verified examples or claim tests passed."},REFERENCE_SCHEMA)
    if type(r) is not dict or set(r)!={"reference","rationale"} or type(r["reference"]) is not str or not 0<len(r["reference"].encode())<=MAX_SOURCE or type(r["rationale"]) is not str or len(r["rationale"])>1500:
        raise ProviderError("invalid_reference_proposal")
    return {**r,"status":"reference_unreviewed","executed":False,"warning":"Review source and constraints; supply independently known controls and optionally a second independently reviewed reference."}
