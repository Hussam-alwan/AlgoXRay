"""Optional presentation layer. External prose is never accepted as evidence."""
def explanation_cards(bundle):
    claims = {c["claim_id"]: c for c in bundle.get("claims", [])
              if c.get("verification_status") == "verified"}
    return [{"claim_id": key, "text": claim["text"], "event_ids": claim.get("event_ids", [])}
            for key, claim in claims.items()]

def select_explanation(bundle, selected_ids):
    """An optional model may select existing cards, but cannot invent claims."""
    cards = {c["claim_id"]: c for c in explanation_cards(bundle)}
    if not isinstance(selected_ids, list) or any(type(i) is not str or i not in cards for i in selected_ids):
        raise ValueError("Unknown explanation claim")
    return [cards[i] for i in dict.fromkeys(selected_ids)]
