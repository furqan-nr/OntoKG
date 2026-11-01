# Temporal resolution v1

No historical or financial-v2 date is rewritten. Numerical positives remain numerical positives; a quarantined case is excluded from report-event validation.

| Corrected cohort | Numerical positives | Decision counts | Authenticated first-earnings events |
|---|---:|---|---:|
| demo_idx_financial_v2 | 9 | {'not_a_report_event_claim': 8, 'quarantined_temporal_mismatch': 1} | 0 |
| demo_idx_scaled_financial_v2 | 42 | {'not_a_report_event_claim': 22, 'quarantined_non_report_analysis_window': 20} | 0 |
| demo_msx_financial_v2 | 2 | {'declared_alignment_only_not_authenticated': 1, 'official_annual_report_announcement_date_matched': 1} | 0 |
| demo_psx_financial_v2 | 5 | {'not_a_report_event_claim': 4, 'official_financial_results_document_date_matched': 1} | 0 |

## Why dates cannot simply be matched

The scaled input explicitly calls its market anchors recent_analysis_window. Its latest fundamentals report_date equals fiscal year-end (2025-12-31); this does not authenticate a publication date. All 20 positive scaled R1 cases are quarantined as non-report analysis windows, regardless of whether an equality check could be made to pass. The 22 remaining scaled numerical positives are non-R1 classifications; this is not 22 authenticated report events.

Curated TOWR has report date 2026-03-18 and window anchor 2026-03-25. Its numerical R1 positive is quarantined. No primary publication timestamp was authenticated in this audit, and neither date is substituted for the other.

Other aligned declarations remain declared-only, not externally authenticated. A delayed window may be scientifically meaningful but is not the strict release-anchored claim. Recent-window R2/R3 comparisons may be reported descriptively without claiming a report reaction.

## Source reconnaissance (2026-10-16)

[ANTAM official annual report listing](https://antam.com/id/company-report/annual-report) was indexed with “Laporan Tahunan 2025 (30 April 2026)”; the direct text retrieval did not expose that listing. This is a bounded source lead, not an authenticated first-earnings announcement and not used to alter any date. It illustrates the need to distinguish fiscal end, financial-statement authorization, earnings publication, and annual-report upload. TOWR official financial-report URL was inaccessible through the retrieval tool; third-party March 18/March 25 listings were not promoted to primary-source authentication.

## Required recovery procedure

For each quarantined R1 case obtain the official earnings release or exchange disclosure with publication date/time and timezone; identify the exact accounting period/scope; obtain company and benchmark close endpoints covering the predeclared same-calendar horizon; reconstruct returns on identical observed intervals; document whether a same-day close follows disclosure. Missing horizon coverage stays incomplete. Do not infer publication from fiscal end, auditor signature, search snippet, retrieval date, or annual-report upload alone. Current data do not support an authenticated full-horizon recomputation, so no synthetic replacement result is claimed.

The overlay is a separate exclusion ledger, not a replacement ontology or modified production finding graph. Reproduce with docs/jws_temporal_resolution.py after metadata_v2. Five synthetic controls assert strict quarantine and ensure recent windows cannot pass merely through matching date declarations.

## Bounded official date matches

[Maybank issuer announcement](https://maybank.listedcompany.com/news.html/id/2605866) explicitly records 01 Apr 2026 for the FY2025 annual report and CG report, reference DCS-01042026-00004. This authenticates the recorded annual-report announcement date and matches the window anchor; observations begin April 2. It does not establish first disclosure of FY2025 earnings, precise upload time, or source truth of market prices.

[FFC exchange-hosted issuer disclosure](https://dps.psx.com.pk/download/document/269389.pdf), page 1, is dated January 29 2026 and reports the FY2025 financial-results board meeting on that date. It matches the PSX R1 anchor; observations begin January 30. This authenticates the issuer document date, not an independently logged exchange upload timestamp or proof of first publication. Both distinctions are preserved in JSON and RDF. Maxis official annual report contains an AGM notice dated April16 2026, but a notice date is not automatically an annual-report publication date; its R1 remains declared-only.
