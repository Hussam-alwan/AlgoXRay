# Option B — WP1 research claims register (initial draft)

Status: provisional. This is a repository evidence inventory, not a new
literature review, independent validation, or new experiment.

## Historical claims

Keep the two generations of results separate. The existing manuscript draft
describes the earlier 320-run protocol; the later 0.2.0 release has its own
freeze, raw files, protocol, and summary. Neither is evidence for changes
made on option-b.

| ID | Claim allowed only with stated historical scope | Evidence | Limitation |
|---|---|---|---|
| H01 | 480 discovery runs across 12 program files (6 faulty, 6 correct), 20 seeds, 2 strategies | results/core-release/summary.json; protocol.json; corpus.json | Repeated runs are not independent programs or learners |
| H02 | 240/240 faulty runs had witnesses; 0/240 control runs were accused | results/core-release/summary.json; runs.csv | Bounded Dijkstra and binary search corpus only; failures include exceptions and timeouts |
| H03 | 72/72 audit replay attempts matched; 19/24 witnesses reduced in size | results/core-release/summary.json | Audit subset; no universal determinism or minimality proof |
| H04 | 6/24 audited witnesses had specific source observations; 18/24 abstained | results/core-release/summary.json; claims.csv | Two exception locations and four returned-index observations, not root-cause accuracy |
| H05 | 20/20 recorded certificates verified, 30 emitted claim instances passed internal checks | results/core-release/summary.json; claims.csv | Internal validation, not independent human accuracy evaluation |
| H06 | 21 complete and 3 truncated traces among 24 audited witnesses | results/core-release/summary.json | Structural trace validation is not semantic completeness |
| H07 | Saved clean-check report says all eight checks passed | results/core-checks/clean.json | Historical Windows environment only; WP0 must produce fresh evidence |

Historical codebase SHA-256: 1fe1dda00536a3317ff6f4d8a77c1f2c1f33357ea0242cfb99e0b84bb3cd8c78.
See results/core-release/freeze.json for byte-level identities.
Do not update this hash or silently combine the old and new results.

## Candidate new contribution — not established novelty

Typed diagnostic claims tied to source identity, a reproducible legal witness,
execution events and claim-specific validation, with explicit abstention.
The research question is whether such verification reduces unsupported claims
without making coverage impractically low on held-out implementation families.

| ID | Question | Comparator and outcome | Gate / evidence needed |
|---|---|---|---|
| RQ1 | Stable legal witness discovery | Random vs Hypothesis, equal declared budgets; detection, false accusations, failure kind, runtime | Frozen independent evaluation corpus; raw runs and grouped analysis |
| RQ2 | Evidence-grounded explanation | Same explainer with code only, with witness, with witness + trace; before vs after verifier | Typed claim rubric; coverage, contradiction, unsupported claims, abstention; independent human review when available |
| RQ3 | Problem extensibility | Add one materially different package after core freeze | Record all changed files and integration effort; independent solutions through ordinary user entry; no hidden engine modifications |
| RQ4 | Educational benefit | Appropriate learner study | Not planned as a result until actual participant study is approved and conducted |

RQ2 can initially use deterministic explainers; the optional external AI
adapter is not a prerequisite for implementation. If a provider is later
approved, record model, prompt, version, settings, cost, failures and data policy.
No external provider is enabled by this work.

## Prior-work review queue

Repository docs/RELATED_WORK.md already identifies Python Tutor, Code Hunt /
Pex4Fun, ITAP, CodeHelp, CodeAid and Hypothesis. The Option B plan additionally
requires close review of Whyline, shrinking/minimization, and relevant
AAAI 2025 and MENTOR 2026 work. Their exact papers, comparisons and novelty
implications must be verified from primary sources; do not mark a feature
absent because a summary omits it.

For each paper record citation, exact page/section, task, language, oracle,
witness generation, reduction, trace, hints, claim verification, abstention,
dataset, baselines, limitations, and a testable distinction. Unknown stays
unknown. If prior art matches the proposed contribution, narrow the claim.

## Claims currently forbidden

- General correctness, guaranteed root-cause localization, universal language
  or algorithm support, first-of-its-kind novelty, improved learning outcomes,
  sandbox safety, and AI superiority.
- Treating all 480 runs as independent programs, or 6 specific observations
  as verified root causes.
- Reporting unexecuted Option B tests or presenting draft conference material
  as camera-ready.

WP1 gate G1 remains open: complete primary-paper review and freeze evaluation
design before claiming novelty or comparative performance.
