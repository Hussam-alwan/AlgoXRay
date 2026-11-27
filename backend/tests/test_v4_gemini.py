import json,urllib.error
import pytest
from algoxray import v4_gemini as g
from algoxray.v4_provider import ProviderError
def test_budget(tmp_path):
    l=g.Ledger(tmp_path/"usage.db")
    for i in range(5):l.reserve(g.MODELS[0],1000+i)
    with pytest.raises(ProviderError,match="budget"):l.reserve(g.MODELS[0],1006)
    l.reserve(g.MODELS[1],1006)
    for i in range(15):l.reserve(g.MODELS[0],1100+i*61)
    with pytest.raises(ProviderError,match="budget"):l.reserve(g.MODELS[0],2100)
    assert l.counts(g.MODELS[0],2100)["local_attempts_24h"]==20
    l.reserve(g.MODELS[0],100000)
def test_provider_explicit_consent():
    with pytest.raises(ProviderError,match="consent"):g.provider_for(g.MODELS[0])
    with pytest.raises(ProviderError,match="unsupported"):g.provider_for("https://bad.example",True)
    assert g.provider_for(g.MODELS[1],True).model==g.MODELS[1]
def test_wire_and_usage(monkeypatch,tmp_path):
    monkeypatch.setattr(g,"get_key",lambda:"not-a-real-key")
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,*a):return json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[{"thought":True,"text":"private"},{"text":"{\"hypotheses\":[],\"facts\":[]}"}]}}],"usageMetadata":{"totalTokenCount":21}}).encode()
    class Open:
        def open(self,req,timeout):
            assert req.full_url=="https://generativelanguage.googleapis.com/v1beta/models/gemini-4-hydrogen:generateContent"
            assert req.get_header("X-goog-api-key")=="not-a-real-key"
            assert json.loads(req.data)["generationConfig"]["responseJsonSchema"]=={"type":"object"}
            return Response()
    monkeypatch.setattr(g.urllib.request,"build_opener",lambda *a:Open())
    p=g.GeminiProvider(ledger=g.Ledger(tmp_path/"usage.db"))
    assert p.propose("diagnosis",{},{"type":"object"})=={"hypotheses":[],"facts":[]}
    assert p.usage["totalTokenCount"]==21
