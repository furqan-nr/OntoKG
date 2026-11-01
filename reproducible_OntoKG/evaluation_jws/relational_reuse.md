# Relational reuse control

Run: 2026-10-16. Same SQLite schema, CQ1/CQ3 SQL, and dependency join reused unchanged across PSX, MSX, and IDX.

| Market | CQ1 SQL/SPARQL | CQ3 SQL/SPARQL | Dependency rows SQL/SPARQL | Numeric/FK rejection |
|---|---:|---:|---:|---|
| PSX | 0/0 (equal) | 2/2 (equal) | 19/19 (equal) | pass |
| MSX | 2/2 (equal) | 0/0 (equal) | 6/6 (equal) | pass |
| IDX | 0/0 (equal) | 2/2 (equal) | 20/20 (equal) | pass |

Schema SHA-256: `4d6ef6ac278260ee80b504b2d2d12b63818686152d02088cec0404fddeb0f5e0`.
SQL hashes and input graph hashes are recorded in `relational_reuse.json`.

The relational schema includes numeric checks, foreign keys, source/context records, persistent findings, deciding observations, bundles, and evidence-source joins. Both CQ result sets include the returned numeric values, not only company identifiers. Dependency equality compares finding, CQ, entity, supported observation, metric/value, bundle, contextual evidence item, and source.

The evidence join associates contextual bundle evidence with findings. It does not assert an independently verified source for each numeric observation; a bundle join can form multiple combinations of observations and contextual sources. Equality establishes representation/query equivalence on the supplied graphs, not complete provenance or absence of missing source records.

This fair control uses the same stored graph metrics for both representations. It demonstrates that normalized relational schemas can also support unchanged cross-market queries, constraints, and evidence joins. It does not independently recompute source metrics, measure mapping/engineering effort, test different raw schemas, establish market-data authenticity, or show an RDF advantage. Empty-result queries are weak evidence and are reported explicitly. Constraint tests show rejection of a nonnumeric value and unknown subject; they are not a comprehensive integrity evaluation.

SQLite 3.49.1; rdflib 7.6.0. Overall: PASS.
