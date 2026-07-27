# MSX — Bursa Malaysia (FBM KLCI): competency-question result summary

Result-row counts for the five worked competency-question cases, produced by the unchanged ontology, SHACL shapes, CQ SPARQL templates, and rules on this market's data.

| Competency question | Result rows |
|---|---:|
| CQ1 — Fundamentals | 2 |
| CQ2 — Exchange-rate context | 4 |
| CQ3 — Relative outperformance | 0 |
| CQ4 — Official announcements | 0 |
| CQ5 — Explainability | 3 |

CQ2 is structural (one exchange-rate-association row per company by construction). CQ1/CQ3/CQ4 can legitimately return zero when the data do not satisfy the stated condition. Per-row detail is in the `CQ*_CASE_01_results.csv` files in this directory.
