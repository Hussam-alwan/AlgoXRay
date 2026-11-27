import pytest
from jsonschema import Draft202012Validator
from algoxray.v4_draft_review import field_schema

def test_list_shapes_are_exclusive_and_dependent_length_is_supported():
    validator=Draft202012Validator(field_schema())
    validator.validate({"name":"a","kind":"ints","min":-9,"max":9,"length_from":"n"})
    for bad in [
        {"name":"a","kind":"ints","min":-9,"max":9},
        {"name":"a","kind":"ints","min":-9,"max":9,"length":1,"length_from":"n"},
        {"name":"x","kind":"int","min":0,"max":3,"alphabet":"abc"}]:
        assert not validator.is_valid(bad)
