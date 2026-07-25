# Explanation faithfulness: GraphRAG/LLM vs OntoKG-EQ (D5)

Worked cases: 6 (CQ3 outperformer + CQ1 divergence findings across PSX/MSX/IDX). Scored automatically against the validated graph.

| Method | cases | numeric faithfulness | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|---:|
| OntoKG-EQ (provenance-grounded) | 6 | 1.00 | 0.00 | 0.00 | 1.00 |

*Controlled metric-validation variants (single case; confirm each failure detector):*

| Variant | numeric faithfulness | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|
| variant: faithful | 1.00 | 0 | 0 | 1 |
| variant: numeric hallucination | 0.67 | 1 | 0 | 1 |
| variant: unsupported assertion | 1.00 | 0 | 2 | 1 |
| variant: missing provenance | 1.00 | 0 | 0 | 0 |

> No LLM provider set (ONTOKG_LLM unset): only the OntoKG-EQ reference and controlled variants are scored. Set ONTOKG_LLM (e.g. `hf:Qwen/Qwen2.5-7B-Instruct` on a free GPU) to append a live GraphRAG/LLM row.

## Live run (Kaggle free GPU, Qwen2.5-7B-Instruct, 2026-06-30)

Open-weight model, no API key; six worked cases; scored by the same harness.

| Method | cases | numeric faithfulness | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|---:|
| OntoKG-EQ (provenance-grounded) | 6 | 1.00 | 0.00 | 0.00 | 1.00 |
| GraphRAG/LLM [Qwen2.5-7B-Instruct] | 6 | 1.00 | 0.00 | 0.00 | 0.67 |
| GraphRAG/LLM [Qwen2.5-3B-Instruct] | 6 | 1.00 | 0.00 | 0.00 | 0.00 |

Finding: the open LLM matched numeric faithfulness on this small set but omitted the official source in
2 of 6 answers (provenance 0.67), whereas OntoKG-EQ guarantees provenance (1.00) by construction.
