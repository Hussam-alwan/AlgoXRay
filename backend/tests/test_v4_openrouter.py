import json
import pytest
from algoxray import v4_openrouter as o
from algoxray.v4_gemini import provider_for,Ledger
from algoxray.v4_provider import ProviderError

def test_no_consent_or_paid_model():
    with pytest.raises(ProviderError,match="consent"):provider_for(o.MODEL)
    with pytest.raises(ProviderError,match="unsupported"):provider_for(o.MODEL.removesuffix(":free"),True)

def test_free_wire(monkeypatch,tmp_path):
    monkeypatch.setattr(o,"get_key",lambda:"dummy")
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,*a):return json.dumps({"model":o.MODEL,"choices":[{"finish_reason":"stop","message":{"content":json.dumps({"answer":3})}}],"usage":{"total_tokens":10}}).encode()
    class Open:
        def open(self,req,timeout):
            assert req.full_url=="https://openrouter.ai/api/v1/chat/completions"
            p=json.loads(req.data)
            assert p["model"]==o.MODEL and not p["provider"]["allow_fallbacks"]
            assert p["provider"]["max_price"]=={"prompt":0,"completion":0,"request":0}
            return Response()
    monkeypatch.setattr(o.urllib.request,"build_opener",lambda *a:Open())
    p=o.OpenRouterProvider(ledger=Ledger(tmp_path/"budget.db"))
    assert p.propose("diagnosis",{},{"type":"object"})=={"answer":3}
    assert p.usage["total_tokens"]==10
