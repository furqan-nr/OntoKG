# Multi-model oracle faithfulness panel (8 open models, greedy, free GPU; 2026-07-02)

Curated cohort n=6, scaled-64 Indonesia cohort n=41. OntoKG-EQ / any deterministic linearizer = 1.00 on every axis by construction.

| Method | n | numeric faithf. | halluc. | unsupported | provenance | 95% CI |
|---|--:|--:|--:|--:|--:|---|
| OntoKG-EQ / deterministic linearizer (design guarantee) | 47 | 1.00 | 0.00 | 0.00 | 1.00 | [0.92, 1.00] |
| Qwen2.5-0.5B-Instruct (curated) | 6 | 0.83 | 0.33 | 0.17 | 0.00 | [0.00, 0.39] |
| Qwen2.5-0.5B-Instruct (scaled-64) | 41 | 0.94 | 0.17 | 0.39 | 0.00 | [0.00, 0.09] |
| Qwen2.5-1.5B-Instruct (curated) | 6 | 0.95 | 0.17 | 0.17 | 0.00 | [0.00, 0.39] |
| Qwen2.5-1.5B-Instruct (scaled-64) | 41 | 1.00 | 0.00 | 0.02 | 0.05 | [0.01, 0.16] |
| Qwen2.5-3B-Instruct (curated) | 6 | 1.00 | 0.00 | 0.00 | 0.33 | [0.10, 0.70] |
| Qwen2.5-3B-Instruct (scaled-64) | 41 | 0.98 | 0.07 | 0.00 | 1.00 | [0.91, 1.00] |
| Qwen2.5-7B-Instruct (curated) | 6 | 0.95 | 0.17 | 0.00 | 0.67 | [0.30, 0.90] |
| Qwen2.5-7B-Instruct (scaled-64) | 41 | 1.00 | 0.00 | 0.00 | 0.61 | [0.46, 0.74] |
| SmolLM2-1.7B-Instruct (curated) | 6 | 1.00 | 0.00 | 0.00 | 1.00 | [0.61, 1.00] |
| SmolLM2-1.7B-Instruct (scaled-64) | 41 | 0.92 | 0.29 | 0.00 | 0.49 | [0.34, 0.64] |
| Phi-3.5-mini-instruct (curated) | 6 | 1.00 | 0.00 | 0.00 | 1.00 | [0.61, 1.00] |
| Phi-3.5-mini-instruct (scaled-64) | 41 | 1.00 | 0.00 | 0.00 | 1.00 | [0.91, 1.00] |
| Mistral-7B-Instruct-v0.3 (curated) | 6 | 0.95 | 0.17 | 0.00 | 1.00 | [0.61, 1.00] |
| Mistral-7B-Instruct-v0.3 (scaled-64) | 41 | 1.00 | 0.00 | 0.00 | 1.00 | [0.91, 1.00] |
| TinyLlama-1.1B-Chat-v1.0 (curated) | 6 | 0.88 | 0.33 | 0.00 | 0.17 | [0.03, 0.56] |
| TinyLlama-1.1B-Chat-v1.0 (scaled-64) | 41 | 0.95 | 0.29 | 0.37 | 0.66 | [0.51, 0.78] |

Key finding: provenance on the scaled-64 cohort ranges 0.00–1.00 and is NON-monotonic in model size
(Qwen2.5-3B=1.00 > Qwen2.5-7B=0.61). Pairwise exact McNemar partitions the models into 3 tiers
(near-zero: 0.5B/1.5B; partial ~0.49-0.66: 7B/SmolLM/TinyLlama; reliable=1.00: 3B/Phi/Mistral); cross-tier
p<1e-4, within-tier non-significant. Smallest models also fabricate numbers and add unsupported assertions.
See panel_mcnemar.csv for the full pairwise matrix.
