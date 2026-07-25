#!/usr/bin/env python3
"""Run the UNCHANGED CQ1-CQ5 SPARQL templates on a real triplestore (Oxigraph) at scale.

Closes the at-scale query gap: CQ1/CQ3 (multi-join) exceed RDFLib's in-memory nested-loop engine at
37k triples but run in single-digit milliseconds on Oxigraph, which has a real join planner and indexes.
The SPARQL templates are byte-identical to those run on RDFLib.

Usage:  pip install pyoxigraph
        python triplestore_benchmark.py            # defaults to data/demo_idx_scaled.ttl
"""
import time, os
import pyoxigraph as ox

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTL  = os.environ.get("ONTOKG_TTL", os.path.join(HERE, "data", "demo_idx_scaled.ttl"))
QUERIES = {n: open(os.path.join(HERE, "queries", f"CQ{n}_CASE_01.rq")).read() for n in range(1, 6)}

def main():
    store = ox.Store()
    t0 = time.perf_counter()
    with open(TTL, "rb") as f:
        store.load(f, format=ox.RdfFormat.TURTLE)
    print(f"loaded {len(store):,} triples in {(time.perf_counter()-t0)*1000:.0f} ms "
          f"from {os.path.basename(TTL)}")
    for n, q in QUERIES.items():
        best_ms, rows = float("inf"), 0
        for _ in range(5):                      # best of 5
            s = time.perf_counter()
            res = list(store.query(q))
            best_ms = min(best_ms, (time.perf_counter() - s) * 1000)
            rows = len(res)
        print(f"CQ{n}: {rows} rows in {best_ms:.1f} ms (best of 5)")

if __name__ == "__main__":
    main()
