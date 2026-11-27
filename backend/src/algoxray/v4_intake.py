"""One bounded problem intake for public Codeforces URLs and user-supplied text.

Intake retains provenance, not oracle authority. All statements and samples
are untrusted data. No URL supplied as text is fetched automatically.
"""
from datetime import datetime, timezone
import hashlib
from .v4_authoring import import_problem, normalize_url
from .v4_isolation import MAX_INPUT

KINDS=("codeforces","text","description")
QUESTIONS=[
    "What exactly must the output represent, including multiple valid answers?",
    "What is the input format and all value/size/dependency constraints (including T)?",
    "Which sample inputs and independently known outputs can be used as controls?"
]

def validate_samples(samples):
    if type(samples) is not list or len(samples)>8:
        raise ValueError("Provide up to 8 sample input/output pairs")
    for sample in samples:
        if type(sample) is not dict or set(sample)!={"stdin","stdout"}:
            raise ValueError("Sample requires stdin and stdout")
        for k,cap in (("stdin",MAX_INPUT),("stdout",8192)):
            if type(sample[k]) is not str or len(sample[k].encode("utf-8"))>cap:
                raise ValueError("Sample exceeds bounds: "+k)
    if sum(len(x[k].encode("utf-8")) for x in samples for k in ("stdin","stdout"))>65536:
        raise ValueError("Combined samples exceed 64 KiB")
    return samples

def validate_intake(record,statement):
    keys={"version","kind","source_url","statement_sha256","samples","captured_at","clarifications"}
    if type(record) is not dict or set(record)!=keys or type(record["version"]) is not int or record["version"]!=1 or record["kind"] not in KINDS:
        raise ValueError("Invalid problem intake record")
    if record["statement_sha256"]!=hashlib.sha256(statement.encode("utf-8")).hexdigest():
        raise ValueError("Intake statement hash mismatch; prepare the edited statement again")
    if record["kind"]=="codeforces":
        if normalize_url(record["source_url"])!=record["source_url"]:
            raise ValueError("Invalid intake URL")
    elif record["source_url"] is not None:
        raise ValueError("Manual intake cannot claim an imported URL")
    timestamp=record["captured_at"]
    if type(timestamp) is not str or len(timestamp)>40:
        raise ValueError("Invalid intake timestamp")
    try:
        if datetime.fromisoformat(timestamp).utcoffset() is None:
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid intake timestamp") from None
    validate_samples(record["samples"])
    clarifications=record["clarifications"]
    if type(clarifications) is not list or len(clarifications)>12 or any(type(x) is not str or not 1<=len(x)<=400 for x in clarifications):
        raise ValueError("Invalid intake clarifications")
    return record

def prepare_problem(kind, *, text="", url="", samples=None, importer=import_problem):
    if kind not in KINDS:raise ValueError("Unsupported problem source")
    samples=[] if samples is None else validate_samples(samples)
    source=None
    if kind=="codeforces":
        if text or samples:raise ValueError("Import first, then edit as manual text if needed")
        source=normalize_url(url)
        imported=importer(source)
        statement=imported["statement"]
        samples=validate_samples(imported["samples"])
        questions=list(imported.get("limitations",[]))
        questions.append("Review imported formatting and mathematical constraints against the original.")
    else:
        if url:raise ValueError("Manual intake does not fetch links")
        statement=text
        questions=list(QUESTIONS) if kind=="description" else []
        if not samples and QUESTIONS[2] not in questions:questions.append(QUESTIONS[2])
    if type(statement) is not str or not statement.strip() or len(statement)>8000:
        raise ValueError("Supply a nonempty statement of at most 8000 characters")
    record={"version":1,"kind":kind,"source_url":source,
            "statement_sha256":hashlib.sha256(statement.encode("utf-8")).hexdigest(),
            "captured_at":datetime.now(timezone.utc).isoformat(),"samples":samples,
            "clarifications":questions}
    validate_intake(record,statement)
    return {"status":"intake_unreviewed","statement":statement,"source_url":source,
            "samples":samples,"intake":record,
            "warning":"Review source and samples. These do not approve a grammar or reference."}
