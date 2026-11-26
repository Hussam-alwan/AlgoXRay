# Prospective evaluation protocol

Do not treat historical release measurements as Option B results.

## Design
Freeze source hashes, fixture labels, dependency versions, seeds, per-case and total budgets before collecting results. Separate development fixtures from held-out fixtures. Compare random search, property-based search, and reduction-disabled runs under identical budgets. Record every run including inconclusive, timeout, invalid submission and infrastructure failures.

## Metrics
Report detection by labeled faulty program, false accusations on correct programs, reproducibility of witnesses, reduction size before/after, runtime and solver calls. Report diagnosis coverage separately from correctness of source-specific observations. Have independent reviewers label observations without seeing the method. Report counts and denominators, not only percentages. Group uncertainty estimates by program rather than treating repeated seeds as independent programs.

## Release gate
Preserve raw evidence and the frozen manifest. Do not fill result tables until execution is authorized. A witness proves a concrete contract violation, not universal correctness or a causal faulty line.
