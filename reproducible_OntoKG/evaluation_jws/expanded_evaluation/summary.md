# Expanded bounded contract evaluation

Stored RDF numerical tuples; independent traversal and Decimal predicate arithmetic, no production rule functions. No manual source oracle or source accuracy claim.

Curated IDX is a subset of scaled IDX; original and corrected graphs are paired versions, not independent extra companies. Do not sum across datasets as independent sample size.

| Cohort | Companies | Positive | Negative | Incomplete | No event applicable | Replay agrees |
|---|---:|---:|---:|---:|---:|---|
| psx_curated | 4 | 9 | 11 | 0 | 0 | True |
| msx_curated | 4 | 2 | 12 | 0 | 3 | True |
| idx_curated | 4 | 10 | 10 | 0 | 0 | True |
| idx_scaled_archived | 64 | 43 | 146 | 3 | 64 | True |
| demo_idx_financial_v2 | 4 | 9 | 11 | 0 | 0 | True |
| demo_idx_scaled_financial_v2 | 64 | 42 | 147 | 3 | 64 | True |
| demo_msx_financial_v2 | 4 | 2 | 10 | 2 | 3 | True |
| demo_psx_financial_v2 | 4 | 5 | 6 | 4 | 2 | True |

CQ1/CQ3 comparisons enumerate all eligible graph tuples, compare entire distinct SELECT numerical rows, and report false positives and negatives in results.json. Unknown inputs remain incomplete. R2 is classification only; events are not implied for scaled companies.

Experiment TTL files contain the unchanged source triples plus explicitly constructed candidate findings/bundles for each positive, negative, or incomplete case. These are evaluation fixtures, not newly observed production findings. Positives are oracle-selected independently of stored production findings. Contract replay must reject negative/incomplete evidence. Withheld tests remove complete deciding roles from actual bundles and retain full graph observations. R4 can remain sufficient when its other OR branch passes.

Replay uses a company-specific projection retaining every relevant contract-metric observation for that company, its sectors, and market indexes, plus their entity/window types, links, dependency cells, and primary-source triples. The oracle runs on the complete graph. Oxigraph executes the original unbound SELECT text on the entire input graph. Serialized experiment graphs retain complete inputs.

Eleven synthetic cases include seven R4 cases checking exact inclusive boundaries, missing evidence, negative-return magnitude, and disjoint alternative OR witnesses, plus four R1/R3 strict Decimal boundaries. Their counts are separate from natural cohorts.

Units and upstream metric validity are not certified by this graph-level test. The corrected financial_v2 cohorts are paired sensitivity/repair comparisons. No claims about human audit performance follow from automated replay.

Reproduce: Python 3.13 with .jws_deps on PYTHONPATH; run docs/jws_expanded_evaluation.py.
