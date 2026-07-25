# Fidelity audit: three separate properties

We distinguish three properties the reviewer correctly noted are different:

1. **Graph-grounded generation fidelity** — a rendered answer contains only facts present in the validated
   graph. This is guaranteed by construction (deterministic rendering; Section 7.3).
2. **Source fidelity** — the graph's stored values match the source records. The graph is a deterministic
   materialisation of the nine source sheets; raw values (closes, EPS, dates, sources) are copied verbatim.
3. **Analytical correctness** — the *derived* metrics equal an independent recomputation from the source.

**Analytical-correctness check (independent recomputation).** For the 64-stock Indonesia graph we
independently recomputed the post-report window return for every company directly from the source daily
returns (arithmetic cumulative return = Σ daily simple returns × 100), using a separate implementation,
and compared to the value stored in the graph:

- **64 / 64 companies match exactly** (worst absolute error 0.000 percentage points).

This confirms the metric implementation is correct and the graph values are a faithful transform of the
source series. It does **not** establish that the *source series themselves* are correct, nor that the
comparators (sector baskets, benchmark, FX) are anything other than the documented demonstrator
constructions; those require checking against licensed feeds and original disclosure documents, which we
scope as demonstrator data and flag for a manually audited sample in future work.
