# Option B — WP0 baseline verification

Implementation started from `1721d6f63aaf76bbc877285cb604675e16e83cbb`.
The 0.2.0 historical freeze, benchmark files and saved evidence remain immutable.
This change introduces checkout rules and a new, non-overwriting inventory and verification command.
No new test or benchmark results are claimed by this document.

## Run on a clean Windows checkout using Rider

Use a new checkout/worktree after the .gitattributes change is committed so an
existing CRLF worktree cannot silently invalidate the raw-byte catalog guards.
Do not reset or discard local changes. Use CPython 3.12 (historically 3.12.10).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe tools/option_b_baseline.py
.\.venv\Scripts\python.exe tools/option_b_baseline.py --verify
```

The first command to the script is inventory-only. The second runs pip check,
all backend tests (including API/editor tests), and the reviewed historical
binary-search witness replay. It records a timestamped report and logs under
results/jobs/option-b-baseline/ (ignored by Git). The historical report is
never rewritten. A clean checkout, exact catalog hashes and matching locked
package versions are required for verification. The existing replay is executed
only after confirming its embedded source against the reviewed SHA-256.

Historical hash differences are reported separately: lf_only is a comparison
aid, not an accepted source identity. different requires investigation, not
rewriting historical hashes. In particular, review api.py and app.js against
the release freeze; do not claim the old measurement belongs to them.

## Remaining WP0 exit gate

- Inspect the fresh report; resolve any environment or fixture hash blocker.
- Run the actual browser/editor journey via Rider in a disposable checkout
  (legacy browser scripts may update tracked historical reports).
- Record its new evidence and the exact tested commit separately.
- Only then mark G0 passed and migrate the core contracts (WP2). WP1 research
  review can proceed independently. Keep external AI disabled until separately approved.
