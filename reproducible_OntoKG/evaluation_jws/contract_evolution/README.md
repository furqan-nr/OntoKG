# Bounded CQ3 contract evolution

Change: strict outperformance over both comparators becomes strict outperformance by more than 1 percentage point.

The query and documented rule variants are derived by replacing their original FILTERs. Production code and source graphs remain unchanged. The manifest supplies artifact paths; impact classification is explicit for this bounded edit and is not a general inference mechanism.

| Snapshot | Original selected rows | Changed selected rows | Oracle and archived-query replay |
|---|---:|---:|---|
| psx | 2 | 1 | Pass |
| msx | 0 | 0 | Pass |
| idx | 2 | 1 | Pass |

CQ1, CQ2 and CQ4 return identical rows before and after read-only CQ3 execution on each unchanged snapshot. These are read-only same-snapshot controls, not a broad regression or change-impact proof. Query, rule, contract, shape and graph hashes are recorded in report.json. An old query paired with the new contract fails the query-hash match.

Synthetic boundary fixtures select 3 companies under the original condition and 1 under the new condition. These are test cases, not market findings. Exact thresholds are excluded because both conditions use strict greater-than.

Support-only replay results are also recorded separately. Disagreement with full-query selection means the archived finding supports do not meet the typed contract; it is not silently counted as successful replay.

Limitations: no production rematerialization, source verification, general change-impact inference, or proof of upstream metric correctness. Rule artifacts are versioned but the main production inference implementation would require a corresponding reviewed update before adopting v2.
