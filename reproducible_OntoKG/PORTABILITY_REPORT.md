# OntoKG-EQ Portability Report: PSX (KSE-100) ↔ Bursa Malaysia (MSX)

## Purpose

This report documents the portability validation of OntoKG-EQ. The study was
first implemented on Pakistan Stock Exchange (PSX, KSE-100) data. To show that
the ontology and competency-question (CQ) machinery are not specific to one
market, the **same** artifacts and the **same** build pipeline were applied to an
independent Bursa Malaysia (MSX) data slice.

The claim being tested is portability of the **data-and-knowledge-engineering
contribution** — a bounded, CQ-governed, provenance-aware ontology and query
layer — not the portability of any financial finding.

## What is shared (reused unchanged across both markets)

- `ontology/core.ttl`, `ontology/project.ttl`, `ontology/alignment.ttl` — the core ontology
- `shacl/shapes.ttl` — the SHACL validation shapes
- `queries/CQ1_CASE_01.rq` … `queries/CQ5_CASE_01.rq` — the five CQ SPARQL templates
- `build_market_graph.py` — one builder, one construction logic, for both markets

Only the **instance data** differs (the nine spreadsheets per market).

## One pipeline, two markets

`build_market_graph.py` reads a market's nine spreadsheets and emits an RDF graph
aligned to the core ontology. Both markets use the identical sheet→ontology
mapping:

| Spreadsheet | Ontology mapping |
|---|---|
| 02 company master | `Company` (+ `IndustrySectorClassifier`, `IndustrySectorClassificationScheme`) |
| 03 fundamentals | `FundamentalObservation` + `ReportingPeriod` |
| 04 market windows | `MarketObservation` + `AnalysisWindow` / `EventWindow` |
| 05 comparators | `MarketObservation` of sector classifier / `MarketIndex` benchmark |
| 06 FX (SBP / BNM) | `ExchangeRateObservation` (USD/local, `Currency`) |
| 07 announcements | `Announcement` (`EvidenceItem`) + `Publisher` |
| 08 provenance | `EvidenceSource` + `ProvenanceRecord` |
| 09 query cases | `QueryExecution` + `EvidenceBundle` for CQ1–CQ5 |

Only a small per-market config differs (file prefix, currency, EPS/FX column
names, benchmark label, namespace). For each CQ worked case the **result entity,
evidence item, and CQ family** are taken from sheet 09; the **supporting
observation set** is built by a deterministic, market-agnostic recipe:

- CQ1: company fundamentals + post-report market endpoints
- CQ2: post-report market endpoints + FX endpoints
- CQ3: post-report endpoints + sector-comparator endpoints + benchmark endpoints
- CQ4: company event-window observations
- CQ5: company fundamentals + post-report endpoints (combined explanation)

(The recipe is used in place of PSX sheet-09's bare integer observation IDs,
which are loosely curated and cross-reference inconsistent rows; the recipe makes
construction identical and reproducible across both markets.)

Companies: PSX = ENGRO, FFC (Fertilizer), OGDC, PPL (Oil & Gas);
MSX = MAYBANK, CIMB (Financial Services), TM, MAXIS (Telecommunications & Media).

## Results (identical artifacts, identical pipeline)

| Check | PSX (KSE-100) | MSX (Bursa Malaysia) |
|---|---:|---:|
| RDF triples | 3,805 | 2,442 |
| SHACL `Conforms` | True | True |
| CQ1 (fundamentals vs market response) | 4 rows | 4 rows |
| CQ2 (FX context) | 4 rows | 4 rows |
| CQ3 (relative outperformance) | 100 rows* | 100 rows* |
| CQ4 (announcement event windows) | 10 rows | 10 rows |
| CQ5 (explainability / provenance) | 4 rows | 4 rows |

*CQ3 is capped by the query's `LIMIT 100`.

Both market graphs pass the same SHACL constraints, and all five CQs return
non-empty, evidence-linked result sets on both. Because the construction logic is
identical, the CQ result *shapes* match across markets; the *values* are each
market's real data (e.g. PSX CQ1 returns FFC's FY2024/FY2025 EPS of 45.49 / 51.69
with its post-report closes; MSX CQ1 returns Maybank's EPS of 0.84 / 0.87).
Each result traces `QueryExecution → EvidenceBundle → observations →
evidence item → source → provenance` — the same explainability path in both.

## Two PSX graphs in this bundle

| File | What it is |
|---|---|
| `data/demo.ttl` | Original hand-curated PSX demonstrator (343 triples, abstract Company A/B). Used by the published `run_sparql_queries.py` checks. Unchanged. |
| `data/demo_psx.ttl` | Full PSX graph materialized from the `PSX data v4` spreadsheets by `build_market_graph.py`. Apples-to-apples counterpart of `data/demo_msx.ttl`. |

## How to rep