# Validation report — corrected package

**Validation date:** 2026-06-28  
**Package state:** acquisition-ready; intentionally not market-data complete.

## Static checks

- `python -m compileall` passed for both Python scripts.
- The two CQ3 peer-basket rows now use the same `Telecommunications` label.
- The TOWR FY2025 `yoy_profit_growth_pct` field is now 10.28, matching the field's declared net-profit-growth semantics.

## Functional acceptance test (synthetic data only)

The builder was run against six generated series with the same 97 weekday dates from 2026-01-15 through 2026-05-29. The data are **not** real market observations and are not included in this release. The purpose was to test control flow and acceptance logic.

| Company | Anchor trade date | Shared pre sessions | Shared post sessions | Result |
|---|---:|---:|---:|---|
| BBCA | 2026-01-27 | 8 | 88 | COMPLETE |
| BMRI | 2026-02-06 | 16 | 80 | COMPLETE |
| ISAT | 2026-02-09 | 17 | 79 | COMPLETE |
| TOWR | 2026-03-18 | 44 | 52 | COMPLETE |

The successful test produced all six final history files with 97 data rows each.

## Failure-safety test

The builder was then run using a header-only BBCA raw file while a stale `BBCA_history.csv` was present in the destination. It failed as designed, deleted the stale final file, and wrote:

```text
BLOCKED: raw-input validation failed. No final CSVs were written.
Reason: BBCA: no usable rows inside 2026-01-15 to 2026-05-29
```

## Current package state

The packaged raw files remain header-only placeholders. Running the builder now correctly produces the same `BLOCKED` status in `final_raw_inputs/build_status.txt`. This is expected; download or manually add the six raw series before using the package.
