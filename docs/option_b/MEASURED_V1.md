# Option B v1 — measured and audited results
Measured source revision: 33621199e8c3d85ccd149b0d43b3f057c5747187. The local run completed on 26 November 2026 with exit code 0; raw files under results/option-b-new. The later read-only audit script completed with no audit errors. This report describes v1 only, not the changed engine after f1c33e6 or later.

30 program files (15 labelled faulty, 15 controls); five seeds; three paired variants. 18 of the files were assistant-authored, and the labels are pending external review. The 450 runs are not 450 independent programs or students.

| Variant | Faulty runs with witness | Correct controls accused | Median discovery among 75 successful runs (ms) | Median total across 150 runs (ms) |
|---|---:|---:|---:|---:|
| Random (no trace/shrink) | 75/75 | 0/75 | 58.32 | 73.29 |
| Hypothesis (no trace/shrink) | 75/75 | 0/75 | 73.59 | 126.81 |
| Full (Hypothesis with trace/shrink) | 75/75 | 0/75 | 72.63 | 154.29 |
| Total | 225/225 | 0/225 | — | — |

Each variant found at least one witness for 15/15 labelled faulty programs and accused 0/15 labelled controls. No inference of a perfect population rate; a degenerate bootstrap in this sample is not evidence of certainty.

| Problem | Full variant witnesses | Strict reductions | Specific source observations |
|---|---:|---:|---:|
| Binary Search | 30 | 15 | 20 |
| Dijkstra | 30 | 29 | 0 |
| Maximum Subarray | 15 | 15 | 0 |
| Total | 75 | 59 (78.7%) | 20 (26.7%) |

Across variants: 210 wrong answers, 10 exceptions, 5 timeouts; 675/675 recorded matching replays; 210 certificates passed the independent reference/arithmetic audit; no audit errors. No candidate claim was rejected in this natural run set; the data therefore do not demonstrate a verifier-induced factuality improvement. The original v1 test suite reported 106/106; 18 browser journeys, no page errors/external requests. Independent human annotation and clean-machine replication are still outstanding.

Random was faster on this finite corpus; equal detection does not demonstrate Hypothesis superiority. No claims of general correctness, causal localization, learning benefit, or independent student-code evaluation.
