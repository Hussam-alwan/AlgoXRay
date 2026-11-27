# AlgoXRay V4 — Dynamic AI Engine
Status: active V4 continuation record, reconciled 27 November 2026. The bounded local prototype is implemented; the full research/generalization gates are still partial. The original specification follows the verified checkpoint below.
Baseline: c84d0c9ba1eb1a4c7da857a5454a4ace90f8843d (option-b).
Owner objective: debug previously unseen competitive-programming problems with actual execution, evidence-linked graphics and AI-assisted hypotheses, without adding problem-specific conditions to the engine for every new problem.

## Active checkpoint - 27 November 2026

This is the current plan. Core/Option B handoffs and the earlier V4 status document are historical. Runtime code is measured at `b65f596fca34c487777641ebd47e97ba5161752b`; later documentation, navigation and evidence packaging do not change that engine. V4 lives in `D:/icips-v4` on `v4-dynamic-ai`, port 8002. V3 stays in `D:/icips`, port 8001.

Owner additions: publish all intended project changes to GitHub, and measure execution time for each code block for CP. Code, tests, documentation and the explicit synthetic/public evidence export belong in Git. Credentials, personal submissions, package stores, quota databases, environments and private reviewer keys do not.

| Package | Verified implementation | Open boundary or remaining task |
|---|---|---|
| WP9 | Separate worktree and dependencies; preserved archives; pinned dedicated Docker worker with isolation probes; local Qwen 7B schema/diagnosis/abstention smoke | Independent threat assessment and authenticated adversarial trace evidence are not complete; public execution stays disabled |
| WP10 | Ollama, Gemini, Groq and OpenRouter adapters; strict output schema validation; timeout, local cancellation, consent and local request limits; measured local token/latency metadata | Optional Qwen Cloud adapter and cache are not implemented; remote cancellation and global account quotas are not guaranteed |
| WP11 | Immutable reviewed packages, restart persistence and tamper checks; stdio field grammar with matrices; Codeforces text import; draft/reference proposal and review controls; five data-driven demos | General mathematical constraints/checkers and independent review of arbitrary references remain out of scope for this bounded release |
| WP12 | Seeded boundary/random/Hypothesis generation, AI case suggestions, legal reduction, explicit statuses, three replays and independent reference disagreement handling | General multi-testcase/cross-field constraints, huge CP input ranges and multiple-valid-output checkers are not implemented |
| WP13 | Observed graph, source navigation, actual call frames, variables, side-by-side trace, restricted CFG, supported data/control links and coverage ranking | General alias/heap/call slicing and automatic semantic alignment remain unsupported |
| WP14 | Real local/cloud proposals; schema and event-anchor checks; recomputed scalar facts; execution-tested hypotheses; deterministic core survives AI failure | Free-form causal explanations remain hypotheses; no independent localization accuracy estimate |
| WP15 | Reviewed patch proposals, diff, immutable history, witness and named regression checks, cancellation, export and live browser journeys | Broader repair/usability evidence and guaranteed remote inference termination remain unproven |
| WP16 | Public paired seven-family pilot, local model smoke, 182 tests, 19 browser journeys, five demos, clean reproduction and explicit public evidence manifest; scoped primary-paper comparison | Independent unseen student corpus, human factuality/localization ratings, matched multi-problem AI ablation, author/venue approval and submission remain pending |
| WP17 (owner addition) | Bounded block and line profiling: wall/CPU, self/inclusive, counts/averages, source/graph links, correct-code profiling, CSV/JSON, partial/unavailable states and mobile | Instrumented one-input timings are not judge runtime, a Big-O inference, or a calibrated CP performance benchmark |

### Verification snapshot

