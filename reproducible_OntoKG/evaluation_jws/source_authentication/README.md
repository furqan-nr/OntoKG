# Bounded issuer-original source authentication

Executed 16 October 2026. This is an agent-assisted purposive source review, not a random audit, digital-signature validation, or full-dataset certification. It extends the previous exchange-hosted spot check to actual issuer-authored disclosures. Run `docs/jws_source_authentication.py` with openpyxl available to recheck the preserved workbook against the reviewed transcriptions and hash the evidence copies.

## Observed results: 16 checked workbook facts, four issuer documents

* Four exact value-and-unit matches: FY2025/FY2024 EPS for FFC and ENGROH.
* Four exact matches only after explicit scale correction: FFC FY2025/FY2024 turnover and profit. Workbook headings say thousand PKR but numbers require multiplication by 1,000,000 to reproduce the issuer's thousand-PKR values. Raw values are not authenticated as labelled.
* Two rounded matches after scale correction: ENGROH standalone PAT for FY2025/FY2024 agrees with the original narrative at million-PKR precision only. Exact thousands are not certified by this paragraph.
* Six source-period mismatches: OGDC and PPL FY2025 annual sales/PAT/EPS cells cite documents for the half-year ended December 2025. A valid official URL is not valid provenance for a different accounting period. These facts are quarantined from authenticated-source claims, not replaced with interim values.

FFC's original scan, PDF page 4 (Annexure A page 2), explicitly prints thousand-rupee turnover 432,410,443 / 373,536,920 and profit 73,564,267 / 64,731,439, with EPS 51.69 / 45.49. Rendered pages were visually inspected. This resolves the earlier inability to read the scan.

ENGROH PDF page 16 distinguishes standalone PAT/EPS from consolidated results and describes restructuring and impairment effects. The standalone values must not be relabelled as consolidated business-performance growth. The two values reported only to rounded million precision are not exact-thousand confirmations.

OGDC PDF page 1 identifies a half-year report dated 23 February 2026; PPL PDF page 1 identifies a half-year report dated 13 February 2026. Workbook rows instead label year ended 30 June 2025. Document dates alone cannot repair this period mismatch.

## Evidence and boundaries

`results.json` gives exact workbook addresses, workbook hash, source URLs, source-copy SHA256 hashes, inspected page locators, values, units, scopes and status counts. `evidence/` holds the inspected official copies and rendered page images for local review. Publisher rights remain with the issuers/exchange; these copies are research-review evidence, not a redistribution licence. Do not automatically include the full source PDFs in a public replication archive without checking permission; URL/hash/transcription metadata and retrieval instructions can be published separately.

Original workbooks and financial-v2 graphs were not overwritten. This audit does not authenticate all returns, FX, daily volumes, benchmarks, dates, MSX or IDX source facts. It introduces no fabricated replacement figures and makes no representative accuracy estimate.
