> Current continuation: [V4 active plan and verification status](V4_DYNAMIC_AI_IMPLEMENTATION_PLAN.md). This document preserves its original checkpoint; later measurements do not replace its historical results.

# V4 expanded experimental checkpoint — 27 November 2026

Runtime code: 58f44f39e3a415e8c38b9edbf8b4356ee984377d. Later commits add evidence and reproduction tooling. Local V4 at http://127.0.0.1:8002/v4; V3 on port 8001. Public execution remains disabled. This is not a validated general-purpose tutor.

## Verified results
- 167/167 unit and integration tests at 3dcd805; fresh Python environment and checkout at 58f44f3 also 167/167 (one existing deprecation warning).
- 14/14 browser journeys at 58f44f3, no JS errors or external browser requests; prior failed test retained locally.
- 5/5 authored vertical demos: Hamburgers, array sum, letter count, matrix sum, directed graph reachability. Five deliberate faults found, no witness against intended correct controls within the bounded runs.
- QuixBugs pilot at 5fda05e: 7/7 faulty adaptations, 0/7 corrected variants accused, 21 replay matches; 6/7 complete-trace ranking availability, not localization accuracy. Public benchmark pairs, not independent student submissions or a blind holdout.
- 11 earlier and 3 new Docker probes passed (including absence of provider credentials, read-only root and process cap). Guest traces are not authenticated; not a hostile-code security certification.
- 630 old V2 bundles revalidated, V3 health returned 200.
- Live AI pilot: Qwen and Ling accepted diagnoses, Gemini Hydrogen and Qwen equivalent repair ASTs passed named tests. Groq initially invalid fact schema; Ling repair HTTP 429; Gemini diagnosis server error; Flash unstable. Expanded Groq test found n=3 trigger missed by bounded baseline, two predictions supported. Source-only and witness ranks missed known edit line; delayed trace retry included it at rank 2 and matched two scalar facts. First trace attempt hit local cap. This is a single authored illustration, not comparative accuracy.
- Qwen 7B local digest dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364; 4096 context, Q4_K_M, all loaded bytes in GPU VRAM. Cold draft 77.89 s; no general speed claim.

## Work-package status
| WP | Implemented | Still limited or pending |
|---|---|---|
| 9 | Dedicated pinned Docker worker, resource probes, Qwen running | Independent threat assessment; guest trace authenticity |
| 10 | Ollama, Gemini, Groq, OpenRouter, explicit consent, local rate caps, local cancellation | Flash reliability, actual global quotas/discovery, optional cache/Qwen Cloud; remote cancellation not guaranteed |
| 11 | Codeforces public URL import, draft manifest/reference, matrix fields, optional distinct second reference | Arbitrary constraints, independent owner reference review, mathematical fidelity |
| 12 | stdio, legal boundary/Hypothesis cases, AI suggestions, bounded reduction/replay | General cross-field/multi-testcase constraints and multiple-valid-output semantics |
| 13 | observed graph, frames, timeline, indexed/def-use links, coverage ranking, restricted static CFG, side-by-side trace | General alias/call/heap slicing and semantic alignment |
| 14 | Real model proposals, snapshot facts and anchor checks, execution-tested predictions | General causal diagnosis and independent accuracy study |
| 15 | Review-gated patch proposal, diff, named regression tests, hash-keyed version history | Broader repair and usability evaluation |
| 16 | Paired public pilot, small AI comparison, raw evidence, reviewer packet, clean checkout tools | Independent human ratings, genuine unseen solutions, matched multi-model study, full literature review and conference author/venue approval |

## Evidence and privacy
Use docs/v4-evidence/MANIFEST.json for SHA-256 inventory of the explicitly selected synthetic/public benchmark records. See tools/export_v4_public_evidence.py. No API credentials, user code, arbitrary local logs, databases, private review keys, or user package store are exported. Earlier V2/V3 records stay separate. A clean-checkout reproduction is same-machine and same worker, not independent replication. See reproduction progress when included. The original manuscript should not be replaced automatically with speculative claims.
