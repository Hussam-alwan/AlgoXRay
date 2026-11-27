"""Bounded version 2 stdin grammar: repeated bodies, list constraints, scalar relations.

Legacy contracts retain their original shape. Aggregate cross-case constraints
and arbitrary predicates are unsupported, not silently approximated.
"""
import random

VERSION=2
MAX_CASES=16
FLAGS=("sorted","unique")
OPS={"le","lt","ge","gt","eq"}

def legacy_body(m):
    return {**{k:v for k,v in m.items() if k not in ("schema_version","repeat","relations","fields")},
            "fields":[{k:v for k,v in f.items() if k not in FLAGS} for f in m["fields"]]}

def bounds(m,f,values):
    low,high=f["min"],f["max"]
    for r in m.get("relations",[]):
        if r["right"]!=f["name"]:continue
        x=values[r["left"]];op=r["op"]
        if op in ("le","lt","eq"):low=max(low,x+(op=="lt"))
        if op in ("ge","gt","eq"):high=min(high,x-(op=="gt"))
    return low,high

def validate_manifest(m):
    from .v4_contracts import validate_manifest as legacy_validate
    from .v4_isolation import MAX_INPUT
    if type(m.get("schema_version")) is not int or m["schema_version"]!=VERSION:
        raise ValueError("Unsupported schema_version; use legacy or 2")
    if type(m.get("fields")) is not list or any(type(f) is not dict for f in m["fields"]):
        raise ValueError("Invalid fields")
    legacy_validate(legacy_body(m))
    prior={}
    for f in m["fields"]:
        if any(k in f for k in FLAGS):
            if f["kind"]!="ints" or any(type(f[k]) is not bool for k in FLAGS if k in f):
                raise ValueError("sorted/unique require integer list and boolean flags")
            if f.get("unique"):
                largest=f["length"] if "length" in f else prior[f["length_from"]]["max"]
                if largest>f["max"]-f["min"]+1:
                    raise ValueError("Unique list length exceeds available values")
        prior[f["name"]]=f
    repeat=m.get("repeat")
    if "repeat" in m:
        if type(repeat) is not dict or set(repeat)!={"min","max"} or any(type(v) is not int for v in repeat.values()) or not 1<=repeat["min"]<=repeat["max"]<=MAX_CASES:
            raise ValueError("repeat requires min/max within 1..16")
        # Unordered tokens can hide answers swapped between cases.
        if m["output"]=="unordered_tokens":
            raise ValueError("Repeated cases require order-preserving output policy")
    relations=m.get("relations",[])
    if type(relations) is not list or len(relations)>16:
        raise ValueError("Invalid scalar relations")
    positions={f["name"]:i for i,f in enumerate(m["fields"])}
    seen=set()
    for r in relations:
        if (type(r) is not dict or set(r)!={"left","right","op"} or
                any(type(x) is not str for x in r.values()) or r["op"] not in OPS or
                r["left"] not in prior or r["right"] not in prior or
                prior[r["left"]]["kind"]!="int" or prior[r["right"]]["kind"]!="int" or
                positions[r["left"]]>=positions[r["right"]]):
            raise ValueError("Relations must compare earlier and later integer fields")
        key=(r["left"],r["right"],r["op"])
        if key in seen:raise ValueError("Duplicate relation")
        seen.add(key)
    # Conservative totality: every earlier allowed value admits a later value.
    for f in m["fields"]:
        if f["kind"]!="int":continue
        incoming=[r for r in relations if r["right"]==f["name"]]
        if len(incoming)==1 and incoming[0]["op"]=="eq":
            source=prior[incoming[0]["left"]]
            if source["min"]>=f["min"] and source["max"]<=f["max"]:continue
        low,high=f["min"],f["max"]
        for r in incoming:
            source=prior[r["left"]]
            if r["op"] in ("le","lt","eq"):low=max(low,source["max"]+(r["op"]=="lt"))
            if r["op"] in ("ge","gt","eq"):high=min(high,source["min"]-(r["op"]=="gt"))
        if low>high:raise ValueError("Relations do not guarantee a constructible interval; revise bounds")
    # Conservative serialized bytes including empty list lines and separators.
    total=len(m["lines"])+len(m["fields"])
    for f in m["fields"]:
        width=max(len(str(f["min"])),len(str(f["max"])))+1
        if f["kind"]=="int":total+=width
        elif f["kind"]=="word":total+=f["max"]
        elif f["kind"]=="ints":total+=width*(f["length"] if "length" in f else prior[f["length_from"]]["max"])
        else:
            dims=[f[a] if a in f else prior[f[a+"_from"]]["max"] for a in ("rows","cols")]
            total+=width*dims[0]*dims[1]+dims[0]
    if repeat is not None:total=total*repeat["max"]+len(str(repeat["max"]))+1
    if total>MAX_INPUT:raise ValueError("Maximum input size exceeds worker budget")
    return m

