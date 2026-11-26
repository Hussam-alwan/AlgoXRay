# Architecture and verified boundaries

The user browser loads static HTML, CSS, JavaScript and Cytoscape.js from a loopback FastAPI server. POST /api/analyze resolves either a catalog identifier or explicitly trusted local pasted source and calls the analysis engine. Pasted source is syntax/contract checked without execution, written to a temporary UTF-8 file with exact bytes, then executed through the same worker. The temporary file is removed after evidence persistence. A process-separated, persistent worker executes a fresh namespace for each candidate. The worker source hash must match the registered source snapshot. There is one active HTTP analysis per server process.

## Components

| Component | Owns |
|---|---|
| problems.py | Legal input contracts, output checkers and cross-checked reference answers |
| registry.py | Fixture identity, source bytes/hash/provenance and hash-gated adapter selection |
| generation.py | Hypothesis strategies and a seeded random baseline |
| runner.py / worker.py | Bounded process protocol, execution deadline, output limits and process cleanup |
| engine.py | Discovery, verification replay, shrinking, trace replay and evidence assembly |
| hints.py / diagnostics.py | Verified observations, educational questions, hash-gated adapters, narrow AST/runtime observations and recorded exception locations |
| api.py / cli.py | Local interface, strict request boundaries and explicit trusted-file execution |
| benchmarks/run.py | Frozen trial configuration, raw evidence/CSV and summary derivation |

## Invariants

1. A valid counterexample is checked against the problem's real contract, not a text comparison where outputs may differ legitimately.
2. Dijkstra reference answers must agree between NetworkX Bellman–Ford and an independent small Floyd–Warshall implementation.
3. A witness requires repeated matching failure observations. A disagreement or unstable run does not produce a verified accusation.
4. Shrinking preserves input legality and the failure kind; exception shrinking also preserves exception type. This does not prove that every smaller witness has the identical underlying cause.
5. Events are recorded from the submitted source with independent bounded snapshots. A line event is before execution of that line.
6. Original fixture adapters require an exact reviewed source hash and suitable recorded events. New-source observations require a narrow AST pattern plus consecutive matching line events and values, or the matching terminal exception location. No diagnosis is assigned from a code pattern alone.
7. Missing trace data never gets replaced with simulated events. A truncated or changed trace suppresses detailed diagnosis.
8. Discovery timings stop at the first verified witness and exclude minimization; post-discovery engine callbacks are reported separately.
9. Finite search cannot prove a correct solution. The status is inconclusive when no witness is found.

## Trust model

Registered fixtures and explicitly reviewed local files or pasted source are trusted. POST /api/analyze accepts exactly one of fixture_id or source, never a filesystem path. Custom source requires a loopback peer, explicit trusted_local_code, a random per-process token from GET /api/session in X-AlgoXRay-Token, application/json, and same-origin/non-cross-site browser requests. The token is not retained in evidence or source. Host, origin and token checks limit unintended invocation; they do not sandbox submitted code. The CLI server binds loopback. Fresh worker namespaces prevent simple global state from leaking across test cases; imported modules are not a complete isolation boundary.

The parent kills the worker process tree on hard timeout. stdout and up to 32 simple local-variable snapshots per event are bounded; native blocking calls are handled by the parent timeout. CPU/memory/filesystem/network sandboxing for hostile code is **not implemented**. Do not expose this service as a multi-user/public execution platform.

## Deliberate scope

Two finite algorithm contracts; positive-weight directed graphs; small sorted arrays; adapters for two exact authored fixtures, a narrow closed-interval AST/runtime detector for reviewed custom binary-search sources, and recorded Python exception locations. The research artifact is an integration and technical evaluation. No claim of novel fuzzing, globally minimum witnesses, general root-cause diagnosis, or educational improvement is established by the implementation.

## Engineering decisions

- Approved local trusted-code boundary and Python/HTML/JavaScript architecture follow the single-developer implementation plan.
- Persistent worker avoids paying Python startup for every candidate while resetting the submission namespace per request.
- HTTP analysis is serialized to keep input generation and fixture execution predictable for this prototype.
- A source hash gates semantic adapters; generic tracing and mismatch feedback remain available without an adapter.
- Bibliography, raw results, system behavior and future plans remain separately labeled.

## Pasted-code evidence and compatibility

The editor supports paste, local .py file selection, per-problem in-memory drafts, explicit source provenance, syntax locations, and source-aware invalidation of previous evidence. It does not add submissions to fixtures/catalog.json or relabel unknown source as a known mistake. Exports contain exact submitted UTF-8 source and its SHA256, actual results and trace events. Saved source bytes use UTF-8 without platform newline translation.

AST observation v1 requires direct bindings from payload["array"]/["target"], lower=0, upper=len(array)-1, a top-level while lower<upper immediately followed by return -1, and consecutive recorded condition/return line events with equal bounds and a remaining matching element. It states the observed skipped-element situation and a conceptual direction; it does not prove an arbitrary fix or global root cause. Other code receives a verified witness and trace with explicit abstention when unsupported. Exception-location observations require a complete matching trace and the terminal traceback line/type; caught unrelated exceptions are not selected merely by their presence.

The 320-trial benchmark and original manuscript/poster PDFs are historical measurements/drafts for their saved source fingerprint. This extension has separate automated/API/browser verification; no new accuracy or learning-benefit claim follows from adding the editor.
