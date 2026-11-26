from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .paths import FIXTURES


@dataclass(frozen=True)
class Submission:
    fixture_id: str
    problem_id: str
    path: Path
    source: str
    sha256: str
    origin: str
    label: str
    split: str
    adapter: str | None = None
    display_name: str = ""


def catalog():
    return json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8-sig"))


def get_submission(fixture_id):
    item = next((x for x in catalog() if x["id"] == fixture_id), None)
    if item is None:
        raise ValueError("Unknown fixture_id")
    path = (FIXTURES / item["path"]).resolve()
    if not path.is_relative_to(FIXTURES.resolve()) or path.suffix != ".py":
        raise ValueError("Invalid fixture path")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return Submission(fixture_id, item["problem_id"], path, raw.decode("utf-8"), digest,
                      item["origin"], item["label"], item["split"],
                      item.get("adapter") if digest == item["sha256"] else None, item["name_ar"])


def local_submission(problem_id, path):
    path = Path(path).resolve()
    if path.suffix != ".py" or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("Reviewed local submission must be a .py file of at most 64 KiB")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return Submission("local_" + digest[:12], problem_id, path, raw.decode("utf-8"), digest,
                      "reviewed_local_file", "unknown", "local", display_name=path.name)


def fixture_cards(problem_id=None):
    result = []
    for item in catalog():
        if problem_id and item["problem_id"] != problem_id:
            continue
        sub = get_submission(item["id"])
        result.append({"id": sub.fixture_id, "problem_id": sub.problem_id, "name_ar": sub.display_name,
                       "origin": sub.origin, "split": sub.split, "label": sub.label,
                       "source": sub.source, "source_sha256": sub.sha256,
                       "adapter_supported": sub.adapter is not None})
    return result
