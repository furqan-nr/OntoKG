# Original-source spot checks (16 October 2026)

This is a bounded, purposive check, not a random audit or a certification of all source rows. Workbook hashes and cell identities are in financial_v2.json and the versioned graphs. Exchange-hosted financial tables can be standardized by a vendor; they are distinguished below from issuer-authored disclosure text. Accessibility alone is not fact verification.

## ENGROH: original issuer disclosure

Source: [Engro Holdings FY2025 disclosure hosted by PSX](https://dps.psx.com.pk/download/document/271307.pdf), PDF page 16 (zero-based page 15), Financial Performance paragraph. The issuer reports standalone PAT of approximately PKR253 million versus PKR9,854 million, and EPS of PKR0.21 versus PKR20.48. Workbook fundamentals rows 2/3 reproduce those EPS values. PAT cells store 0.253154 and 9.854391 under a thousand-PKR column label; these magnitudes are consistent with billions rather than the declared thousands. The ratio-based growth is unchanged by a common scaling factor, but the absolute monetary unit is wrong. The same paragraph distinguishes consolidated PAT and restructuring effects: this is standalone growth, not a uniform measure of consolidated business performance.

## ENGROH: exchange-hosted financial table

Source: [PSX ENGROH company page](https://dps.psx.com.pk/company/ENGROH), Financials > Annual, accessed 16 October 2026. Its thousands-PKR table reports FY2025/FY2024 total income 548,958/14,473,158 and PAT 253,154/9,854,391. Workbook sales cells are 548.958/14473.158 (factor 1,000 below that table); workbook PAT cells are 0.253154/9.854391 (factor 1,000,000 below that table). Thus the monetary-column scales are inconsistent even within this company's financial record. This also makes the supplied revenue-growth value unsafe: although the two income cells share a scaling factor, the absolute unit labels remain incorrect. EPS matches. PSX cautions that its financial table can be standardized and differ from issuer-reported data.

## FFC: exchange-hosted financial table

Source: [PSX FFC company page](https://dps.psx.com.pk/company/FFC), Financials > Annual, accessed 16 October 2026. The thousands-PKR table reports FY2025/FY2024 PAT 73,564,267/64,731,439, sales 432,410,443/373,536,920 and EPS 51.69/45.49. Workbook fundamentals rows 4/5 match EPS but store PAT 73.564267/64.731439 and sales 432.410443/373.53692 under thousand-PKR headings: both monetary fields differ by factor 1,000,000. This checks four financial numbers after explicit scaling and two EPS facts; it is not issuer-original document authentication.

## Attempted but not verified

- [FFC original results PDF](https://dps.psx.com.pk/download/document/269389.pdf): accessible as a ten-page scan, but reliable fact extraction was unavailable in the current bounded check. Its contents are not counted as independently verified financial values.
- [Maybank registered annual-report URL](https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-integrated-annual-report.pdf): retrieval failed. Registered URL status does not verify numerical facts.
- IDX and scaled-IDX original financial documents, individual daily price/volume facts, comparator construction, FX data, reporting dates and event anchors were not independently authenticated in this pass.

## Consequence for the manuscript

Financial v2 repairs calculations and exposes actual dates, units and cell dependencies. It does not silently repair or certify workbook monetary magnitudes. Derived growth retains an explicit accounting-scope/unit caveat; PAT recomputation tests internal arithmetic, not source accuracy. The source review verifies selected EPS facts and finds material scale defects. It supports transparent qualification, not a claim that source truth is resolved. A complete monetary normalization requires a separately versioned source-by-source extraction review before absolute profit or revenue figures are used as validated evidence.
