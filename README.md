# OntoKG-EQ — Reproducibility Repository

Code, data, and evaluation artifacts to independently reproduce and verify every result reported in the
paper *OntoKG-EQ: A provenance-grounded, competency-question-governed knowledge graph for auditable
analyst querying*. **This repository contains no manuscript text** — only the machinery, inputs, and
outputs needed to check the paper's claims.

## Environment

Python 3.10+ and:

```bash
pip install -r requirements.txt
```

Core reproduction needs `rdflib`, `pyshacl`, `openpyxl`, `pandas`, `pyoxigraph`. The LLM faithfulness panel
additionally needs `transformers`, `accelerate`, `bitsandbytes` and is meant to run on a GPU (e.g. a free
Kaggle T4).

## Repository layout

```
reproducible_OntoKG/
  ontology/          core.ttl, project.ttl, alignment.ttl     # CQ-bounded core ontology
  shacl/shapes.ttl                                            # SHACL validation shapes
  queries/           CQ1..CQ5_CASE_01.rq                      # the five competency-question SPARQL templates
  rules/             findings.ttl, inference_rules.rq         # R1..R4 inference rules + findings vocabulary
  build_market_graph.py                                       # one builder: nine sheets -> validated RDF graph
  infer_and_explain.py                                        # inference + evidence-bundle / explanation generation
  docs/              *.py  experiment scripts (see claims map) + make_figures.py
  data/              demo_{psx,msx,idx,idx_scaled}.ttl (+ *_inferred.ttl)   # materialized graphs
  evaluation_{psx,msx,idx,idx_scaled}/                        # per-market CQ result CSVs + summaries
  evaluation_faithfulness/                                    # LLM panel, fault-injection, scaling, fidelity, cost, triplestore results
  expert_study/                                               # user-study instrument, protocol, raw anonymous responses, analysis, results
PSX data v4/ · updated MSX/ · IDX data v1/                    # the nine source spreadsheets per market
scale_up/  + idx_data_acquisition/                            # 64-stock IDX acquisition script + data
kaggle_faithfulness/                                          # 8-model LLM faithfulness notebook + dataset (.ttl)
```

## Quick reproduction (run from `reproducible_OntoKG/`)

```bash
python build_market_graph.py psx        # then: msx, idx, idx_scaled  -> data/demo_*.ttl
pyshacl -s shacl/shapes.ttl -d data/demo_psx.ttl -f human       # expect: Conforms True
python infer_and_explain.py psx         # inference + explanation bundles -> evaluation_psx/
python docs/triplestore_benchmark.py    # unchanged CQ1-CQ5 on Oxigraph (ms latencies)
python docs/scaling_benchmark.py 1,3,30   # controlled scaling (37k, 111k, 1.11M triples)
python docs/fault_injection.py data/demo_psx.ttl   # SHACL error-detection (8/8)
python docs/sql_baseline.py             # serious relational baseline
python expert_study/analyze_expert_study.py   # participant-level user-study stats (paths resolve to the script folder)
python docs/make_figures.py             # regenerate figures
```

The eight-model LLM faithfulness panel runs from `kaggle_faithfulness/ontokg_faithfulness_panel.ipynb`
on a GPU, with the four `.ttl` files in `kaggle_faithfulness/dataset_files/` added as the dataset.

## Claims → where to verify

| Paper claim | Reproduce with | Proof artifact |
|---|---|---|
| All three markets are SHACL-conformant | `build_market_graph.py` + `pyshacl` | `reproducible_OntoKG/data/demo_*.ttl`; `evaluation_*/` summaries |
| CQ1–CQ5 result sets per market (portability table) | `build_market_graph.py`, CQ `.rq` | `evaluation_{psx,msx,idx}/*.csv` + `_summary.md` |
| 64-stock Indonesia cross-section (17 / 63 / 24 / 0 / 3) | `docs/cq_scaled_eval.py` | `data/demo_idx_scaled.ttl`; `evaluation_idx_scaled/` |
| Unchanged CQ SPARQL on a triplestore, single-digit ms | `docs/triplestore_benchmark.py` | `evaluation_faithfulness/triplestore_benchmark.md` |
| Controlled scaling to ~1.1M triples | `docs/scaling_benchmark.py` | `evaluation_faithfulness/scaling_benchmark.md` |
| Fault-injection: SHACL detects 8/8 injected errors | `docs/fault_injection.py` | `evaluation_faithfulness/fault_injection.md` |
| Analytical correctness: 64/64 metrics match independent recompute | `reproducible_OntoKG/docs/analytical_correctness.py` | `evaluation_faithfulness/analytical_correctness.md` |
| Serious relational (SQL) baseline: features/effort | `docs/sql_baseline.py` | console output |
| Component ablations | `docs/ablation_study.py` | `evaluation_*/` outputs |
| 8-model LLM faithfulness + pairwise McNemar | `kaggle_faithfulness/ontokg_faithfulness_panel.ipynb` | `evaluation_faithfulness/panel_results.md`, `panel_mcnemar.csv` |
| Deterministic vs generative cost | — | `evaluation_faithfulness/compute_cost.md` |
| User study (n = 17): trust/completeness/preference | `expert_study/analyze_expert_study.py` | `expert_study/Form responses (17).xlsx`, `expert_study/results.md` |
| Figures | `docs/make_figures.py` | (regenerated) |

## Notes

- Sector baskets, broad-market benchmarks, and FX are documented **demonstrator** constructions, not
  licensed feeds; replace before any empirical market claim.
- The user-study responses are fully anonymous (no personal identifiers).
- Source repository: https://github.com/furqan-nr/OntoKG
- Archived immutable release: https://doi.org/10.5281/zenodo.21569316
