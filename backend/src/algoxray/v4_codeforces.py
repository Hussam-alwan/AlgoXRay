"""Run supplied Python on imported public samples without authoring an oracle."""
from .v4_diagnostic_context import diagnose_execution
from .v4_intake import prepare_problem
from .v4_isolation import execute_stdio
from .v4_observation import observation_evidence, validate_text
from .v4_provider import ProviderError
from .v4_run_report import BudgetExhausted, RunLedger


def inspect_samples(url, source, *, run=execute_stdio, prepare=prepare_problem,
                    make_provider=None, seconds=1.0, cancel=None, run_id=None):
    ledger = RunLedger("codeforces_samples", source, run_id=run_id,
                       parameters={"url": url, "seconds": seconds},
                       session_seconds=60, max_executions=8)
    ledger.enter("validation")
    validate_text(source, "")
    ledger.enter("import")
    imported = prepare("codeforces", url=url)
    problem = {k: imported[k] for k in ("statement", "source_url", "samples", "intake")}
    checks = []
    payload = {"status": "codeforces_samples", "problem": problem, "checks": checks,
               "scope": "Published Codeforces samples only. Token comparison is descriptive; no checker, hidden tests, or reference program ran."}
    if not problem["samples"]:
        for stage in ("student", "structure", "diagnosis"):
            ledger.skip(stage, "no_public_samples")
        return ledger.finish(payload, stop_reason="no_public_samples")

    ledger.enter("student")
    selected = None
    selected_priority = -1
    stop = "completed"
    for number, sample in enumerate(problem["samples"], 1):
        if cancel is not None and cancel.is_set():
            stop = "cancelled"
            break
        stdin = sample["stdin"]
        if stdin and not stdin.endswith("\n"):
            stdin += "\n"
        try:
            executed = ledger.execute(run, "student", source, stdin, seconds=seconds,
                                      trace_limit=128, mode="trace_profile", cancel=cancel)
        except BudgetExhausted as exc:
            stop = str(exc)
            break
        status = executed["status"]
        if status == "cancelled":
            stop = status
            break
        same = executed.get("stdout", "").split() == sample["stdout"].split() if status == "ok" else None
        checks.append({"number": number, "status": status, "same_output": same})
        priority = 2 if status in ("exception", "timeout") else 1 if same is False else 0
        if priority > selected_priority:
            selected = (number, stdin, sample["stdout"], executed, same)
            selected_priority = priority
        if status not in ("ok", "exception", "timeout"):
            stop = "worker_unavailable"
            break

    payload["attempts"] = len(checks)
    if selected is None:
        ledger.skip("structure", "no_observation")
        ledger.skip("diagnosis", "no_observation")
        return ledger.finish(payload, stop_reason=stop)
    if stop != "completed":
        ledger.close_stage("partial")

    ledger.enter("structure")
    number, stdin, stdout, executed, same = selected
    judgment = {"status": "example_match" if same is True else "example_difference" if same is False else "example_not_compared",
                "authority": "codeforces_public_example", "expected": stdout, "reference_output_is_example": True,
                "general_correctness_claim": False}
    payload.update(observation_evidence(source, stdin, executed, example_output=stdout),
                   selected_sample=number, judgment=judgment, replay_count=0, ai_status="disabled")
    payload["witness"]["judgment"] = judgment

    if make_provider is None or selected_priority == 0 or stop != "completed" or (cancel is not None and cancel.is_set()):
        ledger.skip("diagnosis", "no_diagnostic_request")
    else:
        ledger.enter("diagnosis")
        try:
            provider = make_provider()
        except ProviderError as exc:
            payload.update(ai_status="unavailable_or_invalid", ai_error=str(exc))
        else:
            payload.update(diagnose_execution(None, source, payload["witness"], provider, cancel=cancel,
                                              sample_statement=problem["statement"],
                                              localization=payload["evidence_localization"],
                                              branches=payload["student_graph"]["branches"]))
        if payload["ai_status"] != "ok":
            ledger.close_stage("partial")
    if cancel is not None and cancel.is_set():
        stop = "cancelled"
    return ledger.finish(payload, stop_reason=stop)
