# Prospective evaluation protocol

Do not treat historical release measurements as Option B results.

## Design
Freeze source hashes, fixture labels, dependency versions, seeds, per-case and total budgets before collecting results. Separate development fixtures from held-out fixtures. Compare random search, property-based search, and reduction-disabled runs under identical budgets. Record every run including inconclusive, timeout, invalid submission and infrastructure failures.

## Metrics
Report detection by labeled faulty program, false accusations on correct programs, reproducibility of witnesses, reduction size before/after, runtime and solver calls. Report diagnosis coverage separately from correctness of source-specific observations. Have independent reviewers label observations without seeing the method. Report counts and denominators, not only percentages. Group uncertainty estimates by program rather than treating repeated seeds as independent programs.

## Release gate
Preserve raw evidence and the frozen manifest. Do not fill result tables until execution is authorized. A witness proves a concrete contract violation, not universal correctness or a causal faulty line.

## New runner
The prospective runner combines the 12 historical corpus programs and 18 new assistant-authored program files (30 distinct implementations if the freeze succeeds). These are not 30 independent human participants or independently sourced student solutions. External review of new labels and further independent recruitment remain pending.
After authorization, use a fresh directory:
```sh
python benchmarks/option_b/evaluate.py freeze --out results/option-b-new
python benchmarks/option_b/evaluate.py run --out results/option-b-new
```
The three paired variants use five declared seeds, giving 450 planned runs. No runs have been executed. The review CSV requires actual independent reviewer judgments.
