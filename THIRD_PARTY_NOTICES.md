# Third-party components and research attribution

The AlgoX-Ray orchestration, contracts, UI, tests, adapters and authored fixtures are provided under the project MIT license. This does not relicense dependencies or claim invention of their techniques.

| Component | Role | License | Source |
|---|---|---|---|
| Hypothesis 6.170.17 | Generated inputs, failure search and built-in shrinking | MPL-2.0 with repository-noted exceptions | https://github.com/HypothesisWorks/hypothesis |
| NetworkX 3.7 | Bellman–Ford reference | BSD-3-Clause | https://github.com/networkx/networkx |
| CPython | Runtime and sys.settrace | Python Software Foundation license | https://www.python.org/ |
| FastAPI | Local HTTP interface | MIT | https://github.com/fastapi/fastapi |
| Starlette | ASGI and static files | BSD-3-Clause | https://github.com/Kludex/starlette |
| Pydantic | Request validation | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | Local ASGI server | BSD-3-Clause | https://github.com/encode/uvicorn |
| Cytoscape.js 3.35.0 | Locally vendored graph renderer | MIT | https://github.com/cytoscape/cytoscape.js |
| QuixBugs | One curated, defective external binary-search program | MIT | https://github.com/jkoppel/QuixBugs |

Cytoscape.js is retained in `web/static/vendor/cytoscape.min.js`, with upstream license in `cytoscape.LICENSE`. Its SHA256 is `71fa9ebec21a7ca2c40cff6aacc30d1f6464e363662ad4b2c197e1adc770cd94`.

QuixBugs source is pinned to commit `4257f44b0ff1181dedaedee6a447e133219fcebf`. `python_programs/find_in_sorted.py` is retained with an attributed header and a `solve(payload)` contract adapter. The original algorithm is not silently corrected. Original source hash and URL are recorded in `fixtures/catalog.json`. Upstream license: `fixtures/external/QuixBugs_LICENSE.txt`.

Development tools (pytest, HTTPX, jsonschema, Playwright) retain their respective upstream licenses. Installed distributions retain their own notices. No source from CodeHelp, ITAP, CodeAid or Python Tutor is copied into the application; they are related work. The application does not use an LLM API.

Relevant sources for the research discussion are listed in `docs/RELATED_WORK.md`. Combining capabilities does not establish novelty by itself.
