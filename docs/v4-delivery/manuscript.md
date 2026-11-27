# AlgoX-Ray V4: Replayable Python Debugging Evidence and Block-Level Profiling

Hussam Eddin Alwan - Experimental revision for author review - 27 November 2026

## Abstract

AlgoX-Ray V4 is a local experimental workbench for bounded Python programming tasks. An author reviews an immutable problem package containing an input grammar, a reference and independently known controls. The workbench searches for legal counterexamples, reduces them, replays failures, records execution and presents an observed graph, variable states and reference comparison. Optional language models propose hypotheses and cases; deterministic checks validate response structure, event references and scalar snapshot facts without certifying causal prose. The continuation adds block/line wall and CPU profiling for correct and incorrect code. Software verification passed 182 tests and 19 browser journeys. A public seven-family paired benchmark yielded seven faulty witnesses, no accusations against seven corrected variants and 21 replay matches. These limited observations establish feasibility on known examples, not learning benefits or general fault-localization accuracy.

## 1. Problem and scope

A wrong output confirms a discrepancy on a particular input, but does not identify its cause. V4 packages the legal input, actual and expected output, source identity, replay and observed execution so a learner can inspect the evidence. It also makes computational cost visible at source blocks. The intended research question is whether structured observation checks improve factual support without excessive abstention on matched contexts; this release does not settle that question.

The supported release is deterministic, noninteractive Python stdin/stdout using bounded declarative integer, word, list and matrix fields. Existing solve(payload) contracts remain in the classic workbench. General mathematical constraints, arbitrary special judges, large competitive-programming inputs and other languages are not covered. Reference correctness is conditional on author review and finite controls; a second reference can expose disagreement, but shared mistakes remain possible.

## 2. Implementation and execution boundary

The local FastAPI workbench loads packages by immutable hash. Code and exact input bytes run in short-lived, pinned Docker workers: no network or host mounts, read-only root, non-root user, removed capabilities and CPU, memory, process, time and output budgets. Loopback/token checks protect local actions. These controls reduce risk; guest trace reports are not authenticated against adversarial source and public execution is disabled.

Seeded boundary/random or Hypothesis generation searches the declared domain; AI suggestions must pass the same validator. Reduction preserves legal inputs and an observed failure category, followed by three exact replay comparisons before a mismatch is presented. Oracle disagreement, infrastructure failure, timeout, instability and no-witness outcomes remain distinct. Finite successful tests are not a correctness proof.

The browser displays recorded call/line/return events, source navigation, frame identities, variable changes, matrices and independent student/reference stepping. A restricted syntactic CFG is separate from the observed graph. Supported arithmetic, indexed-value, def-use and control relationships are explicitly bounded. Coverage ranking expresses correlation; a changed execution path is not itself a bug.

## 3. Language models and claim checking

Ollama is the default local provider. Selected cloud adapters require explicit consent; there is no automatic cloud fallback. Production adapters validate returned JSON against the requested schema before business use. Model hypotheses remain unverified even when their line/event anchors exist. Scalar facts are recomputed from the recorded snapshots; this confirms the recorded value only, not causal explanation. Suggested test predictions are executed within the same input contract. Optional repairs are separate immutable candidates, manually reviewed and tested on named cases while preserving the original source.

## 4. Profiling method

The trusted bootstrap measures time between source trace callbacks with monotonic high-resolution wall and process CPU clocks. Callback work is excluded from attributed segments. Self cost excludes traced child calls; inclusive cost includes them. Source AST ranges aggregate observed segments into functions, loops and supported compound statements. Repeated headers are counted as visits, including final loop-condition checks, rather than asserted body-iteration counts. Nested and recursive inclusive costs overlap and must not be added across rows.

Collection is bounded by 100000 timing events, 384 frame/line rows, 128 blocks and 6000 AST nodes. Partial execution and collection limits are labeled explicitly. Visual snapshot truncation is independent of the aggregate profile. Profiling works on one reviewed legal input even for correct code and exports CSV and JSON. Timings remain instrumented and container-dependent: they do not predict Codeforces judge runtime, prove Big-O or support unqualified speed comparisons.