def validate_body(m,c):
    from .v4_contracts import validate_case as legacy_validate
    legacy_validate(legacy_body(m),c)
    for f in m["fields"]:
        v=c[f["name"]]
        if f["kind"]=="ints":
            if f.get("sorted") and any(a>b for a,b in zip(v,v[1:])):raise ValueError("List must be sorted: "+f["name"])
            if f.get("unique") and len(set(v))!=len(v):raise ValueError("List must be unique: "+f["name"])
        if f["kind"]=="int":
            lo,hi=bounds(m,f,c)
            if not lo<=v<=hi:raise ValueError("Scalar relation violated: "+f["name"])
    return c

def validate_case(m,c):
    if "repeat" not in m:return validate_body(m,c)
    if type(c) is not dict or set(c)!={"t","cases"} or type(c["t"]) is not int or type(c["cases"]) is not list:
        raise ValueError("Repeated case requires t and cases")
    if c["t"]!=len(c["cases"]) or not m["repeat"]["min"]<=c["t"]<=m["repeat"]["max"]:
        raise ValueError("Invalid repeated case count")
    for item in c["cases"]:validate_body(m,item)
    return c

def serialize(m,c):
    from .v4_contracts import serialize as legacy_serialize
    from .v4_isolation import MAX_INPUT
    validate_case(m,c);base=legacy_body(m)
    if "repeat" not in m:return legacy_serialize(base,c)
    s=str(c["t"])+"\n"+"".join(legacy_serialize(base,x) for x in c["cases"])
    if len(s.encode("utf-8"))>MAX_INPUT:raise ValueError("Input too large")
    return s

def generate(m,seed,count):
    from .v4_contracts import dimension
    rng=random.Random(seed)
    def number(lo,hi,i):
        return lo if i==0 else hi if i==1 else rng.choice([lo,hi,rng.randint(lo,hi)])
    def one(i):
        c={}
        for f in m["fields"]:
            lo,hi=f["min"],f["max"];kind=f["kind"]
            if kind=="int":v=number(*bounds(m,f,c),i)
            elif kind=="word":v="".join(rng.choice(f["alphabet"]) for _ in range(number(lo,hi,i)))
            elif kind=="matrix":
                v=[[number(lo,hi,i) for _ in range(dimension(f,"cols",c))] for _ in range(dimension(f,"rows",c))]
            else:
                n=f["length"] if "length" in f else c[f["length_from"]]
                if f.get("unique"):
                    v=list(range(lo,lo+n)) if i==0 else list(range(hi-n+1,hi+1)) if i==1 else rng.sample(range(lo,hi+1),n)
                    if not f.get("sorted") and i>1:rng.shuffle(v)
                else:v=[number(lo,hi,i) for _ in range(n)]
                if f.get("sorted"):v.sort()
            c[f["name"]]=v
        return c
    for i in range(count):
        if "repeat" in m:
            t=number(m["repeat"]["min"],m["repeat"]["max"],i)
            c={"t":t,"cases":[one(i) for _ in range(t)]}
        else:c=one(i)
        yield validate_case(m,c)

