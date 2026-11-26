"""Regression tests for the raw/normalized hash distinction in WP0."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/option_b_baseline.py"
spec = importlib.util.spec_from_file_location("option_b_baseline", SCRIPT)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def test_exact_source_identity():
    raw = b"def solve(x):\n    return 0\n"
    assert baseline.compare_bytes(raw, baseline.digest(raw))["status"] == "exact"


def test_crlf_equivalence_is_not_raw_identity():
    lf = b"def solve(x):\n    return 0\n"
    crlf = lf.replace(b"\n", b"\r\n")
    result = baseline.compare_bytes(crlf, baseline.digest(lf))
    assert result["status"] == "lf_only"
    assert result["raw_sha256"] != result["expected_sha256"]


def test_source_edit_is_not_normalization():
    assert baseline.compare_bytes(b"return 1\r\n", baseline.digest(b"return 0\n"))["status"] == "different"


def test_missing_source(tmp_path):
    assert baseline.compare_file(tmp_path / "absent.py", "a" * 64)["status"] == "missing"