## 5. Verification and measured observations

| Check | Observation | Boundary |
|---|---|---|
| Unit/integration regression | 182 passed | Software checks, one existing Starlette warning |
| Browser acceptance | 19 journeys passed; no page errors or external requests | Synthetic authoring and repair interactions |
| Authored vertical examples | Five passed | Hamburgers, sum, count, matrix sum, reachability |
| Paired public corpus | 7/7 faulty variants found; 0/7 controls accused | Seven exposed QuixBugs families, adapted wrappers and bounded domains |
| Replay on faulty variants | 21 matches | Three per faulty witness |
| Local Qwen 7B smoke | Three schema-valid tasks; empty-evidence abstention passed | Fixed-candidate draft transport, one diagnosis, one abstention; not an accuracy study |
| Local smoke latencies | 10.594 s, 4.391 s, 0.421 s | One measured sequence, not throughput estimates |
| GPU observation | 5003 MiB peak sampled board usage | Whole board, not isolated peak model allocation |

The local model was Qwen2.5-Coder 7B Q4_K_M, context 4096, digest dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364. Runtime code is b65f596fca34c487777641ebd47e97ba5161752b. The first profiling browser attempt failed a mobile width assertion; the CSS was corrected and subsequent acceptance passed. The failed record is retained. A new checkout/virtual-environment run records dependency installation, regression, five demos and the public pilot using the same machine and pinned worker; this is reproduction, not independent replication. The exported manifest retains source revisions, SHA-256 hashes, raw synthetic records and the exact boundaries above.

## 6. Related work and interpretation

Python Tutor records and visualizes actual Python runtime state [1]. Code Hunt/Pex4Fun compares programs using generated input/output clues and describes synthesized edit hints [2]. ITAP constructs personalized paths through abstract program states [3]. CodeHelp uses structured prompting and guardrails to support students without directly revealing solutions [4]. These establish prior art for execution visualization, counterexample feedback and programming hints. The proposed contribution is an inspectable integration and evaluation question; no first-of-kind or superiority claim follows from combining those mechanisms. A page-located comparison is maintained in the repository.

## 7. Limitations and next evidence

The corpus is small, public and known; corrected/faulty pairs and repeated tests are correlated. There are no independent human ratings, genuine unseen student submissions or measured learning outcomes. A larger matched source-only/witness/trace/verification ablation and independently labeled localization study remain necessary. Schema adherence, replay and snapshot matching cannot validate free-form causal claims or the mathematical fidelity of an arbitrary package. General heap/alias slicing, semantic alignment, multi-testcase constraints and calibrated performance benchmarking remain unsupported.

The earlier V2/V3 reports remain separate. This revision does not retroactively validate any unsupported statement in an earlier submission. Author and venue approval are required before a camera-ready submission; no committee communication is represented as completed.

## References

[1] Philip J. Guo. Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education. SIGCSE 2013. DOI: 10.1145/2445196.2445368. https://pg.ucsd.edu/publications/Online-Python-Tutor-web-based-program-visualization_SIGCSE-2013.pdf

[2] Nikolai Tillmann et al. Code Hunt: Searching for Secret Code for Fun. SBST 2014. DOI: 10.1145/2593833.2593838. https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/CodeHunt20SBST202014b.pdf

[3] Kelly Rivers and Kenneth R. Koedinger. Data-Driven Hint Generation in Vast Solution Spaces: A Self-Improving Python Programming Tutor. IJAIEd 2017. DOI: 10.1007/s40593-015-0070-z. https://krivers.net/files/ijaied2015-paper.pdf

[4] Mark Liffiton et al. CodeHelp: Using Large Language Models with Guardrails for Scalable Support in Programming Classes. 2023. DOI: 10.1145/3631802.3631830. https://arxiv.org/abs/2308.06921

[5] QuixBugs paired source provenance, pinned source hashes and license: benchmarks/v4_external/manifest.json and THIRD_PARTY_NOTICES.md in the AlgoXRay repository. https://github.com/Hussam-alwan/AlgoXRay
