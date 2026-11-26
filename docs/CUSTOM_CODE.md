# Local pasted-code extension — 26 November 2026

## Delivered user journey

The user selects Dijkstra or Binary Search, chooses كودي الخاص, pastes Python or opens a UTF-8 .py file, confirms ownership/review of the local code, and runs manual or generated tests. The callable contract is solve(payload), returning the problem result. The same finite input contracts and worker apply. There is no Codeforces-wide problem understanding, C++ runner or hostile-code sandbox.

The source editor shows line numbers and a byte counter, supports Tab and Ctrl+Enter, retains per-problem drafts in page memory, and supplies explicit template/bug-example buttons. Source and option edits invalidate previous displayed evidence. The resulting evidence contains submitted source, actual source SHA256, attempts, replay outcomes, trace, claims and a bounded diagnosis summary. A .py import reads file contents, not a server filesystem path. Source stays local; results/runs stores the source with the run.

## API and trust boundary

POST /api/analyze requires exactly one of fixture_id or source. Custom source (maximum 32768 UTF-8 bytes) additionally requires trusted_local_code=true, a loopback client, application/json and X-AlgoXRay-Token from GET /api/session. Existing host/origin checks remain; a cross-site Fetch Metadata header is rejected. The per-process token rotates on restart and is not logged or put in evidence. Browser clients acquire it when running custom source. The server stays bound to 127.0.0.1.

The user explicitly requested direct local source execution, extending the previous catalog-only HTTP boundary. Scope remains code belonging to/reviewed by the local user. These checks prevent unintended browser invocation and do not isolate malicious Python from the user's files, network or privileges. No AST allowlist is advertised as a sandbox. A separate sandbox is still required before public/untrusted execution.

Source is checked by ast.parse and the solve signature without running it, then written byte-for-byte to a randomly named temporary directory. Worker processes close before deletion. Persisted source uses UTF-8 without Windows newline conversion. Concurrent analysis still returns 409, request bodies are capped at 64 KiB, and time/output/event limits remain.

## Diagnostic claims

1. Syntax failure: HTTP 422 with a message, line and column where available; no solver execution.
2. Terminal Python exception: observed type and traceback source line, linked to a matching complete trace exception event. The line is where it manifested, not a proof of root cause. Fingerprints include the exception line to reject unstable locations.
3. Narrow closed-interval binary-search observation: AST identifies direct array/target bindings, lower=0, upper=len(array)-1, while lower<upper, and an immediately following return -1. Actual consecutive line events must show the condition followed by that return with equal integer bounds, the unchanged legal array and a matching remaining target. Different variable names are supported. The claim states those concrete facts and gives a conceptual review direction.
4. Unsupported logic, incomplete trace or trace/output mismatch: witness/trace remains available; no source-specific diagnosis is invented. Timeout is not relabeled as wrong answer or memory exhaustion.

Original reviewed hash-gated fixture adapters remain. Custom source is not assigned an existing adapter by name or expected bug label. Up to 32 simple local variables per event are bounded/copied; missing variables suppress a diagnosis.

## Verification and challenge

62 automated tests passed, including original regressions, exact source/bytes preservation on Windows, temporary-file cleanup, untouched catalog, renamed locals, correct solution control, unsupported-logic/half-open abstention, truncated traces, runtime and syntax locations, missing trust/token, cross-origin/cross-site, non-loopback peers, source/body limits, timeouts and recovery. Evidence: docs/custom-code-tests.xml.

14 browser journeys passed on installed Edge: trust gate, paste and actual analysis, diagnostic navigation, evidence export, edit invalidation/correct solution, abstention, syntax/runtime lines, file import/renaming, per-problem drafts, generated witness, safe text rendering, file limits, mobile layout. No page errors or external requests. Evidence: docs/custom-code-ui-verification.json; source: tools/verify_custom_browser.py.

A Windows newline-translation mismatch was found and fixed by byte-preserving source writes; the exact-source assertion remained. Tests deliberately challenge false diagnosis on a half-open interval and on generic wrong code. Token alone is insufficient for a non-loopback client. No new independent human review, educational study or diagnosis-accuracy estimate is claimed. Earlier 320-trial data and PDF drafts remain historical to their saved source fingerprint.

## Primary references used for this change

- Python 3.12 ast: https://docs.python.org/3.12/library/ast.html — syntax-tree parsing is inspection, not isolation.
- Python 3.12 exec: https://docs.python.org/3.12/library/functions.html#exec — dynamic execution is arbitrary Python, hence the trusted-local scope.
- OWASP CSRF prevention: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html — custom request headers/token plus origin checks as browser request defenses, not a sandbox.

## Next maintenance point

Start with api.py, diagnostics.py, hints.py, worker.py and test_custom_code.py. Changes to a diagnosis need negative controls as well as a failing witness. Capture new research measurements against the new source fingerprint before updating scientific claims. Backups of the pre-change source are under results/backups/custom_code_20261126T122549. User-selected files and the fixture catalog were not overwritten by this extension.
