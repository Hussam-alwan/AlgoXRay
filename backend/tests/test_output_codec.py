import pytest

from algoxray.output_codec import encode_output, UnsupportedOutput


def test_exact_output_preserves_values_beyond_trace_snapshot_limits():
    value = list(range(100)) + [None, True, {"key": "x" * 1000}]
    assert encode_output(value) == value


@pytest.mark.parametrize("value", [(1, 2), {1, 2}, float("inf"), float("nan"), {1: "x"}, 2**1024])
def test_unsupported_output(value):
    with pytest.raises(UnsupportedOutput):
        encode_output(value)


def test_cyclic_output():
    value = []
    value.append(value)
    with pytest.raises(UnsupportedOutput):
        encode_output(value)


def test_oversized_output():
    with pytest.raises(UnsupportedOutput):
        encode_output(list(range(4096)))
