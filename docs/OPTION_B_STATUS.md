# Option B implementation status

The measured local research prototype is at [089009d](https://github.com/Hussam-alwan/AlgoXRay/commit/089009dc71beeb6fa0be7f0d8b965ac59cc55805). Subsequent documentation and packaging changes do not alter the measured engine or UI. Main is unchanged.

| Work package | Verified output | Remaining gate / limitation |
|---|---|---|
| WP0 baseline | 126 tests, dependency pins, catalog hashes and archived replay passed on accepted v2 retry | Earlier intermittent test failure preserved; same-machine clean replication passed |
| WP1 research protocol | Scoped prior-work matrix, claims register, paired experiments and matched-context ablation measured | Wider literature review and independent human labels; no priority claim |
| WP2 core contracts | Output codec, worker states, registry, cancellation, fresh-process option and evidence validation tested | No hostile-code isolation |
| WP3 problem packages | Three live contracts, local package review, capability-driven rendering and generic fallback | Author review for new packages; no automatic untrusted package loading |
| WP4 trace and localization | Frame/event identity, verified observations, spectrum ranking, arithmetic link subset | Original V2: 75/75 spectrum ranks, 0/75 arithmetic links; external pilot: 25/30 spectrum ranks, 15/30 arithmetic links; independent Top-k labels needed |
| WP5 explanation | Deterministic prose integrity and abstention, 75/75 tampered prose and 40/40 missing-event probes rejected | No natural rejection in sample; human factuality pending; no external AI provider activated |
| WP6 UI | 20 browser journeys, cancellation, author review, editing/replay, mobile and export passed | Foundry unavailable, implemented directly; human design review pending |
| WP7 evaluation | 450/450 v2 executions, 225/225 faulty witnesses, 0/225 controls accused, audit and ablation passed | Fresh-environment repeat passed; additional external-source pilot: 180 runs, 90/90 faulty trials found, 0/90 controls accused. Larger independent holdout and human review pending |
| WP8 conference | Measured manuscript, refined one-page PDF poster, reviewer response, demo, reproduction reports and integrity-checked local ZIP archives generated | Final committee format/anonymization, author approval and submission outstanding |

See [V2 measured results](option_b/MEASURED_V2.md), [V1 measured results](option_b/MEASURED_V1.md), [reproduction](option_b/REPRODUCE_V2.md) and [independent review protocol](option_b/HUMAN_REVIEW_PROTOCOL.md). Historical artifacts remain unchanged. Raw logs and generated conference materials are local and not submitted to the committee.

External pilot report: [EXTERNAL_PILOT_RESULTS.md](option_b/EXTERNAL_PILOT_RESULTS.md). The pilot is a separate measured dataset; historical and mutant faults are reported separately.
