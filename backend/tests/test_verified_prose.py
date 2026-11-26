from copy import deepcopy
import pytest
from algoxray.engine import Options,analyze,validate_bundle
from algoxray.registry import get_submission
from algoxray.explanation import explanation_cards

def test_tampered_text_rejected_even_with_valid_event_ids():
    b=analyze(get_submission("binary_missing_last"),Options(shrink=False),case={"array":[7],"target":7},persist=False)
    changed=deepcopy(b)
    changed["claims"][0]["text"]="Invented explanation"
    changed["explanation_cards"]=explanation_cards(changed)
    with pytest.raises(ValueError,match="deterministic evidence templates"):
        validate_bundle(changed)
