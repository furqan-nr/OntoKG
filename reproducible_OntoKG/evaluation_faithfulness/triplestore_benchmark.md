# At-scale CQ execution on a real triplestore (Oxigraph)

Unchanged CQ1–CQ5 SPARQL templates on the 64-stock Indonesia graph (37,046 triples), Oxigraph pyoxigraph store. Load: 71 ms. Best of 5 runs.

| CQ | rows | latency (ms) |
|---|---:|---:|
| CQ1 | 17 | 3.81 |
| CQ2 | 63 | 0.26 |
| CQ3 | 24 | 5.06 |
| CQ4 | 0 | 1.63 |
| CQ5 | 3 | 0.09 |

CQ1 and CQ3 (the multi-join analytical queries that exceed RDFLib's in-memory nested-loop engine at this size) return the same counts (17, 24) as the direct condition evaluation, now via the UNCHANGED SPARQL on a real triplestore — closing the at-scale query gap.
