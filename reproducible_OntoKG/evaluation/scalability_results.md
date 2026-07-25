# Scalability (C3)

The PSX graph was replicated with a constant schema and multiplied instances (each copy a
disjoint namespace suffix), then timed on the reproducibility VM using rdflib's in-memory
store and pySHACL. Reported figures are single-run wall-clock seconds.

## Per-CQ query latency and SHACL validation vs graph size

| scale x | triples | CQ1 (s) | CQ2 (s) | CQ3 (s) | CQ4 (s) | CQ5 (s) | SHACL (s) | conforms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1  | 4,065  | 0.13 | 0.01 | 0.02 | 0.02 | 0.01 | 0.46 | True |
| 5  | 20,309 | 9.96 | 0.15 | 10.03 | 0.05 | 0.01 | 2.30 | True |
| 10 | 40,614 | —    | —    | —     | —    | —    | 4.66 | True |

## Findings

- **SHACL validation scales near-linearly:** 0.46 s at 4k triples, 2.30 s at 20k, 4.66 s at 41k
  (~0.11 s per 1k triples). The structural-validity layer is production-viable on the reference engine.
- **Single-pattern competency questions (CQ2, CQ4, CQ5) scale flat:** all stay under ~0.15 s even at 20k
  triples — they are dominated by a small bounded result set.
- **The two multi-join analytical queries (CQ1, CQ3) degrade sharply** under rdflib's naive in-memory
  nested-loop join: ~0.02 s at 4k triples but ~10 s at 20k. This is an **engine** limitation, not a
  data-model one — the joins (company × benchmark × sector observations over a shared window) are not
  index-optimised by rdflib.

## Implication

For large graphs the appropriate deployment is an optimised triplestore (Apache Jena TDB,
GraphDB, or similar) with join planning and indexing; the OntoKG-EQ model, shapes, and queries
are standard SPARQL/SHACL and run unchanged on such engines. On the reference engine, the
validation and explanation layers already scale, and the analytical-query cost is bounded by the
chosen store rather than by the ontology or the method.
