"""Declarative, bounded stdin grammar; packages are data, not host plugins."""
import hashlib,json,random,re,math
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from .v4_isolation import MAX_INPUT,MAX_SOURCE

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def validate_manifest(m):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        return v2.validate_manifest(m)
    if type(m) is not dict or not {"id","title","statement","fields","lines","output"}<=set(m)<={"id","title","statement","fields","lines","output","tolerance"}:
        raise ValueError("Expected id,title,statement,fields,lines,output")
    if type(m["id"]) is not str or not re.fullmatch("[a-z0-9_]{1,60}",m["id"]): raise ValueError("Invalid id")
    for k,cap in (("title",120),("statement",8000)):
        if type(m[k]) is not str or not 1<=len(m[k])<=cap: raise ValueError("Invalid "+k)
    if m["output"] not in ("tokens","exact","unordered_tokens","float_tokens"): raise ValueError("Unsupported output policy")
    if m["output"]=="float_tokens":
        tolerance=m.get("tolerance")
        if type(tolerance) is not dict or set(tolerance)!={"abs","rel"} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=.01 for v in tolerance.values()):
            raise ValueError("Supply explicit finite abs/rel tolerances in [0,.01]")
    elif "tolerance" in m:raise ValueError("Tolerance is only supported by float_tokens")
    if type(m["fields"]) is not list or not 1<=len(m["fields"])<=16: raise ValueError("Invalid fields")
    prior={}
    for f in m["fields"]:
        if type(f) is not dict or type(f.get("name")) is not str or not re.fullmatch("[a-z][a-z0-9_]{0,30}",f["name"]) or f["name"] in prior: raise ValueError("Invalid field name")
        k=f.get("kind")
        base={"name","kind","min","max"}
        if k=="int":
            if set(f)!=base or type(f["min"]) is not int or type(f["max"]) is not int or not -10**15<=f["min"]<=f["max"]<=10**15: raise ValueError("Invalid integer bounds")
        elif k=="word":
            if set(f)!=base|{"alphabet"} or type(f["min"]) is not int or type(f["max"]) is not int or not 0<=f["min"]<=f["max"]<=100 or type(f["alphabet"]) is not str or not re.fullmatch("[a-zA-Z0-9]+",f["alphabet"]) or len(set(f["alphabet"]))!=len(f["alphabet"]): raise ValueError("Invalid word bounds")
        elif k=="ints":
            if set(f) not in (base|{"length"},base|{"length_from"}) or type(f["min"]) is not int or type(f["max"]) is not int or not -10**15<=f["min"]<=f["max"]<=10**15: raise ValueError("Invalid list bounds")
            if "length" in f:
                if type(f["length"]) is not int or not 0<=f["length"]<=100: raise ValueError("Invalid list length")
            else:
                p=prior.get(f["length_from"]) if type(f["length_from"]) is str else None
                if not p or p["kind"]!="int" or not 0<=p["min"]<=p["max"]<=100: raise ValueError("Invalid dependent length")
        elif k=="matrix":
            if not base<=set(f) or set(f)-base-{"rows","rows_from","cols","cols_from"} or type(f["min"]) is not int or type(f["max"]) is not int or not -10**15<=f["min"]<=f["max"]<=10**15:raise ValueError("Invalid matrix bounds")
            for axis in ("rows","cols"):
                if (axis in f)==(axis+"_from" in f):raise ValueError("Specify exactly one matrix dimension")
                if axis in f:
                    if type(f[axis]) is not int or not 1<=f[axis]<=32:raise ValueError("Invalid matrix dimension")
                else:
                    p=prior.get(f[axis+"_from"]) if type(f[axis+"_from"]) is str else None
                    if not p or p["kind"]!="int" or not 1<=p["min"]<=p["max"]<=32:raise ValueError("Invalid dependent dimension")
        else: raise ValueError("Unsupported field kind")
        prior[f["name"]]=f
    lines=m["lines"]
    if type(lines) is not list or not lines or any(type(row) is not list or not row or any(type(n) is not str for n in row) for row in lines):
        raise ValueError("Invalid lines")
    flat=[n for row in lines for n in row]
    if flat!=list(prior): raise ValueError("Lines must list every field exactly once in field order")
    for row in lines:
        if any(prior[n]["kind"]=="matrix" for n in row) and len(row)!=1:raise ValueError("Matrix must occupy its own line group")
    # Worst-case encoded size: do not admit a grammar that can generate oversized inputs.
    total=0
    for f in m["fields"]:
        width=max(len(str(f["min"])),len(str(f["max"])))+1
        if f["kind"]=="int":total+=width
        elif f["kind"]=="word":total+=f["max"]+1
        elif f["kind"]=="ints":total+=width*(f["length"] if "length" in f else prior[f["length_from"]]["max"])
        else:
            sizes=[f[a] if a in f else prior[f[a+"_from"]]["max"] for a in ("rows","cols")]
            total+=width*sizes[0]*sizes[1]
    if total>MAX_INPUT:raise ValueError("Maximum input size exceeds worker budget")
    return m

def dimension(f,axis,c):return f[axis] if axis in f else c[f[axis+"_from"]]

