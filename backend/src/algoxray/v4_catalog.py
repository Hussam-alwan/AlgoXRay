"""Local, versioned catalog and the student-facing analysis projection."""
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from .paths import ROOT
from .v4_contracts import digest, validate_package
from .v4_run_report import sha


def validate_catalog_metadata(package):
    value = package["catalog"]
    keys = {"version", "url", "reference_language", "reference_origin", "trust_basis", "visualization"}
    if type(value) is not dict or set(value) != keys or type(value["version"]) is not int or value["version"] < 1:
        raise ValueError("Invalid catalog metadata or version")
    if value["reference_language"] != "python":
        raise ValueError("Only Python catalog references are supported")
    if value["trust_basis"] not in ("development_reference", "curator_supplied_reference", "accepted_reported_by_curator"):
        raise ValueError("Unsupported reference trust basis")
    if value["visualization"] not in ("execution", "lanterns"):
        raise ValueError("Unsupported catalog visualization")
    if value["visualization"] == "lanterns":
        fields = {field["name"]: field["kind"] for field in package["manifest"]["fields"]}
        if fields != {"n": "int", "length": "int", "positions": "ints"} or "repeat" in package["manifest"]:
            raise ValueError("Lanterns visualization requires one road and its positions")
    if type(value["reference_origin"]) is not str or not 1 <= len(value["reference_origin"]) <= 300:
        raise ValueError("Record the source of the reference")
    url = value["url"]
    if type(url) is not str or len(url) > 250:
        raise ValueError("Invalid problem URL")
    parsed = urlsplit(url)
    if url and (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password):
        raise ValueError("Problem URL must use HTTPS")
    if "test_plan" not in package:
        raise ValueError("Catalog packages require a versioned test plan")


def public_problem(package):
    manifest, meta = package["manifest"], package["catalog"]
    return {"id": manifest["id"], "version": meta["version"], "key": digest(package),
            "title": manifest["title"], "statement": manifest["statement"], "url": meta["url"],
            "trust_basis": meta["trust_basis"], "language": "python", "input_layout": manifest["lines"],
            "limits": manifest["fields"], "output": {key: manifest[key] for key in
             ("output", "output_count", "tolerance", "relative_to") if key in manifest}}


class Catalog:
    def __init__(self, store, fixtures=ROOT / "fixtures" / "v4_catalog"):
        self.store = store
        self.fixtures = Path(fixtures)
        self.index = store.root / ".catalog.json"

    def _builtins(self):
        for path in sorted(self.fixtures.glob("*.json")):
            yield validate_package(json.loads(path.read_text(encoding="utf-8")))

    def _entries(self):
        if not self.index.exists():
            return {}
        return json.loads(self.index.read_text(encoding="utf-8"))

    def _write(self, entries):
        self.index.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.index.parent, delete=False) as file:
            path = Path(file.name)
            try:
                json.dump(entries, file, indent=2)
                file.close()
                path.replace(self.index)
            finally:
                path.unlink(missing_ok=True)

    def list(self):
        entries = self._entries()
        packages = {p["manifest"]["id"]: p for p in self._builtins()}
        for problem_id, entry in entries.items():
            if entry["enabled"]:
                packages[problem_id] = self.store.load(entry["key"])
            else:
                packages.pop(problem_id, None)
        return [public_problem(p) for p in packages.values()]

    def load(self, problem_id, key):
        entry = self._entries().get(problem_id)
        if entry:
            if entry["enabled"] and entry["key"] == key:
                return self.store.load(key)
        else:
            for package in self._builtins():
                if package["manifest"]["id"] == problem_id and digest(package) == key:
                    return package
        raise ValueError("Catalog version unavailable. Refresh the catalog.")

    def publish(self, key, enabled):
        entries = self._entries()
        builtin = next((p for p in self._builtins() if digest(p) == key), None)
        package = builtin or self.store.load(key)
        meta = package.get("catalog")
        if meta is None:
            raise ValueError("This approved package has no catalog metadata")
        identity, version = package["manifest"]["id"], meta["version"]
        old = entries.get(identity)
        if old is None:
            existing = next((p for p in self._builtins() if p["manifest"]["id"] == identity), None)
            if existing:
                old = {"key": digest(existing), "version": existing["catalog"]["version"], "enabled": True}
        if old and old["key"] != key and (not enabled or version <= old["version"]):
            raise ValueError("Publish a newer version or disable the currently published version")
        if not old and not enabled:
            raise ValueError("Catalog version is not published")
        if builtin:
            if enabled:
                entries.pop(identity, None)
            else:
                entries[identity] = {"key": key, "version": version, "enabled": False}
        else:
            entries[identity] = {"key": key, "version": version, "enabled": enabled}
        self._write(entries)
        return {"status": "published" if enabled else "disabled", "problem": public_problem(package)}


