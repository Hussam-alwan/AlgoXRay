"""Run published examples and bounded extra cases for supported input formats."""
import ast
import random
import re

from .v4_dataflow import evaluate
from .v4_diagnostic_context import diagnose_execution
from .v4_intake import prepare_problem
from .v4_isolation import execute_stdio
from .v4_observation import observation_evidence, validate_text
from .v4_provider import ProviderError
from .v4_run_report import BudgetExhausted, RunLedger

LEVELS = ("published", "minimum", "maximum", "near_limits", "middle", "varied")
WATERMELON_URL = "https://codeforces.com/problemset/problem/4/A"


def input_line(text):
    return text if not text or text.endswith("\n") else text + "\n"


def integer_bounds(statement):
    """Recognize a single bounded integer declaration, not arbitrary problem prose."""
    match = re.search(r"^Input\s*\n(.*?)^Output\s*$", statement, re.M | re.S)
    if not match:
        return None
    description = match[1].replace("$", "").replace("≤", "<=").replace(r"\leq", "<=").replace(r"\le", "<=")
    description = " ".join(description.split())
    declaration = re.fullmatch(
        r"(?:The (?:first \(and the only\)|only|single) input line|The input) contains "
        r"(?:a single |one |an )?integer (?:number )?([a-zA-Z][a-zA-Z0-9_]*) "
        r"\(\s*(-?\d{1,15})\s*<=\s*\1\s*<=\s*(-?\d{1,15})\s*\)(?:\.)?",
        description, re.I,
    )
    if not declaration:
        return None
    low, high = map(int, declaration.groups()[1:])
    return (low, high) if low <= high else None


def watermelon_output(weight):
    # Independent of the user's predicate: can an even positive part leave another even positive part?
    return "YES" if any((weight - part) % 2 == 0 for part in range(2, weight, 2)) else "NO"


def watermelon_rule(problem):
    if problem["source_url"] != WATERMELON_URL or not problem["samples"]:
        return False
    for example in problem["samples"]:
        value = example["stdin"].strip()
        if not re.fullmatch(r"[1-9][0-9]{0,2}", value):
            return False
        weight = int(value)
        if weight > 100 or watermelon_output(weight) != example["stdout"].strip().upper():
            return False
    return True


def plan_cases(problem):
    known = watermelon_rule(problem)
    bounds = (1, 100) if known else integer_bounds(problem["statement"])
    cases = [{"level": "published", "stdin": input_line(sample["stdin"]),
              "expected": sample["stdout"], "authority": "codeforces_public_example"}
             for sample in problem["samples"]]
    if bounds is None:
        return cases, None

    low, high = bounds
    # An imported example outside the inferred domain means the format was not understood.
    seen = set()
    for row in cases:
        token = row["stdin"].strip()
        if not re.fullmatch(r"[+-]?\d{1,16}", token) or not low <= int(token) <= high:
            return cases, None
        seen.add(int(token))

    middle = (low + high) // 2
    rng = random.Random(2026)
    varied = rng.sample(range(low, high + 1), min(12, high - low + 1))
    values = ((low,), (high,), (low + 1, high - 1), (middle, middle + 1), varied)
    # Even if a boundary already appeared as a sample, retain its level without running it twice.
    covered = {int(row["stdin"].strip()): row for row in cases}
    for level, group in zip(LEVELS[1:], values):
        added = 0
        for value in group:
            if not low <= value <= high:
                continue
            if value in seen:
                if level in ("minimum", "maximum"):
                    covered[value].setdefault("also_levels", []).append(level)
                continue
            row = {"level": level, "stdin": f"{value}\n",
                   "expected": watermelon_output(value) if known else None,
                   "authority": "watermelon_rule" if known else "none"}
            cases.append(row)
            covered[value] = row
            seen.add(value)
            added += 1
            if level == "varied" and added == 4:
                break
    return cases, {"min": low, "max": high, "authority": "watermelon_rule" if known else "statement_integer_bounds"}


def condition_value(test, values, reads):
    if isinstance(test, ast.BoolOp):
        operands = (condition_value(item, values, reads) for item in test.values)
        return all(operands) if isinstance(test.op, ast.And) else any(operands)
    return bool(evaluate(test, values, reads))


