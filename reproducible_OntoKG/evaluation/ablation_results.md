# Ablation study (D4)

Each component removed in isolation; the metric it supports degrades.

## Explanation completeness (fraction of findings with full obs+evidence+source+provenance path)

| Market | Findings | Full | No provenance | No evidence-source |
|---|---:|---:|---:|---:|
| PSX | 9 | 1.00 | 0.00 | 0.00 |
| MSX | 2 | 1.00 | 0.00 | 0.00 |

## Inference rules removed (findings derived)

| Market | With rules | Without rules |
|---|---:|---:|
| PSX | 9 | 0 |
| MSX | 2 | 0 |

## Evidence bundles removed (CQ5 explainability rows)

| Market | With bundles | Without bundles |
|---|---:|---:|
| PSX | 3 | 0 |
| MSX | 3 | 0 |

## SHACL removed (malformed observation detected?)

| Market | With SHACL (violations caught) | Without SHACL |
|---|---:|---:|
| PSX | 1 | 0 (undetected) |
| MSX | 1 | 0 (undetected) |
