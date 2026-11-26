# Option B implementation status

This is a forward development log, separate from historical release results.

| Work package | State | Next gate |
|---|---|---|
| WP0 baseline | Rider: Python 3.12.10; 105 of 106 tests passed before registry test fix | Pull fix, rerun complete suite, inventory, replay and isolated browser journey |
| WP1 research protocol | Initial primary-source abstract matrix and claims register committed | Full-paper review and additional recent work |
| WP2 core contracts | Bounded codec, protocol validation, trace snapshot limits and replay/trace error handling; untested | G0 and runtime verification |
| WP3 problem packages | Third problem package (maximum subarray) integrated through API, generation, oracle, reduction, certificate, fixtures and UI; untested | Engine now dispatches through ProblemSpec registry; evaluate new problem and further packages |
| WP4 trace and localization | Frame identity and ranking exposed in evidence and UI; untested | Semantic checks and runtime verification |
| WP5 explanation | Structural and rule-predicate verification, abstention and constrained claim selection integrated; untested | Independent human evaluation; external provider optional |
| WP6 UI | Ranked observations, frame identity, dynamic problem tabs and separate prospective results integrated; untested | Isolated acceptance script tools/verify_option_b_browser.py added; execution pending |
| WP7 evaluation | Prospective protocol drafted | Prospective runner, 30-file corpus and 450-run protocol prepared; not executed; external label review required |
| WP8 conference | Separate Option B manuscript, poster HTML, demo script and reviewer response drafted | Actual review text, measured results, final template and author approval |

Branch: option-b. Main remains unchanged. Historical benchmark evidence is not
regenerated or rewritten. Build, run and runtime verification are deferred
until requested by the owner and performed through Rider.
