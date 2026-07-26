# Running the GraphRAG/LLM faithfulness experiment on a free Kaggle GPU

No paid API key is needed: a Kaggle notebook gives a free GPU on which you load an open-weight
instruct model locally and generate real GraphRAG answers. The harness then scores them automatically
against the validated knowledge graph and appends a live model row to the model-comparison results.

## Steps

1. **Upload the data.** On kaggle.com → Datasets → New Dataset, upload the `reproducible_OntoKG/`
   folder (or this whole archive). Note its mounted path, e.g.
   `/kaggle/input/ontokg-eq/reproducible_OntoKG`.
2. **New Notebook** → Settings: **Accelerator = GPU T4 x2** (or P100), **Internet = On**.
3. Paste these cells and run:

```python
# Cell 1 — dependencies
!pip -q install rdflib transformers accelerate bitsandbytes sentencepiece

# Cell 2 — copy the repo to a writable dir (Kaggle inputs are read-only)
import shutil, os
SRC = "/kaggle/input/ontokg-eq/reproducible_OntoKG"     # <-- set to your dataset path
shutil.rmtree("/kaggle/working/repo", ignore_errors=True)
shutil.copytree(SRC, "/kaggle/working/repo")

# Cell 3 — run the harness with a local open-weight model (no API key)
import os
os.environ["ONTOKG_LLM"] = "hf:Qwen/Qwen2.5-7B-Instruct"   # 4-bit; fits a single T4
os.environ["ONTOKG_OUT"] = "/kaggle/working"
!cd /kaggle/working/repo && python docs/graphrag_faithfulness.py

# Cell 4 — view results
print(open("/kaggle/working/graphrag_faithfulness.md").read())
```

4. **Copy the live row** from `/kaggle/working/graphrag_faithfulness.md` (the
   `GraphRAG/LLM [hf:Qwen/Qwen2.5-7B-Instruct]` line) into the model-comparison results, and download
   `graphrag_faithfulness.{md,csv}` from the notebook's Output for the reproducibility bundle.

## Model options

- Default: `hf:Qwen/Qwen2.5-7B-Instruct` (Apache-2.0, ungated, no key).
- If you hit GPU memory limits: `hf:Qwen/Qwen2.5-3B-Instruct`.
- For more models, run several and report the distribution: `meta-llama/Llama-3.1-8B-Instruct` or
  `google/gemma-2-9b-it` (these require accepting the model licence on Hugging Face + a Kaggle HF token).
- Free Gemini instead of a local model: get a free key at aistudio.google.com, add it as a Kaggle
  Secret `GOOGLE_API_KEY`, then set `ONTOKG_LLM=gemini:gemini-1.5-flash`.

## What you get

A live, real-LLM `GraphRAG/LLM` row to compare against the OntoKG-EQ provenance-grounded reference
(faithfulness 1.00, 0 hallucinated numbers, 0 unsupported assertions, full provenance). Running across
multiple models turns Table 7 into a faithfulness/hallucination distribution — the model-comparison distribution reported in the evaluation.
