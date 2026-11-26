# AlgoX-Ray measured technical evaluation

Codebase SHA256: `cff4e82bd46badc850eca72cf08fc90a9a5c1c70e0561d00ec2d9ee64c9dba9c`

320 actual runs; 8 programs; 20 seeds per strategy.

| Problem | Strategy | Buggy witnesses | False control accusations | Median discovered time (ms) |
|---|---|---|---|---|
| binary_search_v1 | hypothesis | 60/60 | 0/20 | 85.90 |
| binary_search_v1 | random | 60/60 | 0/20 | 81.73 |
| dijkstra_v1 | hypothesis | 60/60 | 0/20 | 105.48 |
| dijkstra_v1 | random | 60/60 | 0/20 | 77.41 |

Timings include verification before the first confirmed witness. Medians exclude censored trials, which are counted separately in summary.json.
No shrinking or tracing in this comparison. Random and Hypothesis use the same legal domain and budgets, but have different input distributions.
Repeated seeds are not independent programs. All sources were reviewed; development/evaluation splits are bookkeeping, not a blinded holdout claim.
These data do not establish educational benefit, general diagnosis accuracy, or a new test-generation algorithm.
