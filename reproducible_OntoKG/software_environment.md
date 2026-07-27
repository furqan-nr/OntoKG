# Software and hardware environment

All deterministic results — graph construction, SHACL validation, competency-question SPARQL,
inference/explanation, the SQL baseline, fault injection, the triplestore and scaling benchmarks, the
analytical-correctness check, and the participant-level user-study analysis — were produced in the
environment below. The eight-model LLM faithfulness panel was executed separately on a GPU (Kaggle); its
package versions are pinned in the released notebook.

## Reproduction environment (deterministic pipeline + benchmarks)

- Operating system: Ubuntu 22.04.5 LTS (Linux kernel 6.8.0, x86_64)
- CPU: Intel Core i7-11800H @ 2.30 GHz (2 vCPU available to the run)
- Memory: 3.8 GB RAM
- Storage: local SSD-backed working directory
- Python: 3.10.12
- Packages (exact versions used):
  - rdflib==7.6.0
  - pyshacl==0.31.0
  - openpyxl==3.1.5
  - pandas==2.3.3
  - pyoxigraph==0.5.9   (Oxigraph triplestore — powers the triplestore and scaling benchmarks)
- The user-study statistics (`expert_study/analyze_expert_study.py`) use the Python standard library only
  (exact Wilcoxon signed-rank, seeded participant bootstrap, exact sign test) plus openpyxl to read the export.

The performance figures in Tables 10 and 13 come from this environment; latencies are hardware- and
run-dependent. Re-running `docs/triplestore_benchmark.py` (20 runs) and `docs/scaling_benchmark.py 1,3,30`
regenerates `evaluation_faithfulness/triplestore_benchmark.md` and `scaling_benchmark.md`.

## LLM faithfulness panel (GPU)

- Platform: Kaggle free tier with dual NVIDIA T4 GPUs (2x16 GB); each panel model runs in 4-bit on a single T4, and the 14B model did not load reliably across the pair.
- Frameworks: transformers, accelerate, bitsandbytes, sentencepiece (4-bit loading). Package versions are pinned in the notebook's install cell; the exact resolved versions, CUDA/GPU, and Hugging Face model revisions are written to `environment_lock.json` when the notebook runs.
- Models: eight open-weight instruction models — Qwen2.5-0.5B/1.5B/3B/7B-Instruct, SmolLM2-1.7B-Instruct,
  Phi-3.5-mini-instruct, Mistral-7B-Instruct-v0.3, TinyLlama-1.1B-Chat.

## Notes

- `requirements.txt` pins the core packages to the exact versions above; `requirements-lock.txt` mirrors them.
- Full reproduction steps are in the root `README.md` (run from `reproducible_OntoKG/`).
