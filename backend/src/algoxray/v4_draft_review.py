"""Check literal provenance, never infer that a quotation proves full semantics."""
import hashlib,re
ATTRS=("min","max","alphabet","length","length_from","rows","rows_from","cols","cols_from")

def review_draft(statement,manifest,evidence=(),unresolved=()):
    if type(evidence) is not list or len(evidence)>48:raise ValueError("Invalid constraint quotations")
    if type(unresolved) is not list or len(unresolved)>16 or any(type(x) is not str or not 1<=len(x)<=400 for x in unresolved):
        raise ValueError("Invalid unresolved constraints")
    fields={f["name"]:f for f in manifest["fields"]};checks=[];covered=set()
    for item in evidence:
        if type(item) is not dict or set(item)!={"field","attribute","quote"} or any(type(item[k]) is not str for k in item):
            raise ValueError("Invalid quotation entry")
        field,attr,quote=item["field"],item["attribute"],item["quote"]
        if field not in fields or attr not in ATTRS or attr not in fields[field] or not 1<=len(quote)<=600:
            raise ValueError("Unknown quoted field attribute")
        value=fields[field][attr];found=quote in statement
        literal=found and (str(value) in re.findall(r"(?<![A-Za-z0-9_])[-+]?\d+(?![A-Za-z0-9_])",quote) if type(value) is int else str(value) in quote)
        status="literal_present_requires_semantic_review" if literal else "unmatched_requires_review"
        checks.append({**item,"declared_value":value,"status":status})
        if literal:covered.add((field,attr))
    missing=[f["name"]+"."+a for f in manifest["fields"] for a in ATTRS if a in f and (f["name"],a) not in covered]
    pending=list(dict.fromkeys(list(unresolved)+["Review uncited or unmatched attribute: "+x for x in missing]))
    if manifest.get("schema_version")==2:
        if "repeat" in manifest:pending.append("Manual semantic review: repeated cases and count bounds.")
        if manifest.get("relations"):pending.append("Manual semantic review: scalar relations and their direction.")
        if any(f.get("sorted") or f.get("unique") for f in manifest["fields"]):pending.append("Manual semantic review: list ordering and uniqueness.")
    provenance={"statement_sha256":hashlib.sha256(statement.encode()).hexdigest(),"evidence":list(evidence),"unresolved":pending[:48]}
    return {"provenance":provenance,"checks":checks,"uncited_attributes":missing,
            "scope":"Exact quotation/literal checks only. Numeric direction, units and full mathematical fidelity require owner review."}

def validate_provenance(p):
    provenance=p.get("provenance")
    if provenance is None:return
    if type(provenance) is not dict or set(provenance)!={"statement_sha256","evidence","unresolved"}:
        raise ValueError("Invalid package provenance")
    expected=hashlib.sha256(p["manifest"]["statement"].encode()).hexdigest()
    if provenance["statement_sha256"]!=expected:raise ValueError("Provenance statement hash mismatch")
    pending=provenance["unresolved"]
    if type(pending) is not list or len(pending)>48 or any(type(x) is not str or len(x)>400 for x in pending):
        raise ValueError("Invalid unresolved constraints")
    checked=review_draft(p["manifest"]["statement"],p["manifest"],provenance["evidence"],[])
    if checked["uncited_attributes"]:raise ValueError("Resolve unmatched constraint quotations before approval")
    if pending:raise ValueError("Resolve draft constraints before approving this package")

def field_schema(version=1):
    """Mutually exclusive shapes: an int-list has fixed OR dependent length, never both."""
    name={"type":"string","pattern":"^[a-z][a-z0-9_]{0,30}$"}
    number={"type":"integer"}
    def variant(kind,extra):
        properties={"name":name,"kind":{"const":kind},"min":number,"max":number,**extra}
        return {"type":"object","properties":properties,"required":list(properties),"additionalProperties":False}
    variants=[variant("int",{}),variant("word",{"alphabet":{"type":"string"}}),
              variant("ints",{"length":{"type":"integer","minimum":0,"maximum":1000 if version == 2 else 100}}),
              variant("ints",{"length_from":{"type":"string"}})]
    for rows in ("rows","rows_from"):
        for cols in ("cols","cols_from"):
            variants.append(variant("matrix",{rows:{"type":"string"} if rows.endswith("_from") else {"type":"integer","minimum":1,"maximum":32},
                                               cols:{"type":"string"} if cols.endswith("_from") else {"type":"integer","minimum":1,"maximum":32}}))
    if version==2:
        for variant in variants:
            if variant["properties"]["kind"].get("const")=="ints":
                variant["properties"].update(sorted={"type":"boolean"}, unique={"type":"boolean"},
                                             min_from={"type":"string"}, max_from={"type":"string"})
    return {"oneOf":variants}
