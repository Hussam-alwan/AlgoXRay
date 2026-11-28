from threading import Event

from algoxray.v4_authoring import normalize_url
from algoxray.v4_codeforces import LEVELS, WATERMELON_URL, inspect_samples, plan_cases
from algoxray.v4_provider import MockProvider, ProviderError


URL = "https://codeforces.com/problemset/problem/7/B"
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


def test_watermelon_regression_exposes_weight_two_after_matching_public_example():
    source = 'n = int(input())\nprint("YES" if n % 2 == 0 else "NO")\n'

    def watermelon(*args, **kwargs):
        return {**imported(*args, **kwargs), "samples": SAMPLES[:1]}

    def run(code, stdin, **kwargs):
        assert code == source
        weight = int(stdin)
        return {"status": "ok", "stdout": "NO\n" if weight % 2 else "YES\n", "trace_status": "complete",
                "events": [{"event_id": "E1", "line": 2, "kind": "line", "frame_id": "F1",
                            "snapshot_timing": "before_line", "locals": {"n": weight}}]}

    data = inspect_samples(WATERMELON_URL, source, prepare=watermelon, run=run)
    assert [level["id"] for level in data["levels"]] == list(LEVELS)
    assert all(level["planned"] for level in data["levels"])
    checks = data["checks"]
    assert len(checks) == len({c["stdin"] for c in checks}) == 11
    assert checks[0]["stdin"] == "8\n" and checks[0]["same_output"]
    assert next(c for c in checks if c["level"] == "minimum")["stdin"] == "1\n"
    assert next(c for c in checks if c["level"] == "maximum")["stdin"] == "100\n"
    assert data["judgment"]["status"] == "checked_difference"
    assert data["witness"]["stdin"] == "2\n"
    assert data["witness"]["student"]["stdout"] == "YES\n"
    assert data["judgment"]["expected"] == "NO"
    assert data["decision"] == {"line": 2, "event_id": "E1", "reads": {"n": 2},
                                "test": "n % 2 == 0", "outcome": True}


def test_unverified_integer_range_runs_values_without_inventing_expected_outputs():
    statement = "Input\nThe only input line contains an integer n (1 ≤ n ≤ 50).\nOutput\nAn answer."
    problem = {**imported("codeforces", url=URL), "statement": statement}
    cases, domain = plan_cases(problem)
    assert domain == {"min": 1, "max": 50, "authority": "statement_integer_bounds"}
    assert any(c["level"] == "maximum" and c["stdin"] == "50\n" for c in cases)
    assert all(c["expected"] is None for c in cases if c["level"] != "published")
    ambiguous = {**problem, "statement": statement.replace("\nOutput", "\nA second line follows.\nOutput")}
    assert plan_cases(ambiguous)[1] is None
