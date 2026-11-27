import hashlib,json,subprocess,sys
from algoxray.v4_source_structure import source_structure
from algoxray.v4_graph import observed_graph
from algoxray.v4_cfg import output_chain
from algoxray.v4_localization import localize
from algoxray.v4_isolation import GUEST

def guest(source,stdin=""):
    req={"source":source,"stdin":stdin,"seconds":1,"trace_limit":256}
    return json.loads(subprocess.check_output([sys.executable,"-I","-c",GUEST],
        input=(json.dumps(req)+"\n").encode(),timeout=5))

def test_source_identity_utf8_and_ambiguous_line():
    source="é = 1; y = 2\nprint(y)\n"
    tree=source_structure(source,[{"line":1,"event_id":"E1","frame_id":"F1","kind":"line"}])
    assert tree["source_sha256"]==hashlib.sha256(source.encode()).hexdigest()
    assert tree["nodes"]==source_structure(source)["nodes"]
    assignment=[n for n in tree["nodes"] if n["kind"]=="Assign"]
    assert assignment[1]["preview"]=="y = 2"
    assert assignment[1]["source_span"]["column_utf8"]==len("é = 1; ".encode())
    assert tree["event_links"][0]["association"]=="ambiguous_line"
    assert not tree["event_links"][0]["expression_execution_proven"]
    assert len(tree["event_links"][0]["candidate_node_ids"])==2
    assert source_structure("if")["status"]=="syntax_error"
    assert source_structure("\n".join("a=1" for _ in range(300)))["status"]=="partial"

def test_snapshot_collections_bounded():
    source="a=list(range(100))\nd={'x':1,'y':2}\ns={1,2}\nf=1.5\nprint(f)"
    r=guest(source)
    ev=next(e for e in r["events"] if e["kind"]=="line" and e["line"]==5)
    assert ev["locals"]["a"]["truncated"] and ev["locals"]["a"]["size"]==100
    assert len(ev["locals"]["a"]["items"])==24
    assert ev["locals"]["d"]["kind"]=="dict" and ev["locals"]["s"]["order"]=="unspecified"
    assert ev["locals"]["f"]==1.5
    assert ev["snapshot_meta"]["max_collection_items"]==24

def test_bounds_evidence_and_effect_separate():
    source="n=int(input())\na=list(map(int,input().split()))\ntotal=0\nfor i in range(n-1):\n    total += a[i]\nprint(total)\n"
    execution=guest(source,"4\n1 2 3 4\n")
    graph=observed_graph(execution["events"],source)
    graph["output_chain"]=output_chain(source,execution,graph)
    report=localize(source,{"kind":"wrong_answer","student":execution},graph)
    assert execution["stdout"]=="6\n"
    assert report["effect_site"]["line"]==6
    assert report["ranked"][0]["line"]==4
    assert report["loop_bounds"][0]["omitted_indices"]==[3]
    assert report["loop_bounds"][0]["observed_read_indices"]==[0,1,2]
    assert report["causal_fault_proven"] is False
    # A correct program can intentionally skip array elements. Do not mark it
    # as a wrong-answer candidate in a standalone observation.
    observation=localize(source,{"student":execution},graph)
    assert observation["loop_bounds"]==[]
    assert all(r["line"]!=4 for r in observation["ranked"])

def test_no_fabricated_missing_line():
    source="print(0)"
    execution=guest(source)
    graph=observed_graph(execution["events"],source)
    r=localize(source,{"kind":"wrong_answer","student":execution},graph)
    assert r["status"]=="insufficient_evidence" and r["ranked"]==[]
