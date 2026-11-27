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

def test_rate_limit_has_no_automatic_retry(monkeypatch,tmp_path):
    monkeypatch.setattr(g,"get_key",lambda:"test-key")
    class Open:
        def open(self,req,timeout):
            raise urllib.error.HTTPError(req.full_url,429,"rate limit",{},None)
    monkeypatch.setattr(g.urllib.request,"build_opener",lambda *a:Open())
    p=g.GeminiProvider(ledger=g.Ledger(tmp_path/"usage.db"))
    with pytest.raises(ProviderError,match="gemini_quota_or_rate_limit"):p.propose("diagnosis",{},{"type":"object"})
    assert p.ledger.counts(p.model)["local_attempts_24h"]==1

def test_draft_requires_cloud_consent_and_preserves_statement(monkeypatch):
    from fastapi.testclient import TestClient
    from algoxray.api import app
    from algoxray import v4_api
    from algoxray.v4_provider import MockProvider
    with TestClient(app) as c:
        token=c.get("/api/session").json()["custom_code_token"]
        headers={"X-AlgoXRay-Token":token}
        body={"statement":"Read one integer n between 1 and 9.","model":g.MODELS[0]}
        assert c.post("/api/v4/packages/draft",json=body,headers=headers).status_code==403
        proposed={"manifest":{"id":"twice","title":"Double","statement":"rewritten","fields":[{"name":"n","kind":"int","min":1,"max":9}],"lines":[["n"]],"output":"tokens"}}
        def provider(model,consent):
            assert model==g.MODELS[0] and consent
            return MockProvider(proposed)
        monkeypatch.setattr(v4_api,"provider_for",provider)
        r=c.post("/api/v4/packages/draft",json={**body,"cloud_consent":True},headers=headers)
        assert r.status_code==200 and r.json()["status"]=="draft_unreviewed"
        assert r.json()["manifest"]["statement"]==body["statement"]
