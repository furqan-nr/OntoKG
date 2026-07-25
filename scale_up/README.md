# Scale the IDX market to ~60 stocks

`scale_idx_market.py` downloads real IDX data from Yahoo Finance and writes the nine OntoKG-EQ sheets
for ~60 stocks into `IDX_scaled_data/`, ready to drop into the builder.

## Run (locally — needs internet)

```bash
pip install yfinance pandas openpyxl
python scale_idx_market.py
```

Runs in ~5–15 min. It prints progress per ticker, keeps only stocks with enough history, and uses only
the trading dates shared by every stock + the JCI index + USD/IDR (no interpolation, no invented rows).

## What it produces (`IDX_scaled_data/`)

`02_company_master.xlsx` … `09_query_cases.xlsx` in the exact schema the pipeline reads, plus
`_scale_summary.txt` (companies kept, skipped, window dates, sector counts). It pulls per stock:
daily close+volume, **sector** (for CQ3 baskets), and **two years of net income + EPS** (for CQ1 YoY
growth) — plus the JCI benchmark and USD/IDR.

## Notes / tuning

- Edit `TICKERS` to add/remove names (~60 liquid large caps are pre-filled, including the original
  BBCA/BMRI/ISAT/TOWR). Use the bare symbol; `.JK` is added automatically.
- `N_WINDOW` (default 60) = trading days in the common analysis window; `PERIOD` (default 6mo) = history pulled.
- Some tickers may be skipped if Yahoo lacks history/financials — that's fine; they're logged in the summary.
- This uses a common recent analysis window across all stocks (good for CQ1/CQ2/CQ3/CQ5 at scale).
  CQ4 event-windows around individual announcement dates are kept for the curated 4-stock set; we can
  add per-stock event windows later if you want CQ4 at scale too.

## Then

Zip and send `IDX_scaled_data/` back. I'll add an `idx_scaled` market config to `build_market_graph.py`,
rebuild + SHACL-validate, run CQ1–CQ5 + inference + explanations on the ~60-stock graph, and report the
scaled results (and update the paper's scale figures).
