# External-source post-freeze pilot — measured 26 November 2026

Engine revision: `089009dc71beeb6fa0be7f0d8b965ac59cc55805`.
Frozen pilot commit: `31bfd27ce8fe41cd7c95ed2b6dcbe0732a3eee83`.
No change to the measured V2 engine, contracts, fixtures, UI or original protocol. The run checked the tracked implementation against that revision before freezing. This is a new external-source pilot, not an independent human evaluation or a full blind holdout.

## Provenance and label preflight
Twelve adapted files in six pairs from TheAlgorithms/Python, MIT licensed, with pinned upstream revisions, archived source, explicit wrappers and mutation records under benchmarks/external_v2. Three faulty files are historical upstream implementations; three are deliberately mutated upstream implementations. Six are intended-correct upstream controls. The recursive and exponential search families share ancestry; do not interpret the six pairs as independent authors or six statistically independent defect classes. Historical licenses from 2016 and 2019 are reproduced in external-licenses; the modern MIT notice is in the pilot directory.

A separate bounded oracle preflight checked 4,624 inputs on the six intended-correct controls without observing a mismatch, and confirmed one predeclared failing input for each faulty file. This does not prove all controls correct, and the failing inputs were not passed to discovery.

## Discovery and evidence
Five seeds and three variants per file: 180 completed executions. Each variant detected all 30 faulty trials (6/6 faulty files) and accused none of its 30 intended-correct trials (0/6 controls). Across arms: 45/45 historical-fault trials detected, 45/45 synthetic-mutant trials detected, and 0/90 accusations on controls. These are repeated trials on a small correlated corpus. There were 45 exceptions and 45 wrong answers; no audit errors. All 270 recorded replay attempts matched; 45 certificates were audited. Fifteen of 30 full-arm witnesses strictly reduced.

| Contract | Full witnesses | Specific observation | Spectrum rank available | Arithmetic links available |
|---|---:|---:|---:|---:|
| Sorted membership | 10 | 10 | 10 | 0 |
| Shortest path | 10 | 5 | 5 | 5 |
| Maximum subarray | 10 | 0 | 10 | 10 |
| Total | 30 | 15 | 25 | 15 |

Specific observation coverage: 15/30 (50%). No new math-return invariant triggered. Arithmetic links appeared on 15/30 witnesses, unlike the original V2 corpus (0/75); this measures availability, not causal localization accuracy. The historical graph implementation produced a too-small distance from its ignored graph argument; the current narrow diagnostics abstained on it. Maximum-subarray mutants also received no specific observation. These are observed limitations, not reasons to change this frozen evaluation.

## Explanation evidence and human review
Source-only: 0 candidate claims. Witness-only: 30 candidate and published claims. Witness+trace: 45 candidate and published claims, including 15 specific observations. No natural candidate rejected, so no claim of natural factuality improvement. Designed integrity probes rejected 30/30 altered prose cases and 15/15 nonexistent-event claims. The automatically generated review packet contains 45 claim items and 30 localization items. No independent reviewer ratings exist.

## Reproduction and limits
Local data: results/external-v2-pilot (freeze, preflight, 180 raw bundles, CSV, summary, audit, explanation and review packets). Gate logs: results/jobs/external-v2-pilot. Keep the pilot separate from the original V2 study. Do not pool correlated seeds into independent programs, or relabel mutants as real student submissions. The proposed 30 genuinely external solutions and an independent human-labelled holdout remain incomplete. Do not tune V2 using these results and then describe a repeat as held-out performance.
