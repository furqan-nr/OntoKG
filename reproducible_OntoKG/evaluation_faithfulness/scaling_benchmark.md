# Controlled scaling benchmark (Oxigraph, on-disk) - unchanged CQ1/CQ3

Replicated 64-stock IDX graph to larger sizes. On-disk Oxigraph store; latency = best of 3 timed runs per scale. Representative run; latencies are hardware- and run-dependent (this script regenerates this file on each run).

| Triples | Ingest (s) | CQ1 rows | CQ1 latency (ms) | CQ3 rows | CQ3 latency (ms) |
|---:|---:|---:|---:|---:|---:|
| 37,046 | 0.2 | 17 | 9.4 | 24 | 11.9 |
| 111,130 | 0.8 | 51 | 31.8 | 72 | 39.4 |
| 1,111,264 | 14.4 | 510 | 468.6 | 720 | 690.5 |
