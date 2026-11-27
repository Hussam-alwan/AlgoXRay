"""Declarative, bounded stdin grammar; packages are data, not host plugins."""
import hashlib,json,random,re
from pathlib import Path
from .v4_isolation import MAX_INPUT,MAX_SOURCE

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def validate_manifest(m):
    if type(m) is not dict or set(m)!={"id","title","statement","fields","lines","output"}:
        raise ValueError("Expected id,title,statement,fields,lines,output")
    if type(m["id"]) is not str or not re.fullmatch("[a-z0-9_]{1,60}",m["id"]): raise ValueError("Invalid id")
    for k,cap in (("title",120),("statement",8000)):
        if type(m[k]) is not str or not 1<=len(m[k])<=cap: raise ValueError("Invalid "+k)
    if m["output"] not in ("tokens","exact"): raise ValueError("Unsupported output policy")
    if type(m["fields"]) is not list or not 1<=len(m["fields"])<=16: raise ValueError("Invalid fields")
    prior={}
    for f in m["fields"]:
        if type(f) is not dict or type(f.get("name")) is not str or not re.fullmatch("[a-z][a-z0-9_]{0,30}",f["name"]) or f["name"] in prior: raise ValueError("Invalid field name")
        k=f.get("kind")
        base={"name","kind","min","max"}
        if k=="int":
            if set(f)!=base or type(f["min"]) is not int or type(f["max"]) is not int or not -10**15<=f["min"]<=f["max"]<=10**15: raise ValueError("Invalid integer bounds")
        elif k=="word":
            if set(f)!=base|{"alphabet"} or type(f["min"]) is not int or type(f["max"]) is not int or not 1<=f["min"]<=f["max"]<=100 or type(f["alphabet"]) is not str or not re.fullmatch("[a-zA-Z0-9]+",f["alphabet"]) or len(set(f["alphabet"]))!=len(f["alphabet"]): raise ValueError("Invalid word bounds")
        elif k=="ints":
            if set(f) not in (base|{"length"},base|{"length_from"}) or type(f["min"]) is not int or type(f["max"]) is not int or not -10**15<=f["min"]<=f["max"]<=10**15: raise ValueError("Invalid list bounds")
            if "length" in f:
                if type(f["length"]) is not int or not 1<=f["length"]<=100: raise ValueError("Invalid list length")
            else:
                p=prior.get(f["length_from"]) if type(f["length_from"]) is str else None
                if not p or p["kind"]!="int" or not 1<=p["min"]<=p["max"]<=100: raise ValueError("Invalid dependent length")
        else: raise ValueError("Unsupported field kind")
        prior[f["name"]]=f
    lines=m["lines"]
    if type(lines) is not list or not lines or any(type(row) is not list or not row or any(type(n) is not str for n in row) for row in lines):
        raise ValueError("Invalid lines")
    flat=[n for row in lines for n in row]
    if flat!=list(prior): raise ValueError("Lines must list every field exactly once in field order")
    return m

def validate_case(m,case):
    if type(case) is not dict or set(case)!={f["name"] for f in m["fields"]}: raise ValueError("Wrong case fields")
    for f in m["fields"]:
        v=case[f["name"]]; lo,hi=f["min"],f["max"]
        if f["kind"]=="int": ok=type(v) is int and lo<=v<=hi
        elif f["kind"]=="word": ok=type(v) is str and lo<=len(v)<=hi and all(x in f["alphabet"] for x in v)
        else:
            size=f["length"] if "length" in f else case[f["length_from"]]
            ok=type(v) is list and len(v)==size and all(type(x) is int and lo<=x<=hi for x in v)
        if not ok: raise ValueError("Illegal "+f["name"])
    return case

def serialize(m,case):
    validate_case(m,case)
    def token(v): return " ".join(map(str,v)) if type(v) is list else str(v)
    s="\n".join(" ".join(token(case[n]) for n in line) for line in m["lines"])+"\n"
    if len(s.encode())>MAX_INPUT: raise ValueError("Input too large")
    return s

def generate(m,seed,count):
    rng=random.Random(seed)
    for i in range(count):
        c={}
        for f in m["fields"]:
            lo,hi=f["min"],f["max"]
            def number(): return lo if i==0 else hi if i==1 else rng.choice([lo,hi,rng.randint(lo,hi)])
            if f["kind"]=="int": v=number()
            elif f["kind"]=="word":
                size=number(); v="".join(rng.choice(f["alphabet"]) for _ in range(size))
            else:
                size=f["length"] if "length" in f else c[f["length_from"]]
                v=[number() for _ in range(size)]
            c[f["name"]]=v
        yield validate_case(m,c)

def complexity(m,c):
    result=[]
    for f in m["fields"]:
        v=c[f["name"]]
        if type(v) is int: result.append(v-f["min"])
        elif type(v) is str: result.extend([len(v),sum(f["alphabet"].index(x) for x in v)])
        else: result.extend([len(v),sum(x-f["min"] for x in v)])
    return sum(result)

def smaller(m,c):
    for f in m["fields"]:
        name=f["name"];v=c[name];lo=f["min"]
        if type(v) is int: candidates=[lo,lo+(v-lo)//2]
        elif type(v) is str: candidates=[v[:lo],f["alphabet"][0]*len(v)]
        else: candidates=[[lo]*len(v)]+[v[:i]+[lo]+v[i+1:] for i in range(min(len(v),8))]
        for x in candidates:
            d={**c,name:x}
            for dependent in m["fields"]:
                if dependent.get("length_from")==name and type(x) is int: d[dependent["name"]]=c[dependent["name"]][:x]
            try: validate_case(m,d)
            except ValueError: continue
            if complexity(m,d)<complexity(m,c): yield d

def equal(m,a,b):
    return a.split()==b.split() if m["output"]=="tokens" else a==b

def validate_package(p):
    if type(p) is not dict or set(p)!={"manifest","reference","controls"}: raise ValueError("Expected manifest,reference,controls")
    m=validate_manifest(p["manifest"])
    if type(p["reference"]) is not str or not 1<=len(p["reference"].encode())<=MAX_SOURCE: raise ValueError("Invalid reference")
    if type(p["controls"]) is not list or not 2<=len(p["controls"])<=8: raise ValueError("Supply 2–8 independently known controls")
    for c in p["controls"]:
        if type(c) is not dict or set(c)!={"case","expected"} or type(c["expected"]) is not str or len(c["expected"])>8192: raise ValueError("Invalid control")
        serialize(m,c["case"])
    if len({digest(c["case"]) for c in p["controls"]})!=len(p["controls"]): raise ValueError("Duplicate controls")
    return p

class PackageStore:
    def __init__(self,root): self.root=Path(root)
    def save(self,p):
        validate_package(p); key=digest(p)
        self.root.mkdir(parents=True,exist_ok=True)
        file=self.root/(key+".json")
        if file.exists():
            self.load(key)
        else:
            with file.open("x",encoding="utf-8") as f: json.dump(p,f,ensure_ascii=True,indent=2)
        return key
    def load(self,key):
        if type(key) is not str or not re.fullmatch("[0-9a-f]{64}",key): raise ValueError("Invalid package hash")
        path=self.root/(key+".json")
        if not path.is_file(): raise ValueError("Unknown package")
        p=json.loads(path.read_text(encoding="utf-8"))
        if digest(p)!=key: raise ValueError("Package hash mismatch")
        return validate_package(p)
    def list(self):
        output=[]
        for f in sorted(self.root.glob("*.json")):
            try:
                p=self.load(f.stem);output.append({"key":f.stem,"manifest":p["manifest"]})
            except (ValueError,OSError): continue
        return output