def validate_case(m,case):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        return v2.validate_case(m,case)
    if type(case) is not dict or set(case)!={f["name"] for f in m["fields"]}: raise ValueError("Wrong case fields")
    for f in m["fields"]:
        v=case[f["name"]]; lo,hi=f["min"],f["max"]
        if f["kind"]=="int": ok=type(v) is int and lo<=v<=hi
        elif f["kind"]=="word": ok=type(v) is str and lo<=len(v)<=hi and all(x in f["alphabet"] for x in v)
        elif f["kind"]=="matrix":
            ok=type(v) is list and len(v)==dimension(f,"rows",case) and all(type(row) is list and len(row)==dimension(f,"cols",case) and all(type(x) is int and lo<=x<=hi for x in row) for row in v)
        else:
            size=f["length"] if "length" in f else case[f["length_from"]]
            ok=type(v) is list and len(v)==size and all(type(x) is int and lo<=x<=hi for x in v)
        if not ok: raise ValueError("Illegal "+f["name"])
    return case

def serialize(m,case):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        return v2.serialize(m,case)
    validate_case(m,case)
    def token(v):
        if type(v) is list and v and type(v[0]) is list:return "\n".join(" ".join(map(str,row)) for row in v)
        return " ".join(map(str,v)) if type(v) is list else str(v)
    s="\n".join(" ".join(token(case[n]) for n in line) for line in m["lines"])+"\n"
    if len(s.encode())>MAX_INPUT: raise ValueError("Input too large")
    return s

def generate(m,seed,count):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        yield from v2.generate(m,seed,count);return
    rng=random.Random(seed)
    for i in range(count):
        c={}
        for f in m["fields"]:
            lo,hi=f["min"],f["max"]
            def number(): return lo if i==0 else hi if i==1 else rng.choice([lo,hi,rng.randint(lo,hi)])
            if f["kind"]=="int": v=number()
            elif f["kind"]=="word":
                size=number(); v="".join(rng.choice(f["alphabet"]) for _ in range(size))
            elif f["kind"]=="matrix":v=[[number() for _ in range(dimension(f,"cols",c))] for _ in range(dimension(f,"rows",c))]
            else:
                size=f["length"] if "length" in f else c[f["length_from"]]
                v=[number() for _ in range(size)]
            c[f["name"]]=v
        yield validate_case(m,c)

def complexity(m,c):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        return v2.complexity(m,c)
    """Lexicographic structural size, then magnitude of values."""
    from .v4_shrinking import complexity as measure
    return measure(m,c)

def smaller(m,c):
    if type(m) is dict and "schema_version" in m:
        from . import v4_spec_v2 as v2
        yield from v2.smaller(m,c);return
    from .v4_shrinking import candidates
    yield from candidates(m,c)

def equal(m,a,b):
    if m["output"]=="tokens":return a.split()==b.split()
    if m["output"]=="unordered_tokens":return Counter(a.split())==Counter(b.split())
    if m["output"]=="exact":return a==b
    if m["output"]!="float_tokens":return False
    left,right=a.split(),b.split()
    if len(left)!=len(right):return False
    def number(token):
        if len(token)>128 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?",token):raise ValueError("Unsupported numeric token")
        value=Decimal(token)
        if not value.is_finite() or abs(value.as_tuple().exponent)>256:raise ValueError("Unsupported numeric magnitude")
        return value
    try:
        with localcontext() as ctx:
            ctx.prec=512
            absolute=Decimal(str(m["tolerance"]["abs"]));relative=Decimal(str(m["tolerance"]["rel"]))
            return all(abs(number(x)-number(y))<=max(absolute,relative*max(abs(number(x)),abs(number(y)))) for x,y in zip(left,right))
    except (ValueError,InvalidOperation):return False

def validate_package(p):
    if type(p) is not dict or not {"manifest","reference","controls"}<=set(p)<={"manifest","reference","controls","reference_alt","provenance","intake","checker"}: raise ValueError("Expected manifest,reference,controls")
    m=validate_manifest(p["manifest"])
    if "checker" in p:
        from .v4_checker import validate_checker,semantic_answer
        validate_checker(m,p["checker"])
    if type(p["reference"]) is not str or not 1<=len(p["reference"].encode())<=MAX_SOURCE: raise ValueError("Invalid reference")
    if "reference_alt" in p and (type(p["reference_alt"]) is not str or not 1<=len(p["reference_alt"].encode())<=MAX_SOURCE or p["reference_alt"]==p["reference"]):raise ValueError("Alternative reference must be distinct and bounded")
    if type(p["controls"]) is not list or not 2<=len(p["controls"])<=8: raise ValueError("Supply 2–8 independently known controls")
    for c in p["controls"]:
        if type(c) is not dict or set(c)!={"case","expected"} or type(c["expected"]) is not str or len(c["expected"])>8192: raise ValueError("Invalid control")
        serialize(m,c["case"])
        if "checker" in p and semantic_answer(m,p["checker"],c["case"],c["expected"])["status"]!="accepted":
            raise ValueError("Control violates semantic checker")
    if len({digest(c["case"]) for c in p["controls"]})!=len(p["controls"]): raise ValueError("Duplicate controls")
    if "intake" in p:
        from .v4_intake import validate_intake
        validate_intake(p["intake"],m["statement"])
    if "provenance" in p:
        from .v4_draft_review import validate_provenance
        validate_provenance(p)
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