def recorded_decision(source, execution):
    """Match a simple print ternary's recorded input values and actual output."""
    if execution["status"] != "ok":
        return None
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError, ValueError):
        return None
    prints = [node for node in ast.walk(tree) if isinstance(node, ast.Expr)
              and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
              and node.value.func.id == "print" and len(node.value.args) == 1 and not node.value.keywords
              and isinstance(node.value.args[0], ast.IfExp)]
    if len(prints) != 1:
        return None
    statement = prints[0]
    expression = statement.value.args[0]
    events = [e for e in execution.get("events", ()) if e.get("line") == statement.lineno
              and e.get("snapshot_timing") == "before_line"]
    if len(events) != 1 or expression.end_lineno != statement.lineno:
        return None
    event = events[0]
    reads = {}
    try:
        outcome = condition_value(expression.test, event.get("locals", {}), reads)
    except (ValueError, ArithmeticError, TypeError, RecursionError):
        return None
    branch = expression.body if outcome else expression.orelse
    if not isinstance(branch, ast.Constant) or type(branch.value) is not str or branch.value + "\n" != execution.get("stdout"):
        return None
    test = ast.get_source_segment(source, expression.test)
    if test and len(test) <= 160:
        return {"test": test, "outcome": outcome, "reads": reads, "line": statement.lineno, "event_id": event["event_id"]}


def inspect_samples(url, source, *, run=execute_stdio, prepare=prepare_problem,
                    make_provider=None, seconds=1.0, cancel=None, run_id=None):
    ledger = RunLedger("codeforces_samples", source, run_id=run_id,
                       parameters={"url": url, "seconds": seconds},
                       session_seconds=90, max_executions=18)
    ledger.enter("validation")
    validate_text(source, "")
    ledger.enter("import")
    imported = prepare("codeforces", url=url)
    problem = {k: imported[k] for k in ("statement", "source_url", "samples", "intake")}
    cases, domain = plan_cases(problem)
    checks = []
    levels = [{"id": level, "planned": sum(level == c["level"] or level in c.get("also_levels", ()) for c in cases)} for level in LEVELS]
    payload = {"status": "codeforces_samples", "problem": problem, "checks": checks, "levels": levels, "domain": domain,
               "scope": "Published examples and bounded local cases where supported. Expected outputs are labelled by authority. No official judge or hidden tests ran."}
    if not cases:
        for stage in ("student", "structure", "diagnosis"):
            ledger.skip(stage, "no_public_samples")
        return ledger.finish(payload, stop_reason="no_public_samples")

    ledger.enter("student")
    selected = None
    selected_priority = -1
    stop = "completed"
    for number, case in enumerate(cases, 1):
        if cancel is not None and cancel.is_set():
            stop = "cancelled"
            break
        stdin = case["stdin"]
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
        actual = executed.get("stdout", "")
        expected = case["expected"]
        same = None
        if status == "ok" and expected is not None:
            same = actual.upper().split() == expected.upper().split() if domain and domain["authority"] == "watermelon_rule" else actual.split() == expected.split()
        check = {**case, "number": number, "status": status, "same_output": same, "actual": actual}
        checks.append(check)
        priority = 3 if status in ("exception", "timeout") else 2 if same is False and case["authority"] == "watermelon_rule" else 1 if same is False else 0
        if priority > selected_priority:
            selected = (check, executed)
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
    check, executed = selected
    same = check["same_output"]
    prefix = "checked" if check["authority"] == "watermelon_rule" else "example"
    judgment = {"status": prefix + ("_match" if same is True else "_difference" if same is False else "_not_compared"),
                "authority": check["authority"], "expected": check["expected"],
                "reference_output_is_example": check["authority"] == "codeforces_public_example",
                "general_correctness_claim": False}
    payload.update(observation_evidence(source, check["stdin"], executed, example_output=check["expected"] or ""),
                   selected_sample=check["number"], judgment=judgment, replay_count=0, ai_status="disabled",
                   decision=recorded_decision(source, executed))
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
