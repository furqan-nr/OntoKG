# Observation source-cell lineage audit and separate overlay

This adds workbook-cell and explicit source-register lineage, not independent verification of original sources. Base graphs remain unchanged. No company announcement is used as evidence for a market metric solely because it concerns the same company.

| Market | Observations | Value-matched mappings | Unresolved mappings | Cells |
| --- | ---: | ---: | ---: | ---: |
| psx | 522 | 500 | 22 | 838 |
| msx | 321 | 319 | 2 | 561 |
| idx | 542 | 542 | 0 | 973 |
| idx_scaled | 4947 | 4944 | 3 | 9055 |

## Coverage of actual finding-support observations

These counts use the current data/demo_<market>_inferred.ttl supportedByObservation links, not all observations or contextual announcements. Graph SHA256 values are recorded in JSON.

| Market | Distinct supporting observations | Source-cell mapped | Unresolved |
| --- | ---: | ---: | ---: |
| psx | 19 | 18 | 1 |
| msx | 6 | 6 | 0 |
| idx | 20 | 20 | 0 |

Unresolved finding-support observations:
- psx: `https://w3id.org/ontokg-eq/psx#derived_event_ar_2_event_1_1`

Overlay Turtle round-trip and source_id-to-register identity smoke checks passed for every market.

Across mapped observation-dependency pairs, 0 cells lack source_id and 0 cells do not resolve to exactly one source-register row (shared cells may be counted repeatedly).

Each mapped observation links through prov:wasDerivedFrom to exact workbook field entities carrying file SHA256, worksheet, Excel cell, original row identifiers and explicit source_id cell. Cell entities link via prov:hadPrimarySource only when their source_id resolves uniquely in sheet 08. The source-register workbook hash, worksheet and row are retained. Registered URLs are recorded rather than treated as checked or official. Dependencies describe the implemented calculations; workbook row lineage is not equivalent to provenance of the original published numbers.

## Remaining gaps

- Current builder uses summed daily returns; the manuscript's compounding claim needs reconciliation.
- Event metrics sum the supplied event daily_return cells without benchmark subtraction in this builder. Those cells may already represent abnormal returns; their upstream meaning requires verification before an abnormal-return claim is accepted or the implementation changed.
- Supplied growth and comparator cells are traced to their workbook/source IDs, but upstream construction from original disclosures or peer constituent data is not certified.
- Value matches check the proposed mapping against archived graph values; correlation uses the existing Pearson helper, so this is not a fully independent analytical correctness audit.
- The overlay supplements rather than changes existing CQ5 bundles. Source evidence should be rendered through these dependency links, while official announcements remain contextual event evidence unless a metric-specific relationship is demonstrated.
- The present unresolved mappings are missing input values represented as default zero observations by the builder (including empty event-return aggregations). They are not certified source-backed zero measurements.
- Duplicate row identifiers, missing values or unmatched derived values remain unresolved. No fallback attachment to a company disclosure is made.

Reproduce: run docs/jws_source_lineage.py with openpyxl and rdflib installed. Inspect source_lineage.csv for observation-level status and source_lineage.<market>.ttl for the separate overlay.
