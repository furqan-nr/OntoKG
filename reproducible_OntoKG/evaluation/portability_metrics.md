# Quantified portability (D1, part b)

Across markets, **13 core artifacts are reused byte-identical**; only the nine-sheet data and a
bounded adapter configuration change. Demonstrated on **three independent emerging markets**.

## Reused-unchanged apparatus (market-independent)

ontology (`core/project/alignment.ttl`), SHACL `shapes.ttl`, the five CQ SPARQL templates,
the inference vocabulary + rules (`rules/findings.ttl`, `rules/inference_rules.rq`), the unified
builder (`build_market_graph.py`) and the inference/explanation generator (`infer_and_explain.py`).
**= 13 artifacts, 100% reused unchanged.**

## Per-market surface (the only things that change)

| Market | Data folder | Companies (sectors) | Adapter config highlights |
|---|---|---|---|
| PSX | `PSX data v4/` | ENGRO, FFC (Fertilizer); OGDC, PPL (Oil & Gas) | ns=psx, eps, pkr_usd_rate/06_sbp_fx, PKR, growth×1, benchmark="market index" |
| MSX | `updated MSX/` | MAYBANK, CIMB (Financial); TM, MAXIS (Telecom) | ns=msx, eps_myr, myr_usd_rate/06_bnm_fx, MYR, growth×100, benchmark="broad_market_benchmark_proxy" |
| IDX | `IDX data v1/` | BBCA, BMRI (Banking); ISAT, TOWR (Telecom) | ns=idx, eps, idr_usd_rate/06_fx, IDR, growth×1, benchmark="broad_market_benchmark" (JCI) |

## Three-market results (identical ontology, shapes, queries, rules, code)

| Market | RDF triples | SHACL | CQ1 | CQ2 | CQ3 | CQ4 | CQ5 | Inference findings | Data |
|---|---:|:---:|---:|---:|---:|---:|---:|---:|---|
| PSX (KSE-100) | 4,065 | True | 0 | 4 | 2 | 6 | 3 | 9 | full, from spreadsheets |
| MSX (Bursa) | 2,618 | True | 2 | 4 | 0 | 0 | 3 | 2 | full, from spreadsheets |
| IDX (Jakarta) | 4,185 | True | 0 | 4 | 2 | 6 | 3 | 10 | **real, from Yahoo daily; 83 exact shared dates** |

## Portability ratio

- Apparatus reused unchanged: **13/13 = 100%** (ontology, shapes, queries, rules, code).
- Market-dependent surface: 1 data folder + 1 config record (~9 keys) per market.
- Demonstrated on **3** independent emerging markets with identical CQ/inference/explanation behaviour;
  every market is SHACL-conformant and exercises the competency questions. Empty CQ cells are honest
  data outcomes on bounded slices (e.g. in a falling Jakarta market, large caps fell less than the
  index, so CQ1's "weak response vs benchmark" set is empty), not pipeline failures.

## IDX provenance note

The Indonesia market uses real daily data: company closes/volumes (BBCA.JK, BMRI.JK, ISAT.JK,
TOWR.JK), USD/IDR (IDR=X), and the Jakarta Composite (^JKSE) from Yahoo Finance, retained only on the
83 trading dates shared by all six series (2026-01-15..2026-05-29), with no interpolation or synthetic
rows; fundamentals from S&P/stockanalysis; FY2025 announcement anchors from official IDX disclosure
PDFs. TLKM was replaced by TOWR because TLKM's FY2025 audited results were released too late for a
completed post-event window.
