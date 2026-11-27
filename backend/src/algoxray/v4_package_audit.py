"""Finite enumeration and distinct-reference agreement; not a proof of independence."""
import hashlib,itertools,time
from .v4_contracts import validate_package,validate_case,serialize,digest,equal,dimension
from .v4_engine import oracle
from .v4_isolation import execute_stdio

def small_cases(m,limit):
    """Enumerate only when a conservative upper bound fits; never materialize huge ranges."""
    upper=1;prior={}
    for f in m["fields"]:
        span=f["max"]-f["min"]+1
        if f["kind"]=="int":size=span
        elif f["kind"]=="word":
            size=0
            for n in range(f["min"],f["max"]+1):
                if n>16 or len(f["alphabet"])**n>limit:return None
                size+=len(f["alphabet"])**n
                if size>limit:return None
        elif f["kind"]=="ints":
            n=f["length"] if "length" in f else prior[f["length_from"]]["max"]
            if n>16 or span>limit:return None
            size=span**n
        else:
            n=(f["rows"] if "rows" in f else prior[f["rows_from"]]["max"])*(f["cols"] if "cols" in f else prior[f["cols_from"]]["max"])
            if n>16 or span>limit:return None
            size=span**n
        upper*=size;prior[f["name"]]=f
        if upper>limit:return None
    out=[]
    def walk(i,c):
        if i==len(m["fields"]):out.append(validate_case(m,dict(c)));return
        f=m["fields"][i]
        if f["kind"]=="int":values=range(f["min"],f["max"]+1)
        elif f["kind"]=="word":values=("".join(x) for n in range(f["min"],f["max"]+1) for x in itertools.product(f["alphabet"],repeat=n))
        elif f["kind"]=="ints":
            n=f["length"] if "length" in f else c[f["length_from"]]
            values=(list(x) for x in itertools.product(range(f["min"],f["max"]+1),repeat=n))
        else:
            rows,cols=dimension(f,"rows",c),dimension(f,"cols",c)
            values=([list(x[r*cols:(r+1)*cols]) for r in range(rows)] for x in itertools.product(range(f["min"],f["max"]+1),repeat=rows*cols))
        for value in values:
            c[f["name"]]=value;walk(i+1,c)
        c.pop(f["name"],None)
    walk(0,{})
    return out

def audit_package(p,limit=16,run=execute_stdio):
    validate_package(p)
    if type(limit) is not int or not 2<=limit<=32:raise ValueError("Invalid audit case budget")
    m=p["manifest"];checks=[];seen=set();start=time.monotonic()
    enumeration=small_cases(m,limit) if "reference_alt" in p else None
    cases=[c["case"] for c in p["controls"]]+(enumeration or [])
    timed_out=False
    for case in cases:
        key=digest(case)
        if key in seen:continue
        if len(checks)>=limit or time.monotonic()-start>45:timed_out=True;break
        seen.add(key);stdin=serialize(m,case)
        result=oracle(p,stdin,lambda src,text,trace:run(src,text,trace_limit=trace))
        known=next((c["expected"] for c in p["controls"] if c["case"]==case),None)
        match=result["status"]=="ok" and (known is None or equal(m,result["stdout"],known))
        checks.append({"case":case,"status":result["status"],"agreed":match})
        if not match:break
    passed=bool(checks) and all(c["agreed"] for c in checks)
    exhaustive=enumeration is not None and not timed_out and len(seen)==len(enumeration) and passed
    return {"status":"reference_disagreement_or_failure" if not passed else "budget_exhausted" if timed_out else "finite_domain_agreement" if exhaustive else "bounded_reference_agreement" if "reference_alt" in p else "controls_only_no_second_reference",
            "package_sha256":digest(p),"reference_sha256":hashlib.sha256(p["reference"].encode()).hexdigest(),
            "alternative_sha256":hashlib.sha256(p["reference_alt"].encode()).hexdigest() if "reference_alt" in p else None,
            "checks":checks,"enumeration_complete":exhaustive,"case_budget":limit,
            "scope":"Agreement with owner-supplied controls and optional distinct reference. Source independence and full correctness are not proven."}
