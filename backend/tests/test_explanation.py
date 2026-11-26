import pytest
from algoxray.explanation import select_explanation

def test_selection_cannot_invent_claims():
    bundle = {"claims": [{"claim_id": "C1", "text": "Recorded", "verification_status": "verified"}]}
    assert select_explanation(bundle, ["C1", "C1"])[0]["text"] == "Recorded"
    with pytest.raises(ValueError):
        select_explanation(bundle, ["invented"])
