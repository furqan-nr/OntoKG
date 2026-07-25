# Kaggle run kit — GraphRAG/LLM faithfulness experiment (free, no API key)

This folder has the two things you upload to Kaggle:

1. `dataset_files/` — **four** files (`demo_psx_inferred.ttl`, `demo_msx_inferred.ttl`,
   `demo_idx_inferred.ttl`, and `demo_idx_scaled.ttl`). These ARE the dataset. The scaled file lets the
   notebook evaluate the **64-stock cohort** (24 CQ3 + 17 CQ1 = 41 cases), not just the 6 curated cases.
2. `ontokg_faithfulness.ipynb` — the notebook (the code).

## Exact steps

**A. Create the dataset**
1. kaggle.com → **Datasets → New Dataset**.
2. Drag in the four files from `dataset_files/`.
3. Title it e.g. `ontokg-eq-graphs` → **Create**. (The notebook auto-finds the files, so the exact name
   doesn't matter.)

**B. Create the notebook**
1. kaggle.com → **Code → New Notebook**, then **File → Import Notebook** and choose
   `ontokg_faithfulness.ipynb` (or **Create** a blank notebook and paste the two cells from it).
2. Right panel → **Add Input** → add the dataset you just made.
3. Right panel → **Settings**: Accelerator = **GPU T4 x2**; Internet = **On**.

**C. Run**
1. **Run All**. Cell 1 installs dependencies (~1 min); Cell 2 downloads the open model
   (Qwen2.5-7B-Instruct, ~1–2 min) and evaluates the base cases **plus the 41-case scaled-64 cohort**
   (~10–20 min on a T4).
2. It prints a table and saves `graphrag_faithfulness_live.{md,csv}` to the notebook **Output**
   (`/kaggle/working`).

**D. Use the result**
- The table now has **three** rows: OntoKG-EQ, `GraphRAG/LLM base`, and `GraphRAG/LLM scaled-64`.
  Paste all three back to me and I'll drop the scaled-cohort distribution into Table 7 and re-export.
- Download `graphrag_faithfulness_live.csv` and add it to the reproducibility bundle.
- Paste the printed table back to me and I'll drop the live numbers into the paper and re-export.

## Notes
- **No API key needed** — the model runs locally on Kaggle's free GPU.
- **Switching models / bigger models (e.g. Qwen2.5-14B):** before running a new `MODEL`, do
  **Run → Restart Session** (clears the previous model from VRAM), then **Run All**. Running several
  models back-to-back in one kernel fills the GPU and causes `CUDA out of memory`. The loader now
  force-uses 4-bit (required for 14B on a single T4) and clears the cache automatically.
- If you still hit OOM on a 14B model: it is optional — the two-model result (Qwen2.5-7B + SmolLM2-1.7B)
  is already a complete, publication-strong comparison.
