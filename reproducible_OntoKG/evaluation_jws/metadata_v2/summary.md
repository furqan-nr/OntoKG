# Independent metadata consistency checks

Actual positive oracle cases; metadata consistency, not source authenticity. Corrected and archived cohorts are paired, overlapping datasets.

| Cohort | Positive cases | All applicable metadata consistent | Absent/ambiguous | Mismatch |
|---|---:|---:|---:|---:|
| psx_curated | 9 | 0 | 9 | 0 |
| msx_curated | 2 | 0 | 2 | 0 |
| idx_curated | 10 | 0 | 10 | 0 |
| idx_scaled_archived | 43 | 0 | 43 | 0 |
| demo_idx_financial_v2 | 9 | 8 | 0 | 1 |
| demo_idx_scaled_financial_v2 | 42 | 22 | 0 | 20 |
| demo_msx_financial_v2 | 2 | 2 | 0 | 0 |
| demo_psx_financial_v2 | 5 | 5 | 0 | 0 |

## Actual temporal gaps

Corrected curated IDX contains a positive R1 case for TOWR whose growth-period report date is 2026-03-18 while its return window is anchored at 2026-03-25. This is a numerical positive with an unresolved report-to-window linkage. The corrected scaled cohort contains 20 positive R1 cases whose recorded report dates differ from the recent-analysis window anchor. These remain numerical positives, but do not satisfy the strict report-anchored metadata policy. They must not be counted as validated report-event findings. No dates are silently rewritten to force agreement.

Corrected curated cohorts have 16 numerical positives, 15 of which satisfy all applicable declared-metadata checks. The corrected scaled cohort has 42 numerical positives, 22 of which satisfy those checks; the other 20 are R1 anchor mismatches. These cohorts overlap and their counts are not an independent sample-size total.

Unit labels must equal the role contract (percent, ratio, coefficient). Return comparator currency contexts must agree. R1 requires actual period report date equal to the company window anchor, period end no later than report, and window start on/after anchor. R4 requires the observed event anchor within window endpoints and an explicit finding-to-window link matching the fixture witness. Missing or ambiguous values are unknown, never a pass. R4 checks only passing branch units; an unused nonpassing branch cannot invalidate a sufficient OR witness.

These conditions validate declarations. They cannot establish that a registered report date is authentic, that a same-day market observation followed announcement time, or that monetary extraction was correct. Company currency context is not the measurement unit of percentage returns. Archived inputs lacking declarations remain unknown.

Five synthetic metadata controls cover a valid fixture, wrong unit, wrong currency, wrong report anchor and absent report date. All expected responses must pass. Controls are not natural findings or new participants.

Reproduce: docs/jws_metadata_v2.py after expanded-evaluation results are finalized.
