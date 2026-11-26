# Reproduce Option B v2

Measured engine/UI revision: `089009dc71beeb6fa0be7f0d8b965ac59cc55805`. The later documentation and packaging tools do not change the frozen engine or protocol. Do not pull other source revisions while a frozen run is in progress. The results are exploratory regression on a corpus seen during development, not a blind holdout.

Use CPython 3.12, the pinned requirements, a clean checkout and a browser installed on the same computer. In PowerShell:

```powershell
git worktree add --detach D:/icips-reproduce-089009d 089009dc71beeb6fa0be7f0d8b965ac59cc55805
cd D:/icips-reproduce-089009d
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./backend
.\.venv\Scripts\python.exe tools/release_option_b_v2.py --out results/option-b-v2 --job clean-reproduction --port 8796
```

The ordered gates check dependencies, tests, archived replay, real browser journeys, freeze, 450-run evaluation, reference/certificate audit and matched-context explanation experiment. Every new output directory is unique. Keep failed attempts. Environment-dependent latency and timeouts may differ; record the exact environment and compare all results rather than requiring byte-identical timing. A fresh virtual environment on the same computer is not independent-machine replication.

The later packaging tools are on option-b. After the measured gates finish, use the documentation-only branch tip (verify frozen file hashes; no changed measured inputs):

```powershell
.\.venv\Scripts\python.exe tools/package_option_b_conference.py --input results/option-b-v2 --job results/jobs/option-b2-release-retry-20261126 --out results/option-b-v2/conference
.\.venv\Scripts\python.exe tools/option_b_human_review.py prepare --input results/option-b-v2 --out results/option-b-v2/human-review
```

The human review rubric is in HUMAN_REVIEW_PROTOCOL.md. Never claim human scores before independently filled ratings. The generated poster and manuscript are drafts for author review; verify committee-specific format, anonymization and disclosure before sending. No deployment of hostile or unknown code is covered by this reproduction.
