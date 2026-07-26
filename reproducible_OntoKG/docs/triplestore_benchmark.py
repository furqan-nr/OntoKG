#!/usr/bin/env python3
"""Run the UNCHANGED CQ1-CQ5 SPARQL templates on a real triplestore (Oxigraph) at scale.

Closes the at-scale query gap: CQ1/CQ3 (multi-join) exceed RDFLib's in-memory nested-loop engine at
37k triples but run in single-digit milliseconds on Oxigraph, which has a real join planner and indexes.
The SPARQL templates are byte-identical to those run on RDFLib.

Usage:  pip install pyoxigraph
        python triplestore_benchmark.py            # defaults to data/demo_idx_scaled.ttl
"""
import time, os, statistics
import pyoxigraph as ox

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTL  = os.environ.get("ONTOKG_TTL", os.path.join(HERE, "data", "demo_idx_scaled.ttl"))
QUERIES = {n: open(os.path.join(HERE, "queries", f"CQ{n}_CASE_01.rq")).read() for n in range(1, 6)}

import json
OUT = os.path.join(HERE, "evaluation_faithfulness")

def main():
    store = ox.Store()
    t0 = time.perf_counter()
    with open(TTL, "rb") as f:
        store.load(f, format=ox.RdfFormat.TURTLE)
    load_ms = (time.perf_counter() - t0) * 1000
    ntrip = len(store)
    print(f"loaded {ntrip:,} triples in {load_ms:.0f} ms from {os.path.basename(TTL)}")
    results = []
    for n, q in QUERIES.items():
        times, rows = [], 0
        for _ in range(20):                     # 20 recorded runs
            s = time.perf_counter()
            res = list(store.query(q))
            times.append((time.perf_counter() - s) * 1000)
            rows = len(res)
        med, lo, hi = statistics.median(times), min(times), max(times)
        results.append((n, rows, med, lo, hi))
        print(f"CQ{n}: {rows} rows  median {med:.1f} ms  [{lo:.1f}, {hi:.1f}]  (20 runs)")
    os.makedirs(OUT, exist_ok=True)
    json.dump({"triples": ntrip, "load_ms": round(load_ms), "runs": 20,
               "cq": {f"CQ{n}": {"rows": rows, "median_ms": round(med, 1),
                                 "min_ms": round(lo, 1), "max_ms": round(hi, 1)}
                      for (n, rows, med, lo, hi) in results}},
              open(os.path.join(OUT, "triplestore_benchmark.json"), "w"), indent=2)
    with open(os.path.join(OUT, "triplestore_benchmark.md"), "w") as fh:
        fh.write("# Triplestore benchmark (Oxigraph) - unchanged CQ1-CQ5 SPARQL\n\n")
        fh.write(f"Graph: {os.path.basename(TTL)} ({ntrip:,} triples). One-time load {load_ms:.0f} ms. "
                 "Latency = median of 20 recorded runs, min-max in brackets. "
                 "Representative run; latencies are hardware- and run-dependent.\n\n")
        fh.write("| Query | Rows | Latency (ms): median [min-max] |\n|---|---:|---|\n")
        for (n, rows, med, lo, hi) in results:
            fh.write(f"| CQ{n} | {rows} | {med:.1f} [{lo:.1f}, {hi:.1f}] |\n")
    print("wrote", os.path.join(OUT, "triplestore_benchmark.md"))

if __name__ == "__main__":
    main()
