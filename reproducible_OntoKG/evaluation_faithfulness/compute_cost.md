# Computational cost: OntoKG-EQ vs GraphRAG/LLM (same retrieved evidence)

Measured on the scaled-64 Indonesia graph (37,046 triples), single CPU core, no GPU. Run 2026-06-30.

- Graph parse (one-time): ~1.5 s
- OntoKG-EQ explanation generation: 41 answers in ~108 ms total -> ~2.6 ms/answer (retrieval + render)
- Pure answer-template render: ~0.1 microseconds/answer
- Process peak memory (Python + rdflib + 37k-triple graph): ~70 MB, no GPU

| Path | Hardware | Per answer | Memory | Reproducible |
|---|---|---|---|---|
| OntoKG-EQ (SPARQL + template) | CPU | ~2.6 ms (render sub-microsecond) | ~70 MB | Yes |
| GraphRAG/LLM Qwen2.5-7B / SmolLM2-1.7B | GPU required | order of seconds | ~4-15 GB | No |
| GraphRAG/LLM Qwen2.5-14B | did not fit free dual-T4 | - | >28 GB (fp16) | - |

Two to three orders of magnitude faster per answer, on commodity CPU, with ~70 MB rather than several GB
of accelerator memory, and exactly reproducible. The generative path additionally failed to even load a
14B model on Kaggle's free dual-T4 GPU.
