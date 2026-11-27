"""Bounded legal test generation and model-proposed prediction checks."""
from hypothesis import given,seed as hyp_seed,settings,Phase,strategies as st
from .v4_contracts import serialize,digest,dimension
from .v4_provider import ProviderError

def hypothesis_cases(m,seed,count):
    @st.composite
    def cases(draw):
        c={}
        for f in m["fields"]:
            lo,hi=f["min"],f["max"];number=st.integers(lo,hi)
            if f["kind"]=="int":v=draw(number)
            elif f["kind"]=="word":v=draw(st.text(alphabet=f["alphabet"],min_size=lo,max_size=hi))
            elif f["kind"]=="matrix":
                rows,cols=dimension(f,"rows",c),dimension(f,"cols",c)
                v=draw(st.lists(st.lists(number,min_size=cols,max_size=cols),min_size=rows,max_size=rows))
            else:
                length=f["length"] if "length" in f else c[f["length_from"]]
                v=draw(st.lists(number,min_size=length,max_size=length))
            c[f["name"]]=v
        return c
    output=[]
    @hyp_seed(seed)
    @settings(max_examples=count,deadline=None,database=None,phases=(Phase.generate,))
    @given(cases())
    def collect(c):
        serialize(m,c);output.append(c)
    collect()
    return output[:count]

def case_schema(m):
    properties={}
    for f in m["fields"]:
        number={"type":"integer","minimum":f["min"],"maximum":f["max"]}
        if f["kind"]=="int":v=number
        elif f["kind"]=="word":v={"type":"string","minLength":f["min"],"maxLength":f["max"]}
        elif f["kind"]=="matrix":v={"type":"array","items":{"type":"array","items":number,"maxItems":32},"maxItems":32}
        else:v={"type":"array","items":number,"maxItems":100}
        properties[f["name"]]=v
    return {"type":"object","properties":properties,"required":list(properties),"additionalProperties":False}

def suggestions(provider,m,source,witness=None,hypotheses=()):
    schema={"type":"object","properties":{"proposals":{"type":"array","maxItems":3,"items":{"type":"object","properties":{"case":case_schema(m),"prediction":{"type":"string","enum":["match","mismatch"]},"hypothesis_index":{"type":"integer","minimum":-1,"maximum":2}},"required":["case","prediction","hypothesis_index"],"additionalProperties":False}}},"required":["proposals"],"additionalProperties":False}
    data={"manifest":m,"source":source,"witness":witness,"hypotheses":list(hypotheses),"instruction":"Propose up to 3 different legal cases to test predicted match or mismatch relative to reference. Use hypothesis_index -1 for general search; otherwise index a supported hypothesis. No code or expected output. Include exact field lengths."}
    r=provider.propose("case_suggestions",data,schema)
    if type(r) is not dict or set(r)!={"proposals"} or type(r["proposals"]) is not list or len(r["proposals"])>3:raise ProviderError("invalid_case_suggestions")
    valid=[];rejected=0;seen=set()
    for p in r["proposals"]:
        try:
            if type(p) is not dict or set(p)!={"case","prediction","hypothesis_index"} or p["prediction"] not in ("match","mismatch") or type(p["hypothesis_index"]) is not int or not -1<=p["hypothesis_index"]<len(hypotheses):raise ValueError()
            if p["hypothesis_index"]>=0 and hypotheses[p["hypothesis_index"]].get("status")!="hypothesis":raise ValueError()
            serialize(m,p["case"]);k=digest(p["case"])
            if k in seen:raise ValueError()
            seen.add(k);valid.append(p)
        except (ValueError,TypeError,KeyError):rejected+=1
    return valid,rejected

def classify_probe(proposal,result):
    kind=result["kind"]
    actual="match" if kind=="match" else "mismatch" if kind in ("wrong_answer","exception") else None
    return {**proposal,"observed":actual,"status":"inconclusive" if actual is None else "prediction_supported" if actual==proposal["prediction"] else "prediction_contradicted","result":result,"causal_verified":False}
