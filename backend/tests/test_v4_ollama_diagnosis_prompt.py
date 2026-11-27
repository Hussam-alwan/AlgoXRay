import json
import pytest
from algoxray.v4_provider import OllamaProvider

@pytest.mark.parametrize("task",["diagnosis","repair"])
def test_diagnosis_guidance_is_trusted_system_text_and_does_not_change_other_tasks(monkeypatch,task):
    captured=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,*args):return json.dumps({"done":True,"message":{"content":"{}"}}).encode()
    class Opener:
        def open(self,request,**kwargs):
            captured.append(json.loads(request.data));return Response()
    monkeypatch.setattr("urllib.request.build_opener",lambda *args:Opener())
    OllamaProvider().propose(task,{"source":"UNTRUSTED_SOURCE_INJECTION"},{"type":"object"})
    system=captured[0]["messages"][0]["content"]
    assert "UNTRUSTED_SOURCE_INJECTION" not in system
    assert ("in Arabic" in system)==(task=="diagnosis")
    assert ("at most one" in system)==(task=="diagnosis")
