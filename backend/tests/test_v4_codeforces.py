from threading import Event

from algoxray.v4_authoring import normalize_url
from algoxray.v4_codeforces import inspect_samples
from algoxray.v4_provider import MockProvider, ProviderError


URL = "https://codeforces.com/problemset/problem/4/A"
SOURCE = "n = int(input())\nprint('YES')\n"
SAMPLES = [{"stdin": "8", "stdout": "YES"}, {"stdin": "2", "stdout": "NO"}]


def imported(kind, *, url):
    assert kind == "codeforces"
    return {"source_url": normalize_url(url), "statement": "Divide a watermelon.",
            "samples": SAMPLES, "intake": {}}


def student_only(source, stdin, **kwargs):
    assert source == SOURCE
    assert stdin.endswith("\n")
    assert kwargs["mode"] == "trace_profile"
    return {"status": "ok", "stdout": "YES\n", "events": [], "trace_status": "complete"}


def test_public_sample_difference_keeps_evidence_when_ai_unavailable():
    def offline():
        raise ProviderError("local_model_unavailable")

    data = inspect_samples(URL, SOURCE, prepare=imported, run=student_only, make_provider=offline)
    assert data["status"] == "codeforces_samples"
    assert [c["same_output"] for c in data["checks"]] == [True, False]
    assert data["selected_sample"] == 2
    assert data["witness"]["stdin"] == "2\n"
    assert data["witness"]["reference"]["status"] == "not_run"
    assert data["judgment"]["expected"] == "NO"
    assert not data["judgment"]["general_correctness_claim"]
    assert data["ai_error"] == "local_model_unavailable"
    assert data["run_report"]["physical_executions"] == 2
    assert {w["role"] for w in data["run_report"]["workers"]} == {"student"}


def test_ai_uses_published_example_context_without_approved_package():
    class Explain(MockProvider):
        def propose(self, task, data, schema):
            assert task == "diagnosis"
            assert data["identity"]["package_sha256"] is None
            assert (data["stdin"], data["expected"], data["actual"]) == ("2\n", "NO", "YES\n")
            assert data["judgment"]["authority"] == "codeforces_public_example"
            return super().propose(task, data, schema)

    data = inspect_samples(URL, SOURCE, prepare=imported, run=student_only,
                           make_provider=lambda: Explain({"hypotheses": [], "facts": [], "branches": []}))
    assert data["ai_status"] == "ok"
    assert data["run_report"]["package_sha256"] is None


def test_no_public_sample_or_preempted_run_never_executes():
    def no_samples(*args, **kwargs):
        return {**imported(*args, **kwargs), "samples": []}

    def reject(*args, **kwargs):
        raise AssertionError("unexpected worker call")

    missing = inspect_samples(URL, SOURCE, prepare=no_samples, run=reject)
    assert missing["run_report"]["stop_reason"] == "no_public_samples"
    assert "witness" not in missing
    cancel = Event()
    cancel.set()
    stopped = inspect_samples(URL, SOURCE, prepare=imported, run=reject, cancel=cancel)
    assert stopped["run_report"]["stop_reason"] == "cancelled"
    assert stopped["run_report"]["physical_executions"] == 0
