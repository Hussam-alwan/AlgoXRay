# Package author review
Install a reviewed Python ProblemSpec in source, with legal domain, oracle, checker, generator, reducer and visualization. The local author screen and CLI review an installed package against independently supplied control answers and bounded random generator/reducer checks. They return a control-manifest hash and failures; neither registers arbitrary code nor automatically approves a contract. Hypothesis strategy, external provenance and author approval require separate review.
CLI: python -m algoxray.cli review-package --problem max_subarray_v1 --controls controls.json
Controls JSON example: [{"case":{"array":[-5,-2]},"expected":-2}].
