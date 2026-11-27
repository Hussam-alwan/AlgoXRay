# AlgoXRay V4 — Dynamic AI Engine
Status: active V4 continuation record, reconciled 27 November 2026. The bounded local prototype is implemented; the full research/generalization gates are still partial. The original specification follows the verified checkpoint below.
Baseline: c84d0c9ba1eb1a4c7da857a5454a4ace90f8843d (option-b).
Owner objective: debug previously unseen competitive-programming problems with actual execution, evidence-linked graphics and AI-assisted hypotheses, without adding problem-specific conditions to the engine for every new problem.

## Current continuation - 27 November 2026

The active runtime is `5f58330538f3dda0f73435bc3640f79531cd0bf7`, deployed locally on 8002 and pushed to main/v4-dynamic-ai. V3 remains on 8001. Latest software evidence: 239 tests, 27 normal browser checks plus 7 failure/fixture checks, and a live local timeout/source-link smoke.

[Timeout diagnosis and opt-in profiling AI](V4_TIMEOUT_DIAGNOSIS.md) documents the verified change. Local inference quality remains limited: an initial response contradicted itself; a later tuned response abstained. Both are retained in [the evidence inventory](v4-evidence/timeout-diagnosis-20261127/MANIFEST.json). No new independent accuracy claim or full seven-family re-evaluation is made.

The owner's Engine/Agent roadmap was reviewed against source and evidence: [full Arabic comparison](ENGINE_AGENT_ROADMAP_COMPARISON_AR.md), [32-item machine-readable mapping](ENGINE_AGENT_ROADMAP_STATUS.json). The mapping classifies 14 items as implemented within bounded current scope, 14 partial and 4 missing. These counts are not a project-completion percentage or authorization to implement the proposed roadmap automatically.

Priority gaps found: stdin.buffer compatibility, repeated reduction with FailureSignature, complete evidence bundle, branch coverage/feedback, then an explicit Agent state/tool/budget layer and measured adaptive ranking. Knowledge-base, language expansion and public execution require their own data/security design.

Earlier clean-checkout reproduction and benchmark metrics below retain their original commits. They are not relabeled as new measurements of this continuation.

## Earlier completion checkpoint - 27 November 2026

This is the current plan. Core/Option B handoffs and earlier V4 status documents are historical. The verified runtime at that earlier checkpoint was `1aee128bfaf33313fb01e9dcf8d5ffd70859e13e`; the completion export identifies the exact runtime, ablation and packaging commits separately. V4 lives in `D:/icips-v4`, port 8002; V3 is preserved in `D:/icips`, port 8001.

Owner additions: publish intended project code, tests, documentation and explicit synthetic/public evidence to both `main` and `v4-dynamic-ai`; measure execution time for each supported code block for CP. Credentials, private submissions, package stores, quota databases, environments and private reviewer keys stay outside Git.

The bounded software tasks in [the current task ledger](V4_TASK_STATUS.json) and [the Arabic completion report](V4_COMPLETION_20261127_AR.md) are complete at 100% of their named scope. The research and generalization requirements below remain separate; no overall project percentage is inferred by averaging software checks.

| Package | Verified implementation | Remaining boundary |
|---|---|---|
| WP9 | Dedicated worktree/environment/worker, preserved V3, model digest, fresh clean reproduction, 11+3 local isolation probes | Independent adversarial security assessment and authenticated trace evidence remain open; public execution disabled |
| WP10 | Ollama, Gemini, Groq, OpenRouter and configured Qwen Cloud adapter; schema, request IDs, budgets, consent, cancellation states; opt-in versioned local RAM cache and clear controls | Qwen Cloud live call not tested without credentials/consent; remote termination and global provider quotas not guaranteed |
| WP11 | Immutable packages, persistence/tamper checks, editable text drafts, exact quotation/literal provenance, unresolved gates, exclusive field schemas, bounded finite-domain/second-reference audit | Quotations do not prove semantic extraction accuracy; distinct reference code does not prove independent origin; arbitrary references need review |
| WP12 | Seeded random/boundary/Hypothesis search, legal AI probes, reduction/replay, empty words/lists, bounded unordered and floating output policies, explicit disagreement/error states | General multi-testcase/cross-field constraints, huge CP ranges and arbitrary multiple-valid-output checkers remain unsupported |
| WP13 | Observed source-linked graphs, call frames, arrays, timeline, same-frame snapshots, frame/event filters, pan/layout, observed loop entries, restricted CFG/data/control/def-use and ranking | Heap/alias/call slicing and automatic semantic alignment remain unsupported; partial traces give lower bounds |
| WP14 | Bounded hashed diagnostic context, explicit omissions, ranked evidence, scalar facts and primitive if/while condition recomputation; invalid claims cannot become verified causal prose | General causal diagnosis and independent localization accuracy remain unmeasured |
| WP15 | Immutable reviewed repair/diff/history/regression workflow, cancellation/export, 25 normal and 5 negative real browser checks | Wider repair/usability study and guaranteed remote inference termination remain open |
| WP16 | 223 tests, clean seven-step reproduction, five demos, fresh paired public seven-family pilot, 21 local matched context calls plus same-response verification, raw evidence and hashes, measured research supplement | Independent unseen programs, human ratings, common-contract V3 study, author/venue approval and submission remain open |
| WP17 | Supported block/line wall+CPU, self/inclusive, visits/averages, source/graph links, correct-code profiling, CSV/JSON, partial states and mobile | Instrumented one-input timing is not judge runtime, Big-O inference or a calibrated CP benchmark |

### Current verification

- 223/223 Windows tests in the development run and the clean checkout. One existing Starlette deprecation warning.
- 25 normal + 5 negative browser journeys, no page errors or external browser requests. Outage is deliberately injected in a test-only process, never a production hook.
- Five authored demos; fresh public paired pilot: 7/7 faulty variants observed, 0/7 corrected variants accused, 21 replay matches. Exposed adaptations are not independent student submissions.
- Seven-step same-machine reproduction uses a fresh Python environment and the same pinned Docker worker. The invocation used symbolic HEAD; [SOURCE_FREEZE.json](v4-evidence/completion-20261127/SOURCE_FREEZE.json) resolves the exact checkout commit.
- Local Qwen cache miss/hit/clear/miss passed. An open-ended controlled draft example finally returned the dependent length and quoted bounds; two earlier failures are retained. This is one example, not general authoring accuracy.
- Local ablation on seven exposed families: source-only edit-line Top1/3/5 = 1/3/5 of 7; witness = 1/3/4; trace = 3/6/6. The same-response validator retained 3/6/6. No additional model call or causal validation is claimed for the last arm. All 21 inference requests completed; raw requests, model revision, schema and budgets are retained.
- Of 25 scalar fact claims in the trace arm, 16 matched recorded snapshots and 9 remained unsupported. Claims in arms without supplied events remained unsupported. There were no live trace-arm branch claims; branch checks are unit-tested.
- [Completion evidence](v4-evidence/completion-20261127/MANIFEST.json), [provider completion](V4_PROVIDER_COMPLETION.md), [profiling semantics](V4_PROFILING.md), [measured research supplement](v4-delivery/supplement_20261127.md).
- [Earlier continuation evidence](v4-evidence/continuation/MANIFEST.json) and its 182-test/19-browser PDFs remain historical, unchanged.

The original exit-gate checklist below is a requirements history, not the current task status. General debugging, first-of-kind novelty, improved learning, hostile-code security and universal causal accuracy are not established by these tests.

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

## Historical work packages and exit gates
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
