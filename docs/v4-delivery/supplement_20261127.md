# Measured software and local ablation supplement — 27 November 2026

Runtime: `1aee128bfaf33313fb01e9dcf8d5ffd70859e13e`. Context-only experiment: `2d6d284`. This supplements the historical 182-test/19-browser manuscript and PDFs; it is not a submitted camera-ready revision.

## Software change

The bounded Python workbench now has an opt-in model-versioned RAM cache, configured consent-gated Qwen Cloud adapter, exact quotation/literal constraint review, mutually exclusive field schemas, bounded reference audits, zero-length list/word support and bounded unordered/floating output comparisons. The graph adds frame/event filters, panning, two layouts, previous same-frame snapshots and explicit observed loop counts. Diagnosis receives a bounded hashed context with omission flags; a restricted AST evaluator recomputes primitive if/while conditions from recorded scalar snapshots. Neither ID membership nor a matching condition verifies causal prose.

Verification passed 223 tests, 25 normal and 5 negative browser checks, five authored demos and a fresh seven-step same-machine clean-checkout reproduction. All 11 plus 3 local worker probes passed. The browser negative suite uses an explicitly mocked provider outage in its test-only process; no production outage hook exists. Qwen Cloud transport/configuration is covered with mocked requests, not a live cloud call.

A fresh deterministic public paired pilot observed faulty behavior in 7/7 adaptations, accused 0/7 corrected controls and recorded 21 replay matches. These are exposed public QuixBugs adaptations, with wrappers and bounded domains. They are not unseen student submissions.

## Matched local context experiment

Seven public families: gcd, get_factors, sieve, kth, quicksort, longest_common_subsequence and possible_change. Each arm receives the same task/source and schema, instruction, Qwen2.5-Coder 7B model digest, context 4096, temperature 0 and output budget 1024. One call per family/arm is made in fixed source-only, witness, trace order, without caching. Verification reuses the exact trace response and makes no inference call.

Source-only receives the approved bounded manifest, statement and source; witness adds the previously frozen failing input/output/status; trace adds selected recorded scalar snapshots and trace completeness. No known edit-line label is supplied to the model. The experiment conditions on existing published witnesses; it does not measure new discovery. The fresh deterministic pilot is separate.

| Arm | Requests completed / attempted | Known edit-line Top1 | Top3 | Top5 | Total inference seconds |
|---|---:|---:|---:|---:|---:|
| Source only | 7/7 | 1/7 | 3/7 | 5/7 | 53.608 |
| + Witness | 7/7 | 1/7 | 3/7 | 4/7 | 44.627 |
| + Trace | 7/7 | 3/7 | 6/7 | 6/7 | 49.936 |
| Same trace response + verifier | No new requests | 3/7 | 6/7 | 6/7 | Not measured |

All 21 calls completed schema-valid in this run, with no abstention. Times include each model invocation's request wall time and the initial model load where applicable; fixed order and warm-up can confound timing differences. In raw verification rows, `seconds: 0` is a no-additional-inference sentinel, not measured verifier wall time.

In the trace arm, 16 of 25 scalar value claims matched recorded snapshots and 9 were unsupported. In source-only and witness arms, all 39 value claims and 15 branch claims were unsupported because no trace events were supplied. Trace produced no branch claims, so this run does not estimate the live branch verifier's accuracy. Unit tests cover true, false, unknown and call-containing branch claims.

This small experiment suggests an association between supplying trace context and edit-line agreement on this exposed set. It establishes neither general localization improvement nor independent causal accuracy. Verifier membership filtering did not change Top-k in this run. A candidate at an observed line remains a hypothesis. Program traces are guest-supplied observational evidence, not authenticated adversarial logs.

V3 uses different fixed contracts; no V3 row is fabricated for unsupported stdio packages. A proper common-contract V3 comparison, repeated/randomized runs, unseen licensed programs, independent edit/root-cause labels and human factuality ratings remain pending.

## Provenance and reproducibility

- [Source/model/budget freeze and all raw ablation responses](../v4-evidence/completion-20261127/ablation/freeze.json).
- [Ablation summary](../v4-evidence/completion-20261127/ablation/summary.json).
- [Fresh deterministic pilot](../v4-evidence/completion-20261127/external/summary.json).
- [Resolved checkout and verification inventory](../v4-evidence/completion-20261127/SOURCE_FREEZE.json).
- [Exact-byte public manifest](../v4-evidence/completion-20261127/MANIFEST.json).

Reproduce deterministic checks with a fresh destination and exact runtime commit:

```powershell
.\.venv\Scripts\python.exe tools/reproduce_v4.py --checkout D:/algoxray-repro-new --out results/repro-new --commit 1aee128bfaf33313fb01e9dcf8d5ffd70859e13e
.\.venv\Scripts\python.exe tools/verify_v4_browser.py --out results/browser-new --port 8798
.\.venv\Scripts\python.exe tools/verify_v4_failure_browser.py --out results/browser-failures-new --port 8805
.\.venv\Scripts\python.exe tools/evaluate_v4_context_ablation.py --out results/ablation-new
```

The model experiment requires the recorded local Ollama model; deterministic reproduction makes no live inference. The worker image/dependencies must be prepared as documented in the project README. The evidence exporter uses a fixed public/synthetic allowlist and retains two failed draft attempts plus the initial negative-suite fixture failure. It excludes private package/source stores, credentials and reviewer keys.

Author approval, venue formatting, independent security review and committee submission are outside this measured supplement and have not been simulated.
