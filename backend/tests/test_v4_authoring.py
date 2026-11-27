import pytest
from algoxray.v4_authoring import normalize_url,parse_problem,draft_reference
from algoxray.v4_provider import MockProvider,ProviderError

def test_import_allowlist():
    assert normalize_url("https://codeforces.com/contest/371/problem/C")=="https://codeforces.com/problemset/problem/371/C"
    for x in ("http://codeforces.com/problemset/problem/371/C","https://codeforces.com.evil.com/problemset/problem/371/C","https://codeforces.com@127.0.0.1/problemset/problem/371/C","https://codeforces.com/problemset/problem/371/C?x=1"):
        with pytest.raises(ValueError):normalize_url(x)
def test_parse():
    r=parse_problem('<div class="problem-statement"><div class="title">Sum</div><p>Read n.</p><div class="input"><pre>1<br>2</pre></div><div class="output"><pre>3</pre></div><script>BAD</script></div><p>OUTSIDE</p>',"source")
    assert r["samples"]==[{"stdin":"1\n2","stdout":"3"}]
    assert "BAD" not in r["statement"] and "OUTSIDE" not in r["statement"]
def test_reference_unapproved():
    m={"id":"x","title":"X","statement":"Read n","fields":[{"name":"n","kind":"int","min":1,"max":9}],"lines":[["n"]],"output":"tokens"}
    r=draft_reference(MockProvider({"reference":"print(input())","rationale":"proposal"}),m)
    assert r["executed"] is False and r["status"]=="reference_unreviewed"
    with pytest.raises(ProviderError):draft_reference(MockProvider({"reference":"","rationale":"uncertain"}),m)