def _fields(data, keys):
    return {key: data[key] for key in keys if key in data}


def _witness(raw, *, show_trace=False):
    out = _fields(raw, ("case", "stdin", "kind"))
    student, reference = raw.get("student", {}), raw.get("reference", {})
    out["student"] = _fields(student, ("status", "stdout", "detail", "failure_location"))
    out["reference"] = _fields(reference, ("status", "stdout", "known_expected"))
    if show_trace:
        out["trace"] = _fields(student, ("events", "trace_status", "event_count", "profile"))
    judgment = raw.get("judgment")
    if judgment:
        out["judgment"] = _fields(judgment, ("status", "authority", "policy", "reason", "reference_output_is_example"))
    return out


def student_analysis(package, result):
    """Build the wire response explicitly so future operator fields stay private."""
    report = result["run_report"]
    public = _fields(result, ("status", "analysis_id", "student_source", "attempts", "stop_reason", "replay_count",
                              "kind", "search", "reduction", "original_case", "inconclusive_student_outcomes"))
    public["problem"] = public_problem(package)
    public["run_report"] = _fields(report, ("version", "operation", "run_id", "source_sha256", "package_sha256",
                                       "manifest_sha256", "spec_version", "elapsed_ms", "physical_executions",
                                       "distinct_worker_inputs", "pair_attempts", "limits", "stages",
                                       "stop_reason", "image_ids", "engine_source_files_sha256", "host_python",
                                       "host_system", "parameters"))
    public["run_report"]["workers"] = [
        _fields(worker, ("number", "stage", "role", "input_sha256", "status", "call_ms", "trace_limit",
                         "requested_mode", "timeout_basis", "cleanup_confirmed"))
        for worker in report["workers"]
    ]
    public["reference_sha256"] = sha(package["reference"])
    raw = result.get("witness") or result.get("example_observation", {}).get("witness")
    if raw:
        public["witness"] = _witness(raw, show_trace=True)
    if result.get("original_witness"):
        public["original_witness"] = _witness(result["original_witness"])
    if result.get("partial_observation", {}).get("witness"):
        partial = result["partial_observation"]
        public["partial_observation"] = {**_fields(partial, ("replay_verified", "reduction", "original_case")),
                                         "witness": _witness(partial["witness"], show_trace=partial.get("replay_verified", False))}
    if result.get("detail", {}).get("case") is not None:
        public["detail"] = _witness(result["detail"])
    if result.get("evidence_localization"):
        public["localization"] = result["evidence_localization"]
    if raw and result["status"] == "observed_mismatch":
        public["hints"] = _hints(package, public["witness"])
    if raw:
        public["visualization"] = package["catalog"]["visualization"]
    return public


def _hints(package, witness):
    if witness["kind"] == "exception":
        location = witness["student"].get("failure_location") or {}
        return [{"level": 1, "key": "student_exception", "line": location.get("line")}]
    hints = [{"level": 1, "key": "output_mismatch", "evidence": "witness"}]
    if package["catalog"]["visualization"] == "lanterns":
        case = witness["case"]
        positions = sorted(case["positions"])
        components = (positions[0], case["length"] - positions[-1],
                      max((b - a for a, b in zip(positions, positions[1:])), default=0) / 2)
        dominant = ("left_end", "right_end", "inner_gap")
        hints.append({"level": 2, "key": "largest_gap", "evidence": "witness.case",
                      "components": dict(zip(dominant, components)),
                      "largest": [name for name, value in zip(dominant, components) if value == max(components)]})
        hints.append({"level": 3, "key": "compare_coverages", "evidence": "witness.case"})
    else:
        hints.append({"level": 2, "key": "inspect_before_output", "evidence": "witness.trace"})
    hints.append({"level": 4, "key": "verify_patch", "evidence": "witness"})
    return hints
