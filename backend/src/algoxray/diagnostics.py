"""Narrow AST/runtime observations. No arbitrary root-cause inference or source whitelist."""
import ast


def _bindings(function):
    bindings = {}
    for statement in function.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target, value = statement.targets[0], statement.value
        if isinstance(target, ast.Name):
            bindings[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
            for left, right in zip(target.elts, value.elts):
                if isinstance(left, ast.Name):
                    bindings[left.id] = right
    return bindings


def _payload_key(node, argument, key):
    return (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
            and node.value.id == argument and isinstance(node.slice, ast.Constant) and node.slice.value == key)


def _minus_one(node):
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and node.operand.value == 1


def custom_observation(bundle, submission):
    if bundle["trace_status"] != "complete" or bundle["status"] != "witness_found":
        return None
    events = bundle["events"]
    if bundle["failure_kind"] == "exception":
        error = bundle.get("exception") or {}
        event = next((e for e in reversed(events) if e["kind"] == "exception"
                      and e["line"] == error.get("line") and e["function"] == error.get("function")
                      and e.get("exception_type") == error.get("type")), None)
        if event:
            return {"event_ids": [event["event_id"]], "source_lines": [event["line"]],
                    "text": f"ظهر الاستثناء {error['type']} أثناء تنفيذ السطر {event['line']} في الدالة {event['function']}.",
                    "direction": "افحص قيم المتغيرات في هذا الحدث والمدخل الذي أدى إلى الاستثناء. موضع ظهوره لا يثبت وحده السبب الجذري.",
                    "adapter_id": "python_exception_location_v1"}
        return None
    if bundle["problem_id"] == "max_subarray_v1" and bundle["failure_kind"] == "wrong_answer":
        values = bundle["case"]["array"]
        final = events[-1] if events else {}
        if max(values) < 0 and bundle["observed_output"] == 0 and final.get("kind") == "return" and final.get("function") == "solve" and type(final.get("return_value")) is int and final["return_value"] == 0:
            return {"event_ids":[final["event_id"]],"source_lines":[final["line"]],
                    "text":f"أعاد السطر {final['line']} الصفر رغم أن جميع العناصر سالبة. كل مقطع غير فارغ هنا مجموعُه سالب، فلا يمكن أن يكون الصفر جواباً قانونياً.",
                    "direction":"راجع هل تسمح تهيئة المجموع أو تحديثه بمقطع فارغ؛ افحص القيم السابقة قبل تغيير الكود.",
                    "adapter_id":"max_subarray_zero_negative_v1"}
        return None
    if bundle["problem_id"] != "binary_search_v1" or bundle["failure_kind"] != "wrong_answer":
        return None
    try:
        tree = ast.parse(submission.source.removeprefix("\ufeff"))
    except (SyntaxError, ValueError, RecursionError):
        return None
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "solve"), None)
    if function is None or len(function.args.posonlyargs + function.args.args) != 1:
        return None
    if bundle["observed_output"] != -1:
        # The return event has post-evaluation values. Only attribute a plain local return.
        actual = bundle["observed_output"]
        final = events[-1] if events else {}
        if final.get("kind") != "return" or final.get("function") != "solve" or final.get("return_value") != actual:
            return None
        returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)
                   and node.lineno == final["line"] and isinstance(node.value, ast.Name)]
        if len(returns) != 1:
            return None
        name = returns[0].value.id
        if type(final["locals"].get(name)) is not int or final["locals"][name] != actual:
            return None
        array, target = bundle["case"]["array"], bundle["case"]["target"]
        check = (f"القيمة عند الفهرس {actual} هي {array[actual]} والهدف {target}"
                 if 0 <= actual < len(array) else f"الفهرس {actual} خارج مصفوفة طولها {len(array)}")
        return {"event_ids": [final["event_id"]], "source_lines": [final["line"]],
                "text": f"أعاد السطر {final['line']} قيمة {name} وهي {actual}. {check}.",
                "direction": "تتبّع كيف اختير هذا الفهرس، وافحص شرط التطابق قبل إرجاعه.",
                "adapter_id": "python_returned_index_v1"}
    argument = (function.args.posonlyargs + function.args.args)[0].arg
    bindings = _bindings(function)
    arrays = [name for name, value in bindings.items() if _payload_key(value, argument, "array")]
    targets = [name for name, value in bindings.items() if _payload_key(value, argument, "target")]
    line_events = [event for event in events if event["kind"] == "line" and event["function"] == "solve"]
    for index, statement in enumerate(function.body[:-1]):
        if not isinstance(statement, ast.While):
            continue
        condition = statement.test
        terminal = function.body[index + 1]
        if not (isinstance(condition, ast.Compare) and len(condition.ops) == 1
                and isinstance(condition.ops[0], ast.Lt) and isinstance(condition.left, ast.Name)
                and isinstance(condition.comparators[0], ast.Name)
                and isinstance(terminal, ast.Return) and _minus_one(terminal.value)):
            continue
        lower, upper = condition.left.id, condition.comparators[0].id
        initial_lower, initial_upper = bindings.get(lower), bindings.get(upper)
        if not (isinstance(initial_lower, ast.Constant) and type(initial_lower.value) is int and initial_lower.value == 0
                and isinstance(initial_upper, ast.BinOp) and isinstance(initial_upper.op, ast.Sub)
                and isinstance(initial_upper.right, ast.Constant) and initial_upper.right.value == 1
                and isinstance(initial_upper.left, ast.Call) and isinstance(initial_upper.left.func, ast.Name)
                and initial_upper.left.func.id == "len" and len(initial_upper.left.args) == 1
                and isinstance(initial_upper.left.args[0], ast.Name)):
            continue
        array = initial_upper.left.args[0].id
        if array not in arrays:
            continue
        for position, event in enumerate(line_events[1:], 1):
            previous = line_events[position - 1]
            if event.get("frame_id") != previous.get("frame_id"):
                continue
            if event["line"] != terminal.lineno or previous["line"] != statement.lineno:
                continue
            local = event["locals"]
            left, right, values = local.get(lower), local.get(upper), local.get(array)
            if not (type(left) is int and type(right) is int and left == right and type(values) is list
                    and values == bundle["case"]["array"] and 0 <= left < len(values)):
                continue
            if previous["locals"].get(lower) != left or previous["locals"].get(upper) != right:
                continue
            if not any(name in local and local[name] == bundle["case"]["target"] and values[left] == local[name] for name in targets):
                continue
            return {"event_ids": [previous["event_id"], event["event_id"]],
                    "source_lines": [statement.lineno, terminal.lineno],
                    "trace_roles": {"lower": lower, "upper": upper, "array": array},
                    "text": f"في السطر {statement.lineno} أصبح {lower} = {upper} = {left}، لذلك شرط < لا يتحقق. ثم أعاد السطر {terminal.lineno} القيمة -1 رغم وجود العنصر المطلوب عند الفهرس {left}.",
                    "direction": "راجع استمرار البحث أو فحص العنصر المتبقي عندما يتساوى الحدّان، مع الحفاظ على إنهاء الحلقة.",
                    "adapter_id": "python_closed_interval_ast_v1"}
    return None
