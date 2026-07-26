# Explanation faithfulness: GraphRAG/LLM vs OntoKG-EQ (D5)

Worked cases: 6 (CQ3 outperformer + CQ1 divergence findings across PSX/MSX/IDX). Scored automatically against the validated graph.

| Method | cases | numeric precision | numeric recall | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|---:|---:|
| OntoKG-EQ (provenance-grounded) | 6 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 |

*Controlled metric-validation variants (single case; confirm each failure detector):*

| Variant | numeric precision | numeric recall | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|---:|
| variant: faithful | 1.00 | 1.00 | 0 | 0 | 1 |
| variant: numeric hallucination | 0.67 | 0.67 | 1 | 0 | 1 |
| variant: unsupported assertion | 1.00 | 1.00 | 0 | 2 | 1 |
| variant: missing provenance | 1.00 | 1.00 | 0 | 0 | 0 |
| variant: omission (no numbers) | 1.00 | 0.00 | 0 | 0 | 1 |

> No LLM provider set (ONTOKG_LLM unset): only the OntoKG-EQ reference and controlled variants are scored. Set ONTOKG_LLM (e.g. `hf:Qwen/Qwen2.5-7B-Instruct` on a free GPU) to append a live GraphRAG/LLM row.
