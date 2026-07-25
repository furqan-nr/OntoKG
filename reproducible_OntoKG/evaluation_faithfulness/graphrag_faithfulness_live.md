# Live GraphRAG/LLM faithfulness vs OntoKG-EQ (base + scaled-64 cohort)

Models: Qwen/Qwen2.5-7B-Instruct and HuggingFaceTB/SmolLM2-1.7B-Instruct, greedy decoding, free Kaggle T4 GPU. Run date: 2026-06-30.

| Method | cases | numeric faithfulness | halluc. numbers | unsupported assertions | provenance |
|---|---:|---:|---:|---:|---:|
| OntoKG-EQ (provenance-grounded) | 47 | 1.00 | 0.00 | 0.00 | 1.00 |
| GraphRAG/LLM Qwen2.5-7B-Instruct (curated) | 6 | 1.00 | 0.00 | 0.00 | 0.33 |
| GraphRAG/LLM Qwen2.5-7B-Instruct (scaled-64) | 41 | 1.00 | 0.00 | 0.00 | 0.44 |
| GraphRAG/LLM SmolLM2-1.7B-Instruct (curated) | 6 | 1.00 | 0.00 | 0.00 | 0.83 |
| GraphRAG/LLM SmolLM2-1.7B-Instruct (scaled-64) | 41 | 0.92 | 0.29 | 0.00 | 0.95 |

Key finding — COMPLEMENTARY failure modes: the mid-size model (Qwen2.5-7B) never fabricates numbers but
omits the official-source citation in most answers (provenance 0.33/0.44); the small model (SmolLM2-1.7B)
echoes the source far more (0.83/0.95) but fabricates numeric values (numeric faithfulness 0.92, ~0.29
hallucinated numbers/answer on the scaled cohort). Neither LLM is faithful on all dimensions at once, and
which dimension breaks depends on the model. OntoKG-EQ is faithful on all four by construction (1.00). The
scorer is therefore discriminating (not uniformly 1.00), not a rubber stamp.
