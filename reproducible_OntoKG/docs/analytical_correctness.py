#!/usr/bin/env python3
"""Independent analytical-correctness check for the 64-stock Indonesia window returns.

For every company it recomputes the post-report statistic independently and
compares it to the released graph (without importing the graph builder):

  A. sum of the stored per-day simple returns   (Sigma daily_return * 100)
  B. daily returns recomputed from the raw closes (close[t]/close[t-1] - 1), summed

The statistic is an arithmetic sum, not compounded holding-period return.
Source-close consistency is a separate diagnostic. This audit does not establish
source truth or validate all metrics (see analytical_correctness.md).

Run:  python docs/analytical_correctness.py
"""
from pathlib import Path
import openpyxl
from rdflib import Graph, Namespace, Literal

SHEET = Path(__file__).resolve().parents[2] / "scale_up" / "IDX_scaled_data" / "04_market_windows.xlsx"
TOL = 1e-6  # percentage points
GRAPH = Path(__file__).resolve().parents[1] / "data" / "demo_idx_scaled.ttl"
EX = Namespace("https://w3id.org/ontokg-eq#")
IDX = Namespace("https://w3id.org/ontokg-eq/idxscaled#")


def load_rows(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = {str(h).strip(): i for i, h in enumerate(rows[0]) if h is not None}
    out = []
    for r in rows[1:]:
        if r[hdr["window_type"]] != "post_report":
            continue
        out.append((r[hdr["company_id"]], r[hdr["trade_date"]],
                    r[hdr["close"]], r[hdr["daily_return"]]))
    wb.close()
    return out


def window_returns(rows):
    per = {}
    for sym, date, close, dret in rows:
        per.setdefault(sym, []).append((str(date), close, dret))
    a, b = {}, {}
    for sym, series in per.items():
        series.sort(key=lambda x: x[0])
        stored = [d for _, _, d in series if d is not None]
        if len({d for d, _, _ in series}) != len(series):
            raise ValueError(f"Duplicate dates for {sym}")
        if not stored:
            raise ValueError(f"No daily returns for {sym}; fallback branch is outside this audit")
        a[sym] = sum(float(d) for d in stored) * 100.0
        closes = [c for _, c, _ in series if c is not None]
        recomputed = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
        b[sym] = sum(recomputed) * 100.0
    return a, b


def main():
    rows = load_rows(SHEET)
    a, b = window_returns(rows)
    syms = sorted(a)
    graph = Graph().parse(GRAPH, format="turtle")
    graph_nodes = set(graph.subjects(EX.hasMetricName, Literal("post-report window return %")))
    expected_nodes = {IDX[f"derived_post_return_{s}"] for s in syms}
    if graph_nodes != expected_nodes:
        raise ValueError(f"Metric coverage mismatch: missing={len(expected_nodes-graph_nodes)}, extra={len(graph_nodes-expected_nodes)}")
    graph_values = {}
    for s in syms:
        node = IDX[f"derived_post_return_{s}"]
        values = list(graph.objects(node, EX.hasMetricValue))
        if len(values) != 1:
            raise ValueError(f"Expected exactly one metric value for {s}")
        if (node, EX.isObservationOf, IDX[f"company_{s}"]) not in graph:
            raise ValueError(f"Metric company association mismatch: {s}")
        graph_values[s] = float(values[0])
    diffs = {s: abs(a[s] - graph_values[s]) for s in syms}
    matches = sum(1 for s in syms if diffs[s] <= TOL)
    worst = max(diffs.values()) if diffs else 0.0
    print(f"companies: {len(syms)}")
    print(f"source arithmetic sum vs graph (tolerance {TOL} pp): {matches}/{len(syms)}")
    print(f"worst source-to-graph difference: {worst:.9f} percentage points")
    print(f"source sum vs close-derived sum: {sum(abs(a[s]-b[s]) <= TOL for s in syms)}/{len(syms)}")
    print(f"worst source-close diagnostic difference: {max(abs(a[s]-b[s]) for s in syms):.9f} pp")
    if matches != len(syms):
        for s in syms:
            if diffs[s] > TOL:
                print(f"  MISMATCH {s}: source-sum={a[s]}  graph={graph_values[s]}")
        raise SystemExit(1)
    print("PASS: released graph arithmetic window statistics match independent source sums.")


if __name__ == "__main__":
    main()
