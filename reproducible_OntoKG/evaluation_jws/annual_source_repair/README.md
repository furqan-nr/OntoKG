# Bounded annual-source repair v1

This is a new audit overlay, not an edit to the archived workbook, original graphs,
financial-v2 graphs, or the preceding source-authentication results. It repairs
annual source identity and monetary scale for OGDC, with PPL candidates explicitly pending. Run
`docs/jws_annual_source_repair.py` and its `--self-test` option.

## Primary sources

- OGDC [annual-results letter and statements](https://dps.psx.com.pk/download/document/259805.pdf),
  letter dated 23 September 2025; PDF page 3 (printed page 2), company statement
  of profit or loss for the year ended 30 June 2025, with 2024 comparison. This is
  not the consolidated statement. Monetary amounts are in rupees thousand;
  EPS is rupees per share.
- PPL [annual report 2025](https://dps.psx.com.pk/download/document/261187.pdf),
  unconsolidated statement of profit or loss for the year ended 30 June 2025,
  with 2024 comparison is the **candidate**, not yet visually authenticated source.
  The [results letter](https://dps.psx.com.pk/download/document/259574.pdf)
  is dated 19 September 2025. Both downloads were still incomplete after a bounded
  retrieval attempt; their partial local files are not valid evidence copies.
  The official indexed financial table agrees arithmetically, but all six PPL
  facts remain `pending_financial_page_visual_review`, not authenticated.

The old registered OGDC/PPL half-year sources cannot authenticate annual values
and remain preserved as historical source-selection errors. Four OGDC monetary
cells are visually verified after multiplication by 1,000,000, and two OGDC EPS
cells match without change. The same corrections are candidates for four PPL
monetary cells and two PPL EPS values, pending financial-page review. The four archived
year-on-year growth percentages already match recomputation: a common scale
cancels in the ratio. PPL scope is **unconsolidated**, so a consolidated PAT
figure is not an interchangeable alternative.

## Boundaries

FY2024 values are verified against the comparative columns of the FY2025
statement, not against separately retrieved original FY2024 releases. This
bounded, purposive repair does not establish overall source accuracy across
markets. Neither PDF metadata nor a dated letter establishes first-publication
time. No observation window or event anchor is repaired here.

The complete OGDC source PDF and rendered inspection pages are kept in the already
Git-ignored `source_authentication/evidence` directory. Their hashes identify
the inspected copies, not cryptographic publisher signatures. Do not package
or redistribute source documents without checking rights. Public artifacts
contain links, numerical transcriptions, review locators, and hashes.

`repairs.ttl` creates OGDC `AuthenticatedCellRepair` and PPL `PendingCellRepair` resources with explicit
original and replacement source URLs. It does not overwrite `hasNumericValue`
on any production observation. Downstream code must explicitly consume this
overlay rather than treating it as a silent graph patch.
