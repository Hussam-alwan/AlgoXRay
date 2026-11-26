from algoxray.tracing import safe_value

def test_trace_snapshot_limits_large_values():
    assert safe_value(2**10000) == "<integer limit>"
    result = safe_value(list(range(10000)))
    assert result[:2] == [0, 1]
    assert len(result) == 65 and result[-1] == "<item limit>"

def test_custom_dictionary_keys_do_not_execute_repr():
    class Key:
        def __str__(self):
            raise AssertionError("snapshot must not execute arbitrary formatting")
    assert safe_value({Key(): 1}) == {"<key 0>": 1}
