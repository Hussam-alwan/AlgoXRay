# Related work and attribution

This is a scoped comparison for the current prototype, not an exhaustive novelty search. A feature is not labeled absent from a prior system merely because a summary did not mention it.

| Work | Verified relevance | Consequence for AlgoX-Ray |
|---|---|---|
| Python Tutor | Step-by-step execution visualization and runtime state | Execution visualization alone is not a new contribution |
| Code Hunt / Pex4Fun | Automated input/output clues using dynamic symbolic execution and comparison with hidden reference code | Counterexample-based feedback has prior art |
| ITAP | Data-driven personalized next-step hints through program-state abstraction and paths toward correct solutions | Automated programming hints have prior art |
| CodeHelp | LLM assistance with guardrails intended to avoid directly revealing solution code | Withholding the final answer alone is not novel |
| CodeAid | Conceptual help, pseudocode explanations and annotations/fix suggestions, evaluated in a course deployment | Educational usefulness requires an appropriately designed study |
| Hypothesis | Property-based generation, failure shrinking, and best-effort explain-phase features | These library capabilities are reused and attributed, not claimed as inventions |

The candidate contribution is the implemented connection between a validated, reduced witness, recorded execution and source-gated, evidence-referenced feedback within declared contracts. Whether it is sufficiently novel for a venue remains a review question. The current technical evaluation does not demonstrate educational benefit or general root-cause identification.

## Primary sources

1. Python Tutor official visualizer and documentation: https://pythontutor.com/visualize.html
2. Tillmann, Bishop, Horspool, Perelman, and Xie. *Code Hunt: Searching for Secret Code for Fun* (SBST 2014). https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/CodeHunt20SBST202014b.pdf
3. Rivers and Koedinger. *Data-Driven Hint Generation in Vast Solution Spaces: A Self-Improving Python Programming Tutor*. Author manuscript: https://krivers.net/files/ijaied2015-paper.pdf
4. Liffiton, Sheese, Savelka, and Denny. *CodeHelp: Using Large Language Models with Guardrails for Scalable Support in Programming Classes* (2023). https://arxiv.org/abs/2308.06921 ; DOI 10.1145/3631802.3631830.
5. Kazemitabaar et al. *CodeAid: Evaluating a Classroom Deployment of an LLM-based Programming Assistant that Balances Student and Educator Needs* (CHI 2024). https://arxiv.org/abs/2401.11314 ; DOI 10.1145/3613904.3642773.
6. Hypothesis API, including generation, shrink and explain phases: https://hypothesis.readthedocs.io/en/latest/reference/api.html
7. QuixBugs dataset and program provenance: https://github.com/jkoppel/QuixBugs ; pinned commit in fixtures/catalog.json.

Sources reviewed 26 November 2026. The prototype does not embed or copy source from the five related educational systems.