- 182/182 tests on Windows after schema hardening; one existing Starlette deprecation warning. Earlier Linux baseline 167/167, profiling checkpoint 174/174. Counts are software tests, not students or independent programs.
- 19/19 browser journeys, with no page errors or external browser requests. An initial mobile table overflow failed; fixed and the failed report is retained.
- Five authored demos passed; paired public pilot found 7/7 faulty variants, 0/7 corrected controls accused, 21 replay matches. These are exposed public adaptations, not an unseen student corpus.
- Qwen2.5-Coder 7B Q4_K_M, digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`, context 4096: constrained draft transport 10.594 s, diagnosis 4.391 s, abstention 0.421 s; all three schema-valid, empty-evidence abstention passed. The draft transport uses a fixed candidate, not an open-ended authoring accuracy test. Peak sampled whole-board GPU memory 5003 MiB; it is not isolated peak model allocation.
- [Continuation evidence](v4-evidence/continuation/MANIFEST.json), [profiling semantics](V4_PROFILING.md), [earlier expanded checkpoint](V4_EXPANDED_RELEASE.md), and [reviewable delivery draft](v4-delivery/README.md).

No claim of universal debugging, first-of-kind novelty, improved learning, hostile-code security or general causal accuracy is made. Work remaining for independent participants or conference decisions is kept open rather than simulated. The original checklist below is a specification history; the table above is the current completion record.

## Scope and constraints
- First release: Python, conventional stdin/stdout and existing solve(payload) contracts, bounded deterministic noninteractive problems. No promise of all Python programs, interactive judges, arbitrary languages or guaranteed fault localization.
- Keep existing three problem contracts, archived results, evidence schemas, reviewer packets and V3 demo intact. Work on a new branch `v4-dynamic-ai` from this baseline after the planning commit. Run V4 on loopback port 8002, keep V3 on 8001; separate worktree/environment or pinned V3 checkout for concurrent use.
- Hardware target supplied by owner: Windows, 16 GB RAM, RTX 2070 8 GB. Start Qwen2.5-Coder 7B Q4_K_M via Ollama (published download ~4.7 GB; runtime memory extra); context 4096, one inference at a time; 3B fallback if memory/latency unacceptable. No paid provider or automatic cloud fallback. No cloud submission until explicit data/cost consent and valid credentials; no keys in git/UI/logs.
- Rider preflight: clean option-b; Docker and nvidia-smi discoverable; ollama not on PATH; Gemini and DashScope key env checks false. This does not establish Docker daemon, GPU driver or API availability. Verify during phase 0.
- Paper Review skill was not exposed in the previous conversation's available skill catalog. When provided, apply it to manuscript/prior work in the parallel research lane; do not treat it as installed or necessary to launch V4.

## Architecture
Problem text or approved URL -> draft declarative contract -> independent review/controls -> approved immutable package.
Student source + package -> bounded runner -> legal test search -> counterexample -> reduction -> replay -> trace + expected/actual outputs.
Trace -> observed execution graph, timeline, supported data/control links, suspicious ranking -> AI structured hypotheses -> independent evidence validators -> verified facts / unverified hypotheses / abstention -> interactive UI.
Optional repair -> separate version -> witness + unseen regression tests. Never overwrite original.
AI is a proposal service, not oracle, verifier, renderer of fabricated trace or execution authority. New package data should use a limited declarative grammar interpreted by trusted code; no eval/exec in web process. Executable references need isolated execution and explicit approval.

## Work packages and exit gates
### WP9 — Baseline, execution boundary and model setup
- [ ] Record V3 source, dependency and result hashes; create dedicated V4 branch/worktree; test V3 archive replay and run existing pytest baseline unchanged. Capture missing prior V3 reports.
- [ ] Inspect free disk, RAM, nvidia-smi driver/VRAM, Docker engine and current ports. Install official Ollama for Windows if absent; bind localhost only; pull qwen2.5-coder:7b; record model digest, version and settings. Source: https://ollama.com/library/qwen2.5-coder:7b .
- [ ] Run three local schema-constrained smoke tasks (contract draft, diagnosis hypothesis, abstention). Measure actual latency, peak memory and schema failures; reduce context or use 3B fallback only if measured need. Verify ollama ps and no cloud egress.
- [ ] Design/implement isolation before executing AI-generated or untrusted code: nonprivileged short-lived worker/container, no host mounts or Docker socket, no network, read-only root, bounded tmpfs, CPU/RAM/PIDs/output/time budgets and cleanup; keep model/server credentials outside worker. Test file access, network, resource exhaustion, process-tree cleanup and timeout. Docker alone is not a security proof; public service remains disabled pending independent threat assessment. Trusted-local legacy path explicitly labeled.
Gate G9: old release still usable; model live smoke or explicit blocker with deterministic mock; isolation negative controls passed before generated code execution.

### WP10 — Interchangeable providers
- [ ] Define AIProvider interface, typed request/response, deadline, cancellation, size/token budgets, schema validation and request IDs; implement mock + Ollama first, Gemini and Qwen cloud adapters configurable but off by default.
- [ ] Provider/model settings, model discovery, health endpoint, quota/rate-limit error states, retry only safe transient requests; bounded attempts; local-only fallback when selected. Cache by source/contract/evidence/prompt/model version, never cache secrets.
- [ ] Unit tests for malformed JSON, invented fields, timeout, provider unavailable, injection in source/comments, cancellation, empty result and no network in mock mode.
Gate G10: valid structured result from local model or explicit unavailable state; deterministic core still works when provider fails.

### WP11 — General problem authoring
Existing anchors: problem_registry.py uses a hard-coded REGISTRY; package_review.py checks only installed ProblemSpec. Refactor once to resolve immutable trusted built-ins and approved external data packages by id/version/hash. Avoid mutable global registration and arbitrary imports.
- [ ] Define bounded manifest and declarative grammar for integer/string/list fields, dependent lengths/ranges, token/line encodings, output policy, permitted generators/reducers, examples, provenance and resource limits. Start exact/token output and explicit special checker subset; reject unsupported semantics.
- [ ] Draft from user text (URL import separate, allowlisted domains/public access, no credentials, no SSRF, paste fallback); AI extracts structured constraints with source snippets and unresolved fields. UI enables editing, review, validation and explicit approve. Treat problem text as untrusted data, not instructions.
- [ ] Reference code supplied by user or proposed by AI stays draft until independently reviewed; require independently obtained controls and small exhaustive/brute-force or second independent reference where feasible; oracle disagreement blocks accusations. Keep samples separate from holdout; version and hash all components. Do not let student solution determine expected answers.
- [ ] Save approved packages to versioned local store, reload after restart, reject unapproved/tampered packages; list dynamically via API. Add package by data only with frozen engine/API hashes.
Gate G11: Hamburgers plus at least two distinct new problems loaded through author UI without per-problem engine changes. Reference checks and legal generation validated; unsupported cases explicit.

### WP12 — General execution, generation and reduction
- [ ] Extend worker/runner and codec to support Python stdin/stdout with exact input bytes, bounded stdout/stderr, process exit, traceback and source hash; retain solve(payload) adapter. Record output normalization policy and do not rewrite student code or hide parse errors.
- [ ] Generate legal inputs from schema (seeded random, Hypothesis, boundary cases); AI may suggest cases but validator must accept. Deduplicate and limit. Implement generic reduction preserving validity, failure kind, and measured size; replay three times; handle flaky, timeout, invalid and oracle disagreement distinctly.
- [ ] Add independent test fixtures for multiple cases, whitespace, multiple valid outputs where supported, recursion, imports, huge integers, empty/oversized input and output, cancellation; old bundle compatibility and new revision verification.
Gate G12: correct controls not falsely accused within tested sample, deliberate bugs produce legal reproducible witnesses, no hidden transformations. Hamburgers must accept the owner's ordinary input()/print() implementation; do not assume it contains a bug.

### WP13 — Graphical debugging (core requirement)
Reuse existing frontend, Cytoscape and trace event identity. Extend dependencies.py beyond consecutive +,-,* integer assignments only where evidence supports semantics.
- [ ] Build generic observed execution graph from frame/event IDs (calls, returns, line transitions), with counts for repeated edges, step navigation and source synchronization. Distinguish observed path from static CFG; label branches only when verified. Never guess missing nodes.
- [ ] Add variable timeline, changed values, arrays/tables/JSON, call stack, loop iterations and before/after snapshots; zoom/pan/filter, keyboard, Arabic RTL and LTR code; explicit truncated/unsupported state.
- [ ] Add bounded AST CFG for supported syntax and recorded control edges, dynamic def-use links keyed by frame and event; verify assignment/operand values and supported branch relationships. Track ambiguity for aliasing, mutation, library calls and unsupported syntax. General backward dependency slice to output when supported, not proof of root cause.
- [ ] Side-by-side student/reference runs on same witness, align only comparable input/output or explicitly defined semantic checkpoints; never assume matching line numbers or variable names or that differing implementation is wrong. Color observed divergence separately from suspected fault.
Gate G13: new arbitrary supported Python source yields interactive graph, timeline, click-to-source and actual trace events without problem-specific rendering; Playwright verifies recursion, loop, missing/truncated trace, mobile, output discrepancy and evidence export.

### WP14 — AI diagnosis and verification
- [ ] AI receives approved problem contract, source, actual/expected output, compressed trace slices and ranked evidence; schemas for observed-value, comparison, dependency and candidate hypothesis. All refs include source hash/event/frame/line IDs. Request minimal relevant context, no secrets.
- [ ] Independently recompute facts from immutable evidence, reject false values/IDs or unsupported relationships, classify claims verified / hypothesis / contradicted / unsupported. Generate verified prose from facts; AI free text never promoted to verified by ID alone. Preserve status when unable to localize.
- [ ] Hypothesis tests: legal additional cases, bounded probes, metamorphic checks only when contract supports them; record pass/fail and competing explanations. Render evidence links directly in graph.
Gate G14: malicious or fabricated model outputs cannot create verified claims; no provider required for witness/trace/graph. Test unseen bug families, distinguish symptom from cause.

### WP15 — Optional repair and user workflow
- [ ] Add explicit repair request with proposed patch/diff, new immutable source identity; run in isolated worker on original witness and independent regression set, compare evidence; accept/reject manually. No claim of general correctness from finite tests.
- [ ] UI: paste problem/code, choose provider, review contract, launch progress/cancel, witness, graph/timeline, hypotheses, rerun/export; provider budget/privacy banner; local mode by default; old three problems remain usable.
Gate G15: real browser end-to-end for new problem, correct code, bad code, unsupported contract, disagreement, timeout, AI outage, cancellation, repair regression and evidence replay.

### WP16 — Scientific evaluation and delivery (parallel literature review from WP9)
- [ ] Preserve V3 measured facts (450 runs/225 faulty witnesses/675 replay matches; 65/75 specific observations on exposed development corpus; external V3 270 runs/130 of 135 faulty trials/0 of 135 control accusations; 15/45 specific observations full arm). These are not V4 results or causal localization accuracy.
- [ ] Read closest papers in full (Code Hunt/Pex4Fun, Python Tutor, ITAP, CodeHelp, relevant LLM+localization work); extract DOI, method, evaluation, limitations with page refs. Apply Paper Review skill when accessible. Maintain claims register, no novelty priority assertion without evidence.
- [ ] Freeze separate development, controls and unseen evaluation families; collect licensed real programs with provenance, label mutants separately. Plan 30–60 independent solutions where feasible, disclose smaller/correlated sets; keep reviewer keys private.
- [ ] Compare V3, V4 no AI, model source-only, + witness, + trace, + verification under matched inputs/model/budgets. Measure discovery rate, false accusation, replay, shrink, support/abstention, human factuality, Top1/3/5 on independent labels, latency/cost/token usage, graph evidence correctness. Distinguish control and faulty denominators, report failures. Do not simulate human reviewers.
- [ ] Full regression, browser tests, clean-checkout reproduction, raw manifest/hashes; update manuscript/poster/demo only with measured results and actual screenshots. Author approves claims and venue format before submission. Keep V3 conference-ready draft available; do not delay the submission merely for speculative V4 improvements.
Gate G16: reproducible versioned reports, documented limitations, independent review or explicit pending status, no fabricated results.

## First vertical slice: Hamburgers
Use problem 371C statement (https://codeforces.com/problemset/problem/371/C) or owner-provided text. Implement as a new package, not an engine special case. Independent small brute-force reference and reviewed general reference; validated recipe alphabet/stock/prices/budget from statement. Preserve owner's original Python stdin/stdout solution. Check correct control and controlled mutations (e.g. wrong comparison, omitted ingredient, insufficient upper bound under legal case); do not label original faulty unless a real legal witness exists. Show same input, actual and expected output, execution graph of loop/calls/variables, AI hypothesis anchored to evidence. Add distinct non-binary-search problems to prove extensibility, e.g. string counting and graph reachability.

## Start order and commands
1. Freeze baseline and isolate worktree; verify runtime with `nvidia-smi`, `docker version`, `docker info`, free disk; use official Windows installer https://ollama.com/download/windows if needed. Installation and model download are separate from planning.
2. In Windows terminal: `ollama pull qwen2.5-coder:7b`, `ollama list`, `ollama run qwen2.5-coder:7b`; smoke via localhost:11434/api/chat using bounded context and JSON schema; verify actual GPU usage with `ollama ps`. Record measurements, not estimated throughput.
3. Run existing baseline: `D:/icips/.venv/Scripts/python.exe -m pytest backend/tests -q` in current baseline root; for V4 use its own pinned environment. Run actual browser acceptance using existing tools with new output directories. Start V4 on 127.0.0.1:8002 only after branch/env ready; V3 stays pinned.
4. Implement WP9 -> WP10 -> WP11/WP12 -> WP13 (generic graph usable even without AI) -> WP14 -> WP15 -> WP16. Review after every gate; continue independent work if a provider is unavailable, but never mark blocked gate done.
5. Every task has a test and artifact. Commit small changes, record test commands/exit codes, update this checklist only after verified completion. Do not overwrite existing results or call previous results new. No secret values in reports.
