Malaysia Bursa portability data package for OntoKG-EQ
Updated: 2026-06-12

Purpose
- Mirrors the nine PSX spreadsheet structures with a small Bursa Malaysia portability slice.
- Intended for ontology/KG portability validation, SHACL/SPARQL testing, and evidence-route checking.
- Not a full Bursa Malaysia market database, investment dataset, trading recommendation, or licensed benchmark reconstruction.

Shortlisted companies
- Financial Services: MAYBANK (Malayan Banking Berhad, 1155), CIMB (CIMB Group Holdings Berhad, 1023).
- Telecommunications & Media: TM (Telekom Malaysia Berhad, 4863), MAXIS (Maxis Berhad, 6012).

Updates applied in this version
1. Normalized boolean flags to TRUE/FALSE-compatible values in the scope and announcement sheets.
2. Normalized query-case status values to FINAL_READY.
3. Filled comparator anchor_date values so comparator observations have explicit analysis-window anchors.
4. Added missing provenance records for:
   - MY_SRC_COMP_FINANCIAL_SERVICES
   - MY_SRC_COMP_TELECOMMUNICATIONS_AND_MEDIA
5. Converted retrieval_date fields to ISO date-time strings (2026-06-11T00:00:00) for RDF-safe materialization.

Important caveats
- Company fundamentals are public-summary/annual-report-level values in RM million. Rows marked with notes should be verified against full annual statements before audit-grade empirical use.
- Market windows use public delayed historical price rows from StockAnalysis pages cited in provenance. Replace with official/licensed Bursa historical data if the paper makes empirical market claims.
- The FBM KLCI comparator rows are transparent demonstrator-proxy rows, not a licensed full historical index feed. Source and construction-rule columns state this explicitly.
- FX rows use BNM USD/MYR reference source context. Rebuild from Data.gov.my CSV before final repository release if raw exact rates are required.

Files
1. MY_01_scope_and_selection_final.xlsx
2. MY_02_company_master_final.xlsx
3. MY_03_fundamentals_final.xlsx
4. MY_04_market_windows_corrected.xlsx
5. MY_05_comparators_corrected.xlsx
6. MY_06_bnm_fx_final.xlsx
7. MY_07_announcements_disclosures_final.xlsx
8. MY_08_provenance_final.xlsx
9. MY_09_query_cases_corrected.xlsx
