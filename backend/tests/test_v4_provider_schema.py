import json
import pytest
from algoxray import v4_provider as p


SCHEMA = {"type":"object","properties":{"answer":{"type":"integer"}},
          "required":["answer"],"additionalProperties":False}


def test_ollama_validates_and_records_local_usage(monkeypatch):
    payload = {"answer":3}
    envelope = dict(done=True, done_reason="stop", eval_count=8, eval_duration=1234,
                    total_duration=3000, message={"content":json.dumps(payload)})
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, *args): return json.dumps(envelope).encode()
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:11434/api/chat"
            assert json.loads(request.data)["format"] == SCHEMA
            return Response()
    monkeypatch.setattr(p.urllib.request, "build_opener", lambda *args: Opener())
    provider = p.OllamaProvider()
    assert provider.propose("diagnosis", {}, SCHEMA) == payload
    assert provider.usage["eval_count"] == 8 and provider.usage["elapsed_ms"] >= 0
    assert len(provider.usage["request_id"]) == 32
    envelope["message"]["content"] = '{"answer":3,"invented":true}'
    with pytest.raises(p.ProviderError, match="invalid_model_schema"):
        provider.propose("diagnosis", {}, SCHEMA)
    envelope.update(done_reason="length")
    with pytest.raises(p.ProviderError, match="incomplete"):
        provider.propose("diagnosis", {}, SCHEMA)


@pytest.mark.parametrize("result", [{"answer":True},{"answer":"3"},{}, {"answer":3,"extra":1}])
def test_invalid_values_are_rejected_before_business_use(result):
    with pytest.raises(p.ProviderError, match="invalid_model_schema"):
        p.validated_result(result, SCHEMA)


@pytest.mark.parametrize("adapter", ["v4_gemini","v4_groq","v4_openrouter"])
def test_cloud_adapters_apply_the_same_schema_validation(monkeypatch, tmp_path, adapter):
    import importlib
    from algoxray.v4_gemini import Ledger
    a=importlib.import_module("algoxray."+adapter)
    monkeypatch.setattr(a,"get_key",lambda:"dummy-not-a-secret")
    if adapter=="v4_gemini":
        provider=a.GeminiProvider(ledger=Ledger(tmp_path/"quota.db"))
        envelope={"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":'{"answer":"wrong"}'}]}}]}
    else:
        cls=a.GroqProvider if adapter=="v4_groq" else a.OpenRouterProvider
        provider=cls(ledger=Ledger(tmp_path/"quota.db"))
        envelope={"model":a.MODEL,"choices":[{"finish_reason":"stop","message":{"content":'{"answer":"wrong"}'}}]}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(envelope).encode()
    class Opener:
        def open(self,*args,**kwargs):return Response()
    if adapter=="v4_groq":
        import httpx
        client=httpx.Client
        monkeypatch.setattr(a.httpx,"Client",lambda **kw:client(transport=httpx.MockTransport(
            lambda request:httpx.Response(200,json=envelope)),**kw))
    else:
        monkeypatch.setattr(a.urllib.request,"build_opener",lambda *args:Opener())
    with pytest.raises(p.ProviderError,match="invalid_model_schema"):
        provider.propose("diagnosis",{},SCHEMA)
