import pytest
from algoxray.output_codec import encode_output, UnsupportedOutput

def test_output_budget_is_global():
    with pytest.raises(UnsupportedOutput):
        encode_output(["x" * 16000] * 100)

def test_small_output_preserved():
    assert encode_output([1, None, {"a": True}]) == [1, None, {"a": True}]
