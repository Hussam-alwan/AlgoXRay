import json
import httpx
import pytest
from algoxray import v4_groq as g
from algoxray.v4_gemini import provider_for,Ledger
from algoxray.v4_provider import ProviderError

def test_consent():
    with pytest.raises(ProviderError,match="consent"):provider_for(g.MODEL)
    assert provider_for(g.MODEL,True).model==g.MODEL

def test_transport(monkeypatch,tmp_path):
    monkeypatch.setattr(g,"get_key",lambda:"dummy")
    client=httpx.Client
    def handler(req):
        assert str(req.url)=="https://api.groq.com/openai/v1/chat/completions"
        p=json.loads(req.content)
        assert p["model"]==g.MODEL and p["response_format"]["json_schema"]["strict"] is False
        return httpx.Response(200,json={"model":g.MODEL,"choices":[{"finish_reason":"stop","message":{"content":json.dumps({"answer":3})}}],"usage":{"total_tokens":10}})
    monkeypatch.setattr(g.httpx,"Client",lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    p=g.GroqProvider(ledger=Ledger(tmp_path/"budget.db"))
    assert p.propose("diagnosis",{},{"type":"object"})=={"answer":3}
    assert p.usage["total_tokens"]==10
