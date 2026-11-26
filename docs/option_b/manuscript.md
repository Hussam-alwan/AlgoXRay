# AlgoX-Ray: Counterexample-Driven Visual Debugging and Evidence-Grounded Hints for Algorithmic Problem Solving
**Measured Option B v1 manuscript — author review required; not camera-ready.**

## Abstract
We propose a local trusted-code workbench that links bounded legal counterexample discovery with replay, input reduction, recorded Python execution and evidence-grounded educational feedback. Three declared contracts cover directed shortest paths, binary-search membership and maximum nonempty contiguous subarray. The design records source identity, frame and event identifiers, and narrow diagnostic predicates; unsupported specific claims are removed rather than asserted. A paired technical evaluation of the frozen v1 source on 30 program files and five seeds found 225/225 faulty runs with witnesses and 0/225 control accusations. Of 75 traced/reduced faulty runs, 59 reduced strictly and 20 received a specific source observation. This finite, partly assistant-authored corpus supports feasibility, not general diagnostic accuracy. The later v2 source is not yet measured.

## 1. Research question and related work
Can checking diagnostic observations against a reproducible witness and recorded execution reduce unsupported claims while retaining useful coverage? Execution visualization, why/why-not debugging, data-driven hints, LLM programming assistance and property-based reduction are established lines of work. The proposed engineering contribution is their bounded integration with an inspectable evidence contract and explicit abstention, not a new shrinking algorithm or a general root-cause detector. See ../OPTION_B_PRIOR_WORK.md for the primary-source comparison and unresolved literature review.

## 2. Method
Each problem defines legal inputs and accepted outputs. Directed graphs contain 2–8 vertices and positive integer weights; Bellman–Ford is checked against Floyd–Warshall. Binary search accepts any matching index on sorted arrays of up to 32 entries. Maximum subarray accepts a nonempty array of up to 24 bounded integers; exhaustive segment enumeration is checked against Kadane's algorithm. A reference disagreement is an infrastructure result, not an accusation.

Candidates execute in a fresh namespace within a child interpreter. Failure categories distinguish wrong answer, contract violation, exception and timeout. Repeated matching outcomes are required before accepting a candidate, and again for the final witness. Hypothesis and greedy structural reduction are best-effort procedures that preserve a failure signature, not globally minimality guarantees. The recorded trace must agree with the untraced failure; bounded snapshots can be incomplete.

The evidence bundle links source SHA-256, input, observed and expected outputs, replay counts, frame IDs, event IDs and rule-specific observations. The verifier checks links and narrow arithmetic/runtime predicates. Unsupported observations and their dependent hints are dropped. Ranked source lines reflect recorded observations, not causal probabilities. No external model is required; optional claim selection cannot introduce new claims.

## 3. Evaluation design
The prospective manifest combines 12 historical corpus files and 18 assistant-authored implementations, with distinct source hashes verified at freeze time. The new files require external label review and are not independently authored student submissions. Five seeds and three paired variants yield 450 planned runs. Random and Hypothesis discovery arms disable shrinking and tracing; the full arm enables both. The runner records all outcomes and raw bundles, plus a review CSV for independent annotations. Analyze by program family as well as by run. Report detection and false accusations, coverage, abstention, reduction, runtime, replay, and reviewer-supported factuality separately.

## 4. Results
The following results are from Option B v1 at 3362119, measured on 26 November 2026, and must not be attributed to v2.

| Variant | Witness on faulty runs | Accusations on controls | Median successful discovery (ms) | Median total (ms) |
|---|---:|---:|---:|---:|
| Random | 75/75 | 0/75 | 58.32 | 73.29 |
| Hypothesis | 75/75 | 0/75 | 73.59 | 126.81 |
| Full | 75/75 | 0/75 | 72.63 | 154.29 |

The full variant strictly reduced 59/75 witnesses and produced 20/75 specific source observations (all in binary search). Recorded replay matches were 675/675 across the three variants; the independent arithmetic/reference audit checked 210 certificates without errors. No rejected candidate claim occurred in this natural set; the effect of filtering on factuality is unmeasured. Random was faster on the sampled discovery runs. The 225 failing runs comprise 210 wrong answers, 10 exceptions and five timeouts. All 106 tests and 18 browser journeys passed on v1. Full evidence remains in results/option-b-new and results/jobs; see MEASURED_V1.md. No independent human annotation or new v2 measurements are claimed.

## 5. Demonstration
Use the maximum-subarray input [-5,-2,-7]. A solution that permits an empty segment returns zero, whereas a legal nonempty segment has optimum -2. This is a designed example with analytically known expected behavior, not an executed Option B result. The UI is intended to show the witness, highlighted segment, trace, ranked supported observations, and exported evidence; the v1 browser acceptance recorded this workflow; v2 requires fresh validation.

## 6. Limitations
Trusted local execution is not a security sandbox. The supported problems are bounded, and source-specific diagnosis is incomplete. Repeated seeds are not independent participants. The corpus is partly assistant-authored, not a blind student sample. No general accuracy, minimality, educational gain, first-of-its-kind novelty or superiority claim is established. V1 runtime and browser checks passed; v2 verification, broader full-paper literature review, and independent annotation remain outstanding.

## 7. Reproducibility
Use the option-b branch at https://github.com/Hussam-alwan/AlgoXRay/tree/option-b, locked dependencies and benchmarks/option_b/evaluate.py. Preserve the frozen manifest, raw runs and reviewer records. The v1 numbers are measured. Reconcile the final venue template and author disclosure; do not replace the v1 table with v2 until a separate run and audit complete.
