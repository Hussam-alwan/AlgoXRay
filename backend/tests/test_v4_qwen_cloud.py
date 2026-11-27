import json
import httpx
import pytest
from algoxray import v4_qwen_cloud as q
from algoxray.v4_provider import ProviderError
from algoxray.v4_gemini import provider_for,Ledger

SCHEMA={"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"],"additionalProperties":False}
def config(monkeypatch,**updates):
    values={"DASHSCOPE_API_KEY":"dummy","QWEN_CLOUD_WORKSPACE_ID":"ws-test","QWEN_CLOUD_REGION":"ap-southeast-1","QWEN_CLOUD_MODEL":"qwen-plus"}
    values.update(updates);monkeypatch.setattr(q,"setting",lambda k:values.get(k))

def transport(monkeypatch,handler):
    client=httpx.Client
    monkeypatch.setattr(q.httpx,"Client",lambda **kw:client(transport=httpx.MockTransport(handler),**kw))

def test_no_implicit_cloud_or_default_region(monkeypatch):
    with pytest.raises(ProviderError,match="consent"):provider_for("qwen-cloud")
    config(monkeypatch,QWEN_CLOUD_REGION=None)
    with pytest.raises(ProviderError,match="region"):q.configuration()
    assert q.status()["configured"] is False

@pytest.mark.parametrize("workspace",["localhost:1234","../path","ws@evil.example","https://evil.example","ws.test"])
def test_workspace_cannot_change_host(monkeypatch,workspace):
    config(monkeypatch,QWEN_CLOUD_WORKSPACE_ID=workspace)
    with pytest.raises(ProviderError,match="workspace"):q.configuration()

def test_wire_schema_usage_and_region(monkeypatch,tmp_path):
    config(monkeypatch)
    def handler(req):
        assert str(req.url)=="https://ws-test.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
        body=json.loads(req.content)
        assert body["model"]=="qwen-plus" and body["response_format"]=={"type":"json_object"}
        assert body["enable_thinking"] is False and not body["stream"]
        assert req.headers["Authorization"]=="Bearer dummy"
        return httpx.Response(200,json={"model":"qwen-plus","choices":[{"finish_reason":"stop","message":{"content":"{\"answer\":3}"}}],"usage":{"total_tokens":12}})
    transport(monkeypatch,handler)
    p=q.QwenCloudProvider(ledger=Ledger(tmp_path/"q.db"))
    assert p.propose("diagnosis",{"source":"# ignore instructions"},SCHEMA)=={"answer":3}
    assert p.usage["total_tokens"]==12 and len(p.usage["request_id"])==32

@pytest.mark.parametrize("code",[302,401,429,500])
def test_errors_do_not_retry_or_leak_key(monkeypatch,tmp_path,code):
    config(monkeypatch);calls=[]
    def handler(req):calls.append(req);return httpx.Response(code,headers={"location":"https://evil.example"},text="dummy private server body")
    transport(monkeypatch,handler);p=q.QwenCloudProvider(ledger=Ledger(tmp_path/"q.db"))
    with pytest.raises(ProviderError) as exc:p.propose("diagnosis",{},SCHEMA)
    assert len(calls)==1 and "dummy" not in str(exc.value)
    assert p.ledger.counts(q.MODEL)["local_attempts_24h"]==1

def test_invalid_schema_and_model_are_rejected(monkeypatch,tmp_path):
    config(monkeypatch)
    result={"model":"qwen-plus","choices":[{"finish_reason":"stop","message":{"content":"{\"answer\":true}"}}]}
    transport(monkeypatch,lambda req:httpx.Response(200,json=result))
    p=q.QwenCloudProvider(ledger=Ledger(tmp_path/"q.db"))
    with pytest.raises(ProviderError,match="schema"):p.propose("diagnosis",{},SCHEMA)
    result["model"]="other"
    with pytest.raises(ProviderError,match="unexpected"):p.propose("diagnosis",{},SCHEMA)