def strategy(m):
    from hypothesis import strategies as st
    from .v4_contracts import dimension
    @st.composite
    def one(draw):
        c={}
        for f in m["fields"]:
            lo,hi=f["min"],f["max"];kind=f["kind"];numbers=st.integers(lo,hi)
            if kind=="int":v=draw(st.integers(*bounds(m,f,c)))
            elif kind=="word":v=draw(st.text(alphabet=f["alphabet"],min_size=lo,max_size=hi))
            elif kind=="matrix":
                rows,cols=dimension(f,"rows",c),dimension(f,"cols",c)
                v=draw(st.lists(st.lists(numbers,min_size=cols,max_size=cols),min_size=rows,max_size=rows))
            else:
                n=f["length"] if "length" in f else c[f["length_from"]]
                v=draw(st.lists(numbers,min_size=n,max_size=n,unique=f.get("unique",False)))
                if f.get("sorted"):v.sort()
            c[f["name"]]=v
        return c
    if "repeat" not in m:return one()
    @st.composite
    def repeated(draw):
        t=draw(st.integers(m["repeat"]["min"],m["repeat"]["max"]))
        return {"t":t,"cases":draw(st.lists(one(),min_size=t,max_size=t))}
    return repeated()

def complexity(m,c):
    from .v4_shrinking import complexity as measure
    base=legacy_body(m)
    if "repeat" not in m:return measure(base,c)
    sizes=[measure(base,x) for x in c["cases"]]
    return (c["t"],sum(x[0] for x in sizes),sum(x[1] for x in sizes))

def smaller(m,c):
    from .v4_shrinking import candidates,deletion_windows
    from .v4_contracts import digest
    validate_case(m,c);base=legacy_body(m)
    def options():
        if "repeat" not in m:
            yield from candidates(base,c);return
        for a,b in deletion_windows(c["t"],m["repeat"]["min"]):
            cases=c["cases"][:a]+c["cases"][b:]
            yield {"t":len(cases),"cases":cases}
        for i,item in enumerate(c["cases"]):
            for x in candidates(base,item):
                yield {"t":c["t"],"cases":c["cases"][:i]+[x]+c["cases"][i+1:]}
    seen=set();original=complexity(m,c)
    for x in options():
        try:serialize(m,x)
        except ValueError:continue
        key=digest(x)
        if key not in seen and complexity(m,x)<original:
            seen.add(key);yield x

def case_schema(m):
    from .v4_guidance import case_schema as legacy_schema
    schema=legacy_schema(legacy_body(m))
    for f in m["fields"]:
        if f["kind"]=="ints" and f.get("unique"):
            schema["properties"][f["name"]]["uniqueItems"]=True
    if "repeat" not in m:return schema
    r=m["repeat"]
    return {"type":"object","properties":{"t":{"type":"integer","minimum":r["min"],"maximum":r["max"]},
            "cases":{"type":"array","items":schema,"minItems":r["min"],"maxItems":r["max"]}},
            "required":["t","cases"],"additionalProperties":False}

def capabilities():
    return {"schema_versions":[1,2],"legacy_version":"implicit when schema_version is absent",
            "field_kinds":["int","word","ints","matrix"],
            "v2":{"repeat":{"min":1,"max":MAX_CASES,"shape":{"t":"integer","cases":"array of body cases"}},
                  "list_flags":["sorted","unique"],"scalar_relation_ops":sorted(OPS),
                  "relations":"Earlier integer compared to later integer; conservative constructible intervals.",
                  "generation":["boundary_random","hypothesis"],"shrinking":"Validate every candidate."},
            "semantic_checkers":[{"kind":"two_sum_indices","version":1,"scope":"Single body, two distinct indices summing to target or explicit no-solution token; owner review required."}],
            "unsupported":["nested repeats","cross-case aggregate constraints","arbitrary predicates",
                           "graph/tree invariants","interactive problems","arbitrary semantic checker code"],
            "review_required":True}
