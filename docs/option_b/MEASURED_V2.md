# Option B v2 — measured release evidence

Frozen engine and UI: [089009dc71beeb6fa0be7f0d8b965ac59cc55805](https://github.com/Hussam-alwan/AlgoXRay/commit/089009dc71beeb6fa0be7f0d8b965ac59cc55805). Evaluation completed on 26 November 2026. All six accepted release stages passed: baseline, browser, freeze, evaluation, audit and matched-context explanations. An earlier full gate attempt had one intermittent contract test failure; it was retained, the isolated suite passed, and the full retry passed 126/126 tests. No assertion was relaxed for the retry.

## Technical measurements

30 distinct program files (15 labelled faulty, 15 controls), five seeds and three paired variants, 450 executions. Four files are adapted QuixBugs buggy/correct sources; the other 26 are assistant-authored evaluation programs (eight historical and 18 additional). Labels and claims are pending independent human review. V2 reuses the v1 corpus after development exposure, not a new held-out sample.

| Variant | Faulty runs with witness | Correct control accusations | Median discovery among 75 successful runs (ms) | Median total across 150 runs (ms) |
|---|---:|---:|---:|---:|
| Random | 75/75 | 0/75 | 343.47 | 426.52 |
| Hypothesis | 75/75 | 0/75 | 393.74 | 707.99 |
| Full | 75/75 | 0/75 | 387.36 | 865.06 |
| Total | 225/225 | 0/225 | — | — |

Every arm found a witness for 15/15 labelled faulty programs and accused 0/15 labelled controls. The audit recomputed reference outcomes and certificates: 675/675 recorded replay matches, 210 certificates, no audit errors; 210 wrong answers, 10 exceptions and five timeouts. These are repeated runs, not independent participants. The median total latency is higher than v1 on this run; no controlled cross-revision speed improvement is established. Random had the lowest median discovery time in this v2 sample.

| Problem | Full witnesses | Specific observations | Spectrum ranks available | Arithmetic links available |
|---|---:|---:|---:|---:|
| Binary search | 30 | 20 | 30 | 0 |
| Dijkstra | 30 | 15 | 30 | 0 |
| Maximum subarray | 15 | 5 | 15 | 0 |
| Total | 75 | 40 | 75 | 0 |

59/75 full witnesses were strictly reduced. Specific observation coverage rose from 20/75 (v1) to 40/75 (v2); this includes 20 mathematical return symptoms and does not establish a doubling of causal accuracy. All 75 full witnesses had complete traces and a spectrum rank. No restricted arithmetic read/write link occurred in the measured corpus despite unit-level verification. Do not describe it as a measured coverage benefit. Top-k location accuracy is unmeasured without independently labelled fault locations.

## Matched-context deterministic explanation ablation

| Context | Witnesses | Candidate claims | Published claims | Rejected claims | Specific observation coverage |
|---|---:|---:|---:|---:|---:|
| Source only | 75 | 0 | 0 | 0 | 0/75 |
| Source + witness | 75 | 75 | 75 | 0 | 0/75 |
| Source + witness + trace | 75 | 115 | 115 | 0 | 40/75 |

Source-only abstention is intentional. No natural candidate was rejected, so this experiment does not establish a verifier-induced factuality gain. Synthetic probes rejected 75/75 tampered prose attempts and 40/40 claims with nonexistent event identifiers. This is an integrity test, not a human accuracy result. The same deterministic explainer is used in all arms; no LLM comparison is claimed. 115 claim items and 75 localization items are prepared for independent human reviewers; no ratings collected yet.

## Engineering and handoff

126 tests passed (one Starlette deprecation warning); 20 browser journeys passed with no page errors or external requests. Conference packaging completed; 23/23 package hashes matched and the generated poster is one PDF page. Author/committee review still required. The separate clean-checkout and fresh-environment replication finished on the same machine; all six stages passed. It repeated 450 runs, 225 faulty witnesses, zero control accusations, 675/675 replays, 210 certificates, 59 strict reductions and 40 specific observations, with identical diagnostic availability counts and synthetic negative control counts. The audit had no errors. The median total latencies (random, Hypothesis, full) were 94.35, 156.08 and 180.22 ms respectively; the original run was slower. These timing differences are not controlled performance comparisons.

The two freezes have identical commit, corpus, policy and all frozen file hashes except the untracked editable-install inventory `backend/src/algoxray.egg-info/SOURCES.txt`. Original inventory SHA-256: `041bf2f300c656424ac61485c4698a3c18cf53ee298bfbbaebf398445f259d9d`; regenerated inventory SHA-256: `cf8292e462af35639553dc30479159791ea812a86210df25604aeaf9e70cdfdb`. This inventory was stale in the original environment; no tracked source file differed. Both full freeze files and the explicit difference report are included in the reviewed conference package. The freeze implementation itself has not been altered retroactively. Same-machine fresh-environment reproducibility is not independent-machine replication.

Local evidence: `results/option-b-v2` (450 raw compressed bundles, freeze, runs, summary, audit and explanation review); `results/jobs/option-b2-release-retry-20261126` (gate logs, browser screenshots and exported evidence); `results/option-b-v2/conference` (measured manuscript, poster, response, demo and manifest). Review mapping keys stay separate from reviewer packets. The refined author draft is under `results/option-b-v2/conference-reviewed`; delivery archives are under `results/option-b-v2/delivery-reviewed`. The fresh repeat raw evidence is under `results/jobs/clean-reproduction-089009d/results/option-b-v2`. No hostile-code sandbox, user-study benefit, general correctness or root-cause guarantee is established.
