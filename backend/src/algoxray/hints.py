"""Source-hash-gated adapters; generic mismatch evidence always remains separate."""
from .problems import PROBLEMS
from .diagnostics import custom_observation


def build_hints(bundle, submission):
    if bundle["status"] != "witness_found":
        return [], []
    actual, expected = bundle["observed_output"], bundle["expected_output"]
    kind, problem = bundle["failure_kind"], bundle["problem_id"]
    if kind == "wrong_answer" and problem == "dijkstra_v1":
        index = next(i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1])
        text = f"المسافة للعقدة {index} هي {actual[index]} في الحل، و{expected[index]} في المرجع."
    elif kind == "wrong_answer":
        text = f"أعاد الحل الفهرس {actual}، لكنه لا يحقق عقد البحث على هذه المصفوفة."
    elif kind == "exception":
        text = "توقف الحل باستثناء " + bundle["exception"].get("type", "غير معروف") + " على هذا المدخل القانوني."
    elif kind == "timeout":
        text = "تجاوز هذا التشغيل المهلة المحددة؛ هذه ملاحظة زمنية وليست حكماً بإجابة خاطئة."
    else:
        text = "خرج الحل لا يحقق نوع أو شكل الخرج المطلوب في عقد المسألة."
    claims = [{"claim_id": "C1", "kind": kind, "text": text, "event_ids": [],
               "evidence_refs": ["observed_output", "expected_output", "verification", "case"],
               "verification_status": "verified"}]
    hints = [{"tier": "H1", "claim_ids": ["C1"], "text": text, "kind": "observation"}]
    if kind != "wrong_answer":
        observation = custom_observation(bundle, submission)
        if observation:
            _append_observation(claims, hints, observation)
        return claims, hints
    question = ("أيّ عقدة تختلف مسافتها عن المرجع؟ هل تستطيع تتبّع طريق يصل إليها من المصدر؟"
                if problem == "dijkstra_v1" else "أين يظهر الهدف في هذا المدخل، وماذا يعني الفهرس الذي أعاده حلك؟")
    hints.append({"tier": "H2", "claim_ids": [], "text": question, "kind": "educational_question"})
    lines = submission.source.splitlines()
    diagnostic = None
    if bundle["trace_status"] == "complete":
        for event in bundle["events"]:
            line = event["line"]
            source_line = lines[line - 1].strip() if 0 < line <= len(lines) else ""
            local = event["locals"]
            if submission.adapter == "dijkstra_seen_v1" and event["kind"] == "line" and source_line == "continue":
                if not all(k in local for k in ("u", "v", "w", "d", "dist", "seen")):
                    continue
                v, d, w = local["v"], local["d"], local["w"]
                if any(type(x) is not int for x in (v, d, w)) or not 0 <= v < len(local["dist"]):
                    continue
                old = local["dist"][v]
                if v in local["seen"] and type(old) is int and d + w < old:
                    diagnostic = (event, f"عند فحص الحافة {local['u']} → {v}، تجاوز شرط الزيارة تحسيناً من {old} إلى {d + w}.",
                                  "راجع اللحظة التي تمنع عندها تحديث مسافة عقدة اكتُشفت سابقاً.")
                    break
            if submission.adapter == "binary_last_v1" and event["kind"] == "line" and source_line == "return -1":
                if not all(k in local for k in ("lo", "hi", "arr", "target")):
                    continue
                lo, hi, arr = local["lo"], local["hi"], local["arr"]
                if lo == hi and 0 <= lo < len(arr) and arr[lo] == local["target"] and actual == -1:
                    diagnostic = (event, f"وصل الحل إلى إرجاع -1 مع بقاء العنصر المطابق في الفهرس {lo} داخل المجال الأخير.",
                                  "راجع شرط استمرار البحث عندما يتساوى الحدّان، مع الحفاظ على إنهاء الحلقة.")
                    break
    if diagnostic:
        event, text, direction = diagnostic
        claims.append({"claim_id": "C2", "kind": "source_specific_observation", "text": text,
                       "event_ids": [event["event_id"]], "source_lines": [event["line"]], "evidence_refs": ["case", "observed_output", "expected_output"],
                       "verification_status": "verified", "adapter_id": submission.adapter})
        hints.extend([{"tier": "H3", "claim_ids": ["C2"], "event_ids": [event["event_id"]],
                       "text": text, "kind": "source_specific_observation"},
                      {"tier": "H4", "claim_ids": ["C2"], "text": direction, "kind": "conceptual_direction"}])
    if not diagnostic and submission.origin == "reviewed_local_file":
        observation = custom_observation(bundle, submission)
        if observation:
            _append_observation(claims, hints, observation)
    return claims, hints


def _append_observation(claims, hints, observation):
    claims.append({"claim_id": "C2", "kind": "source_specific_observation", "text": observation["text"],
                   "event_ids": observation["event_ids"], "source_lines": observation["source_lines"],
                   "trace_roles": observation.get("trace_roles"),
                   "evidence_refs": ["case", "observed_output", "expected_output", "exception"],
                   "verification_status": "verified", "adapter_id": observation["adapter_id"]})
    hints.extend([{"tier": "H3", "claim_ids": ["C2"], "event_ids": observation["event_ids"],
                   "text": observation["text"], "kind": "source_specific_observation"},
                  {"tier": "H4", "claim_ids": ["C2"], "text": observation["direction"], "kind": "conceptual_direction"}])
