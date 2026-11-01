# Disclosure-date-aligned cohort v1

Eight PSX/MSX candidates are retained: three numerical positives, five negatives, and zero incomplete post-close arithmetic cases. Missing disclosure closes and pre-event baselines are separately reported rather than treated as complete. Two official dates match the declared anchors. This is an arithmetic demonstration on workbook prices, not an authenticated earnings-event study. Original workbooks and graphs are unchanged.

| Company | Eligibility | R1 arithmetic | Dates / intervals | Company % | Benchmark % |
|---|---|---|---|---:|---:|
| ENGROH | excluded_no_verified_matching_disclosure_date | negative | 2026-02-27 to 2026-04-10 / 28 | 4.735755878233950025797891943686887300100 | -6.287000816424064975479014700333810993870 |
| FFC | official_date_match | positive | 2026-01-30 to 2026-03-13 / 29 | -14.87503610445656421496168680021068012305 | -14.48538828585869845492717259594420486791 |
| OGDC | excluded_wrong_period_february_anchor_no_september_2025_price_coverage | negative | 2026-02-24 to 2026-04-08 / 29 | 6.058059319956578071926322793010470287600 | -8.102895272472691552114453763868218214130 |
| PPL | excluded_wrong_period_february_anchor_no_september_2025_price_coverage | negative | 2026-02-16 to 2026-03-31 / 29 | -14.24120472543165000649097754121770738668 | -12.37194813611351275303446972579154441886 |
| MAYBANK | official_date_match | positive | 2026-04-02 to 2026-05-14 / 29 | -2.443280977312390924956369982547993019110 | 0.373421482546918602403878966334293824800 |
| CIMB | excluded_no_verified_matching_disclosure_date | negative | 2026-03-27 to 2026-05-08 / 29 | 2.987012987012987012987012987012987013300 | 0.013337580594734575657293196713091593300 |
| TM | excluded_no_verified_matching_disclosure_date | negative | 2026-04-20 to 2026-06-04 / 29 | 5.571428571428571428571428571428571428600 | -0.3951247369999433728026285477488787607800 |
| MAXIS | excluded_no_verified_matching_disclosure_date | positive | 2026-04-17 to 2026-06-03 / 29 | -6.849315068493150684931506849315068493110 | 0.071904898106645258134833264228739144000 |

## What is and is not established

[FFC official issuer letter](https://dps.psx.com.pk/download/document/269389.pdf), p. 1, dated 29 January 2026, supports document-date alignment, not first exchange publication time. [Maybank official announcement](https://maybank.listedcompany.com/news.html/id/2605866) records 1 April 2026, reference DCS-01042026-00004, for the FY2025 annual report and CG report. This is not authenticated first earnings disclosure. Maxis remains excluded: an AGM notice date alone is not publication proof. OGDC/PPL September 2025 annual dates do not match February 2026 market windows; available company rows do not cover September. Other excluded companies are preserved rather than silently omitted.

Both matched cases have 30 observed post-disclosure closes and 29 shared intervals. The calculation starts at the first observed post-disclosure close and excludes the initial reaction. All intermediate company dates must exist in the benchmark; missing dates are not intersected away. Returns are reconstructed with 40-digit Decimal arithmetic, and interval products are checked independently against endpoint ratios. Raw monetary scaling cancels in same-scale growth, but accounting scope/source accuracy is not thereby authenticated.

PSX benchmark rows explicitly disclose interpolation and forward filling. MSX benchmark rows explicitly disclose a damped selected-universe proxy and request replacement with a licensed official FBM KLCI feed. Thus numerical R1 labels are illustrative and cannot be advertised as empirically authenticated market underperformance. Bounded official-site endpoint searches did not retrieve a primary-source pair; secondary news values were not substituted.

FFC has January 28/29 event rows but their close values are missing. Maybank has no pre-anchor prices. Neither supports a disclosure-close-to-first-post-close return or an independent pre-event volume estimation period. Missing values remain missing. No price/date is invented, no post-event baseline is relabelled pre-event, and no significance claim is made.

## Reproduction

Run `docs/jws_report_aligned_cohort.py` with openpyxl and rdflib available. Eight synthetic controls cover compounding, negative outcomes, missing growth, intermediate company/benchmark-date mismatch, inadequate endpoints and zero prices. JSON includes exact workbook cell addresses and SHA-256 hashes; RDF is a separate versioned cohort overlay. IDX temporal quarantine remains a separate evaluation, not included in the eight-company denominator.
