import threading,time
import pytest
from algoxray.v4_provider import bounded_propose,ProviderError
from algoxray.v4_repair import RepairStore
def test_inference_cancellation_abandons_result():
    done=threading.Event();cancel=threading.Event()
    class P:
        def propose(self,*a):
            done.wait(2);return {}
    timer=threading.Timer(.08,cancel.set);timer.start()
    try:
        with pytest.raises(ProviderError,match="cancelled"):bounded_propose(P(),"diagnosis",{}, {},cancel)
    finally:done.set();timer.join()
def test_repair_history(tmp_path):
    store=RepairStore(tmp_path)
    key=store.save("package","old","new",{"status":"passed_named_tests"})
    assert store.load(key)["source"]=="old"
    assert store.list("package")[0]["key"]==key
    (tmp_path/(key+".json")).write_text("{}")
    with pytest.raises(ValueError):store.load(key)
