"""Check declared case separation and file identities before evaluation."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SPLITS = {"development", "public_auxiliary", "heldout"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check_inventory(data, root=ROOT, *, require_holdout=False):
    version = data.get("inventory_version")
    if type(version) is not int or version != 1 or not re.fullmatch(r"[a-f0-9]{40}", data.get("release_commit", "")):
        raise ValueError("Expected inventory version 1 and a full release commit")

    files = data["source_files"]
    for name, fingerprint in files.items():
        path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"Source path must be a file within the project: {name}")
        if sha256(path.read_bytes()).hexdigest() != fingerprint:
            raise ValueError(f"Source fingerprint changed: {name}")

    record_ids = set()
    family_splits = {}
    source_splits = {}
    counts = Counter()
    for entry in data["entries"]:
        identity, family, split, name = (entry[key] for key in ("id", "family", "split", "source_file"))
        if not all(nonempty(value) for value in (identity, family, entry["member"])) or split not in SPLITS or name not in files:
            raise ValueError(f"Invalid case, split or source reference: {identity}")
        identity = identity.strip().casefold()
        family = family.strip().casefold()
        if identity in record_ids:
            raise ValueError(f"Duplicate case: {identity}")
        record_ids.add(identity)
        if family_splits.setdefault(family, split) != split:
            raise ValueError(f"Problem family crosses splits: {family}")
        if source_splits.setdefault(files[name], split) != split:
            raise ValueError(f"Source file crosses splits: {name}")
        if split == "heldout":
            for field in ("rights_record", "independent_review", "exposure_record"):
                if not nonempty(entry.get(field)):
                    raise ValueError(f"Held-out case {identity} requires {field}")
        counts[split] += 1

    if require_holdout and not counts["heldout"]:
        raise ValueError("No independently reviewed held-out cases declared")
    return {"entries": dict(counts), "families": len(family_splits), "files": len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", nargs="?", type=Path, default=Path(__file__).with_name("development-inventory.json"))
    parser.add_argument("--require-holdout", action="store_true")
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        summary = check_inventory(inventory, require_holdout=args.require_holdout)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        parser.exit(1, f"Inventory check failed: {error}\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
