"""Bounded, observational line/block timings for the isolated Python worker.

The class is embedded as trusted source in the minimal guest bootstrap. Clocks
exclude time spent inside our trace callback, but this is still an instrumented
run: interpreter tracing, container throttling and library costs remain.
"""
import ast
import inspect
import time


class ExecutionProfiler:
    def __init__(self, source, enabled=True, max_events=100000):
        self.enabled = enabled
        self.max_events = max_events
        self.event_count = 0
        self.truncated = False
        self.stack = []
        self.frames = {}
        self.lines = {}
        self.blocks = []
        self.last = None
        self.callback_wall_ns = 0
        self.callback_cpu_ns = 0
        self.start = None
        if not enabled:
            return
        try:
            tree = ast.parse(source)
            if sum(1 for _ in ast.walk(tree)) > 6000:
                self.truncated = True
                return
        except (SyntaxError, RecursionError):
            return
        def block(node, scope, kind, name=None, first=None):
            if len(self.blocks) >= 128:
                self.truncated = True
                return
            row = dict(id="B" + str(len(self.blocks) + 1), kind=kind,
                       name=name or kind, scope=scope, line=first or node.lineno,
                       end_line=getattr(node, "end_lineno", len(source.splitlines())),
                       hits=0, self_wall_ns=0, self_cpu_ns=0,
                       inclusive_wall_ns=0, inclusive_cpu_ns=0)
            self.blocks.append(row)
            return row
        block(tree, 0, "module", "<module>", 1)
        def visit(node, scope, depth=0):
            if depth > 120:
                self.truncated = True
                return
            for child in ast.iter_child_nodes(node):
                child_scope = scope
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    child_scope = min([child.lineno] + [d.lineno for d in child.decorator_list])
                    block(child, child_scope, "function", child.name)
                elif isinstance(child, (ast.For, ast.AsyncFor, ast.While, ast.If,
                                        ast.With, ast.AsyncWith, ast.Try, ast.TryStar, ast.Match)):
                    block(child, scope, type(child).__name__.lower())
                visit(child, child_scope, depth + 1)
        visit(tree, 0)

    def tick(self, wall, cpu):
        if not self.enabled or self.truncated or self.last is None:
            return
        dw, dc = max(0, wall - self.last[0]), max(0, cpu - self.last[1])
        for pos, ident in enumerate(self.stack):
            state = self.frames[ident]
            row = state.get("row")
            if row is None:
                continue
            row["inclusive_wall_ns"] += dw
            row["inclusive_cpu_ns"] += dc
            leaf = pos == len(self.stack) - 1
            if leaf:
                row["self_wall_ns"] += dw
                row["self_cpu_ns"] += dc
            for b in state["blocks"]:
                b["inclusive_wall_ns"] += dw
                b["inclusive_cpu_ns"] += dc
                if leaf:
                    b["self_wall_ns"] += dw
                    b["self_cpu_ns"] += dc

    def event(self, frame, kind, frame_id):
        if not self.enabled or self.truncated:
            return
        self.event_count += 1
        if self.event_count > self.max_events:
            self.truncated = True
            return
        ident = id(frame)
        if kind == "call":
            scope = 0 if frame.f_code.co_name == "<module>" else frame.f_code.co_firstlineno
            self.frames[ident] = dict(scope=scope, row=None, blocks=[])
            self.stack.append(ident)
            for b in self.blocks:
                if b["scope"] == scope and b["kind"] in ("module", "function"):
                    b["hits"] += 1
        if kind == "line" and ident in self.frames:
            state = self.frames[ident]
            key = (frame_id, frame.f_lineno)
            if key not in self.lines and len(self.lines) >= 384:
                self.truncated = True
                return
            row = self.lines.setdefault(key, dict(frame_id=frame_id, line=frame.f_lineno,
                function=frame.f_code.co_name, hits=0, self_wall_ns=0, self_cpu_ns=0,
                inclusive_wall_ns=0, inclusive_cpu_ns=0))
            row["hits"] += 1
            state["row"] = row
            state["blocks"] = [b for b in self.blocks if b["scope"] == state["scope"]
                and b["line"] <= frame.f_lineno <= b["end_line"]]
            for b in state["blocks"]:
                if b["kind"] not in ("module", "function") and b["line"] == frame.f_lineno:
                    b["hits"] += 1
        if kind == "return" and ident in self.frames:
            self.stack.remove(ident)
            del self.frames[ident]

    def resume(self, entered_wall, entered_cpu):
        wall, cpu = time.perf_counter_ns(), time.process_time_ns()
        self.callback_wall_ns += max(0, wall - entered_wall)
        self.callback_cpu_ns += max(0, cpu - entered_cpu)
        self.last = (wall, cpu)

    def report(self, status, execution_wall_ns, execution_cpu_ns):
        return dict(version=1, status="disabled" if not self.enabled else
                    "partial" if self.truncated or status != "ok" else "complete",
                    method="trace_segments_excluding_callback",
                    clocks=dict(wall="perf_counter_ns", cpu="process_time_ns"),
                    execution_wall_ns=execution_wall_ns, execution_cpu_ns=execution_cpu_ns,
                    callback_wall_ns=self.callback_wall_ns, callback_cpu_ns=self.callback_cpu_ns,
                    timed_events=self.event_count, event_budget=self.max_events,
                    lines=list(self.lines.values()), blocks=self.blocks,
                    scope="Instrumented single-thread Python execution, not judge runtime. "
                          "Self excludes traced child calls; inclusive includes them. "
                          "Nested blocks and recursive inclusive times overlap; do not add rows. "
                          "Loop hits count header visits, including the final condition check. "
                          "Wall includes waiting and throttling; CPU excludes sleep. "
                          "Unvisited blocks have zero hits. Guest observations are not authenticated.")


PROFILE_BOOTSTRAP = "import ast, time\n" + inspect.getsource(ExecutionProfiler) + "\n"


def attach_profile(graph, execution):
    """Join timings by actual frame and source line; never infer missing timing."""
    profile = execution.get("profile", {"status": "unavailable", "lines": [], "blocks": []})
    graph["profile"] = profile
    timings = {(r["frame_id"], r["line"]): r for r in profile.get("lines", [])}
    for node in graph["nodes"]:
        node["timing"] = timings.get((node["frame_id"], node["line"]))
    return graph
