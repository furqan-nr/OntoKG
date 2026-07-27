#!/usr/bin/env python3
"""Independent analytical-correctness check for the 64-stock Indonesia window returns.

For every company it recomputes the post-report window return two independent ways
from the source sheet and confirms they agree:

  A. sum of the stored per-day simple returns   (Sigma daily_return * 100)
  B. daily returns recomputed from the raw closes (close[t]/close[t-1] - 1), summed

Agreement for all companies shows the stored daily returns and their window-return
sum are a faithful, correctly aggregated transform of the source closes. It does not
establish that the source series themselves are correct (see analytical_correctness.md).

Run:  python docs/analytical_correctness.py
"""
from pathlib import Path
import openpyxl

SHEET = Path(__file__).resolve().parents[2] / "scale_up" / "IDX_scaled_data" / "04_market_windows.xlsx"
TOL = 1e-6  # percentage points


def load_rows(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = {str(h).strip(): i for i, h in enumerate(rows[0]) if h is not None}
    out = []
    for r in rows[1:]:
        if r[hdr["window_type"]] != "post_report":
            continue
        out.append((r[hdr["company_symbol"]], r[hdr["trade_date"]],
                    r[hdr["close"]], r[hdr["daily_return"]]))
    return out


def window_returns(rows):
    per = {}
    for sym, date, close, dret in rows:
        per.setdefault(sym, []).append((str(date), close, dret))
    a, b = {}, {}
    for sym, series in per.items():
        series.sort(key=lambda x: x[0])
        stored = [d for _, _, d in series if d is not None]
        a[sym] = round(sum(float(d) for d in stored) * 100.0, 6)
        closes = [c for _, c, _ in series if c is not None]
        recomputed = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
        b[sym] = round(sum(recomputed) * 100.0, 6)
    return a, b


def main():
    rows = load_rows(SHEET)
    a, b = window_returns(rows)
    syms = sorted(a)
    diffs = {s: abs(a[s] - b[s]) for s in syms}
    matches = sum(1 for s in syms if diffs[s] <= TOL)
    worst = max(diffs.values()) if diffs else 0.0
    print(f"companies: {len(syms)}")
    print(f"window returns agree (|A-B| <= {TOL} pp): {matches}/{len(syms)}")
    print(f"worst absolute difference: {worst:.6f} percentage points")
    if matches != len(syms):
        for s in syms:
            if diffs[s] > TOL:
                print(f"  MISMATCH {s}: stored-sum={a[s]}  close-recompute={b[s]}")
        raise SystemExit(1)
    print("PASS: derived window returns are a faithful recompute of the source closes.")


if __name__ == "__main__":
    main()
