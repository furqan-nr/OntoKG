# IDX synchronized raw-input builder — corrected release

## What is fixed in this release

1. **Strict six-series synchronization remains mandatory.** Final inputs are only written when BBCA, BMRI, ISAT, TOWR, USD/IDR, and JCI have an exact date intersection and every event has at least 5 earlier and 35 later shared trading sessions.
2. **Stale final-output protection.** Each builder run removes previously generated final history files before validating current raw inputs. A failed run cannot leave an old `final_raw_inputs/*.csv` set that looks current.
3. **Safer Yahoo acquisition.** The downloader retries temporary Yahoo/network failures and writes raw files only after all six series download successfully. It never creates a partially refreshed raw-data set.
4. **CQ3 peer-basket correction.** ISAT and TOWR now both use `sector=Telecommunications` with `sector_scheme=CQ3 normalized peer-basket sector`. This is an analysis normalization, not a claim that it replaces the official IDX classification.
5. **TOWR metric-semantic correction.** `yoy_profit_growth_pct=10.28` is now the FY2025 consolidated net-profit growth calculated from the official presentation: Rp3,678.3bn in 2025 versus Rp3,335.4bn in 2024. The `eps=69.00` value is retained. The earlier `2.99` is EPS growth and must not populate a field named `yoy_profit_growth_pct`.

## Current status

This release is **acquisition-ready, not data-complete**. The six files under `raw_downloads/` remain header-only placeholders until you run the downloader on a machine with internet access or replace them with permitted manual source files. Do not use `final_raw_inputs/` until `coverage_report.csv` marks every company `COMPLETE` and `build_status.txt` starts with `SUCCESS`.

## Required date range

Acquire all six raw series for at least **2026-01-15 through 2026-05-29**. Use `2026-05-30` as the Yahoo exclusive request end.

| Company | FY2025 result anchor | Required event-window support |
|---|---:|---|
| BBCA | 2026-01-27 | 5 pre + 35 post shared sessions |
| BMRI | 2026-02-06 | 5 pre + 35 post shared sessions |
| ISAT | 2026-02-09 | 5 pre + 35 post shared sessions |
| TOWR | 2026-03-18 | 5 pre + 35 post shared sessions |

## Route A — automatic Yahoo acquisition

From this directory:

```bash
python -m pip install -r requirements.txt
python download_yahoo_idx_series.py --out raw_downloads --start 2026-01-15 --end 2026-05-30
python build_synchronized_idx_inputs.py --raw raw_downloads --output final_raw_inputs
```

The downloader requests **unadjusted daily close** and daily volume for equities. If Yahoo returns rate limiting or a temporary network failure after its retry attempts, use Route B rather than mixing old and newly downloaded files.

## Route B — permitted manual acquisition

Save the six source files using these exact names and required columns:

- `BBCA_history_source.csv`, `BMRI_history_source.csv`, `ISAT_history_source.csv`, `TOWR_history_source.csv`: `Date,Close,Volume`
- `USDIDR_hi