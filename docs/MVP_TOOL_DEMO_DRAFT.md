# Linking Replayed Counterexamples to Python Execution Evidence with AlgoXRay

Draft for author review. FSE 2027 Tool Demonstrations is the candidate track.

## Abstract

Contest programmers can reproduce a wrong answer and still struggle to locate the relevant input and the behavior that produced it. AlgoXRay takes a reviewed input contract, a reviewed reference or checker, and a complete Python program. It searches legal inputs, verifies a failure by replay, and reduces the input within a declared budget. The interface links the resulting witness to source spans, observed events, frame-local values, and candidate fault locations. Users can verify a revised program against the original and reduced witnesses and additional cases. We describe an isolated local prototype and three reproducible demonstration journeys. Validation in this draft is limited to engineered fixtures and runtime checks.

## Workflow

An author reviews the problem description and input grammar and approves a comparison strategy. AlgoXRay records whether the reference and student runs can be judged. Replay detects unstable witnesses. The reducer preserves legality and uses a compatible failure signature within a bounded search. The report retains the original and reduced inputs and distinguishes output effects, ranked locations, and optional hypotheses.

The visualization follows recorded frames and line events. Source highlighting uses the exact source version and UTF‑8 offsets. A separate execution mode collects wall and CPU measurements without trace callbacks. When a reference fails or disagrees, users can still inspect a run on their own input. The optional local model receives scoped evidence and its structured claims are checked against the recorded data. A local model can also abstain.

## Demonstration and validation

The candidate code is pinned at `f6617e9`. Each authored workflow ran twice from a clean Windows setup with a pinned Docker worker.

1. Prepare a new repeated-case description, approve its package, reduce a failing input from two test cases to one, inspect its trace, and verify a candidate repair against both witnesses and its named checks.
2. Compare two correct implementations over five input sizes and five repetitions per size, and inspect profiling on a separate execution of the same input. Every measured output matched the reference. The fit abstained when variability exceeded its documented threshold.
3. Observe refusal to judge when references disagree, then inspect the student program on a manual input. The demonstration also covers missing trace events and a simulated provider outage.

The code passed 307 Backend tests on Windows and Linux. The browser cancellation check observed the running Docker configuration and removal of the dedicated worker. Automated validation uses development cases. Comparative data from independently reviewed problems and usability observations remain planned.

## Artifact and contribution to examine

The proposed contribution is the workflow that keeps the legal counterexample, replay evidence, source and frame navigation, and named repair checks linked to the same versioned result. Delta debugging, spectrum-based ranking, and output-centered debugging tools provide relevant comparison points. The independent study protocol separates candidate reduction, localization ranking, and the evidence behind a model's diagnostic claims. [Related work and evaluation questions](MVP_RELATED_WORK_AR.md)

The repository provides the [local demonstration runbook](MVP_DEMO_RUNBOOK_AR.md) and [verified demonstration evidence](mvp-evidence/demo-release-20261128.json). Author approval, publication history, a submitted-format PDF, and an actual screencast remain pending. [Official track requirements](https://conf.researchr.org/track/fse-2027/fse-2027-demonstrations)
