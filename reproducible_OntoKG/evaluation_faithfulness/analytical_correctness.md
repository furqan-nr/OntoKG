# Fidelity audit: three separate properties

We distinguish three properties the reviewer correctly noted are different:

1. **Graph-grounded generation fidelity** — a deterministic renderer can reproduce selected facts from
   its input graph. This is conditional on the renderer and evidence selection being correct; structural
   validation alone does not prove that all facts deciding a result are included.
2. **Source fidelity** — graph values agree with source records. Deterministic materialisation is a
   design property, not by itself an independent verification of every copied value.
3. **Analytical correctness** — the *derived* metrics equal an independent recomputation from the source.

**Analytical-correctness check (independent recomputation).** For the 64-stock Indonesia graph we
independently recomputed the post-report window return for every company directly from the source daily
returns (arithmetic cumulative return = Σ daily simple returns × 100), using a separate implementation,
and compared to the value stored in the graph:

- **64 / 64 companies match within 0.000001 percentage points**; worst absolute error is
  **0.000000498 percentage points**, consistent with graph serialization to six decimals.
- Coverage checks found exactly the expected 64 metric nodes; each has one metric value and the
  expected company association.
- Separate source-close diagnostic: **64 / 64** arithmetic sums match the sums recomputed from
  consecutive closes within the same tolerance (worst error rounds to 0.000000000 pp).

Audit rerun: 2026-10-16, using `docs/analytical_correctness.py`, openpyxl 3.1.5 and rdflib 7.6.0.
Inputs: `scale_up/IDX_scaled_data/04_market_windows.xlsx` and `data/demo_idx_scaled.ttl`.
The audit reads actual RDF literals and does not import or call the graph builder. The earlier audit
only compared two source-sheet calculations; it did not perform the source-to-graph comparison
claimed by the previous report. This version repairs that gap.

**Metric semantics:** the builder uses `sum(daily_return) * 100` for company, sector, and benchmark
windows when daily returns exist. This is an arithmetic cumulative simple-return statistic, not the
compounded holding-period return `(product(1 + daily_return) - 1) * 100`. It falls back to endpoint
percentage change for company windows lacking daily returns; that fallback is not exercised here.
The manuscript and queries must use the arithmetic interpretation for the released graphs.

This verifies source-to-graph agreement for the 64 company arithmetic window statistics only. It does
not independently audit benchmark/sector statistics, correlation, fundamentals, evidence completeness,
or every copied raw value. It does **not** establish that the *source series themselves* are correct, nor that the
comparators (sector baskets, benchmark, FX) are anything other than the documented demonstrator
constructions; those require checking against licensed feeds and original disclosure documents, which we
scope as demonstrator data and flag for a manually audited sample in future work.
