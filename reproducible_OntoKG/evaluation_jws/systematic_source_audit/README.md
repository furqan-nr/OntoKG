# Frozen source-dependency coverage

This is an executed coverage audit, not a completed source-authenticated financial cohort.

Selected cases: 52 across 29 strata. Unique recorded input facts: 2357. Qualified source-value facts: 4. Fully source-qualified findings: 0.

| Dependency status | Unique facts |
|---|---:|
| declared_proxy_unreviewed | 46 |
| exact_match_after_scale_correction | 4 |
| issuer_republished_unknown_adjustment_basis | 30 |
| recorded_lineage_only_unreviewed | 2271 |
| regulator_original_value_match_basis_not_transferred_to_workbook | 2 |
| reviewed_price_does_not_match_workbook_value | 2 |
| rounded_narrative_match_after_scale_correction | 2 |

## Exact primary-review disagreements

These are pre-existing workbook values compared with previously reviewed original regulator observations; no substitution was performed.

- PSX data v4\05_comparators_corrected.xlsx C31 (2026-03-12 00:00:00): workbook 157496.1; reviewed original 154421.43. Full date-column, page, source URL and document hash in results.json.
- PSX data v4\05_comparators_corrected.xlsx C32 (2026-03-13 00:00:00): workbook 157496.1; reviewed original 153866.17. Full date-column, page, source URL and document hash in results.json.

Four exact scale-qualified dependency facts are FFC PAT I4/I5 and OGDC PAT I6/I7. OGDC review depends on its separate source-repair evidence; financial-v2 graph source links are not automatically repaired. The six verified PPL annual facts are outside this particular frozen dependency selection and are not counted.


Coverage review of frozen selected cases, not 52 independently externally reviewed findings or a population accuracy rate.
Exact recorded lineage is not source authenticity; zero dependency cells do not establish source completeness.
All-recorded-dependency coverage is conservative, not a minimal AND/OR sufficiency proof.
Annual scale-corrected facts do not establish unreviewed monetary accuracy or compatible accounting scopes.
Price matching is numeric evidence only; original-workbook adjustment basis, benchmark compatibility, calendar completeness and publication-time semantics remain separate gates.
Exact workbook-cell identities are deduplicated. Different workbook copies are NOT automatically merged or counted as independent companies; apparent equal values are not an identity oracle.
No new internet source facts admitted in this bounded coverage integration; existing primary-source reviews are cited at fact level.
Annual review evidence may depend on a separate repair overlay. This coverage join does not update historical source associations in the financial graphs.

Reproduce: `python docs/jws_systematic_source_audit.py`. Run assertions with `--test`. No data or manuscript inputs are modified.
