# OntoKG-EQ Reproducibility Bundle

This folder is the self-contained reproducibility package requested for the DKE submission workflow.
It includes the ontology files, SHACL shapes, demo data, SPARQL CQ queries, evaluation outputs, and metadata needed to rerun the published checks.

## Contents

- `ontology/project.ttl`
- `ontology/core.ttl`
- `ontology/alignment.ttl`
- `ontology/shapes.ttl`
- `ontology/demo.ttl`
- `ontology/catalog-v001.xml`
- `queries/` with CQ1 to CQ5 SPARQL files
- `evaluation/` with CQ coverage, worked-case, reasoning, and SHACL outputs
- `data/provenance_register.csv`
- `LICENSE`
- `CITATION.cff`
- `run_sparql_queries.py`
- `data_dictionary.md`
- `manuscript_version.txt`
- `software_environment.md`

## How to run the checks

### 1. Protégé

1. Open Protégé Desktop.
2. Load `ontology/project.ttl`.
3. Keep `ontology/catalog-v001.xml` in the same folder so local ontology imports resolve.
4. Use the ELK reasoner and classify the ontology.
5. Check that the class hierarchy loads without inconsistent or unsatisfiable classes.

### 2. SHACL validation

From this folder, run:

```bash
pyshacl -s shacl/shapes.ttl -d data/demo.ttl -f human
```

Expected result: `Conforms: True`.

### 3. SPARQL CQ checks with Jena ARQ

Run each query against the demo data:

```bash
arq --data data/demo.ttl --query queries/CQ1_CASE_01.rq
arq --data data/demo.ttl --query queries/CQ2_CASE_01.rq
arq --data data/demo.ttl --query queries/CQ3_CASE_01.rq
arq --data data/demo.ttl --query queries/CQ4_CASE_01.rq
arq --data data/demo.ttl --query queries/CQ5_CASE_01.rq
```

The `evaluation/` folder contains the expected outputs used for comparison.

## Notes

- The `data/provenance_register.csv` file is the provenance register for the bundle.
- The folder is intended as a reproducibility ZIP source, not as the main working repository.
- The paper is not yet submitted to DKE, so `manuscript_version.txt` only records a not-yet-submitted status.
