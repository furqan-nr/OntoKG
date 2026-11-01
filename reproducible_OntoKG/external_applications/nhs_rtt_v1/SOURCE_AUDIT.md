# Independent source audit

Recorded 18 October 2026. No RDF/checker imports are used.

The frozen protocol maps `Total` to the actual Treatment Function Name, code `C_999`. The all-specialty workbook rows reside in both `Provider` and `IS Provider`, not a Total-named sheet. The same-provider/month/commissioner key is unique across selected CSV rows; no provider aggregate commissioner row is added to underlying commissioner totals. NONC rows are excluded.

Reconciliation tolerance was fixed in source code before comparison at 1e-12 ratio units for stored Excel floating percentages. Count and weekly-cell comparison requires exact equality. Display is one decimal percent; threshold classification always uses exact integer cross-products, never rounded display.

```json
{
  "all_csv_records": 177770,
  "selected_csv_records": 12786,
  "excluded_NONC_records": 109,
  "providers": 532,
  "workbook_providers": 533,
  "csv_only_providers": [],
  "workbook_only_providers": [
    "D1V5N"
  ],
  "classifications": {
    "below_92_percent": 441,
    "at_least_92_percent": 91
  },
  "reconciliation_mismatches": []
}
```

All raw CSV row IDs, commissioner codes, weekly columns, workbook sheet/row/cell references, file sizes, SHA-256 hashes, archive members and original URLs are retained in `source_oracle.json`. Original binaries were not modified. Missing/invalid counts remain unavailable; zero denominators remain not applicable, rather than failures or success.

The workbook-only provider D1V5N (ACES BOLTON), `IS Provider` row 6758, has DH6758=0, DI6758=0 and DJ6758=0; no Part_2/Total row exists for it in the CSV. It remains a separate undefined publisher-only record, not a zero-filled CSV observation or an inferred missing submission.

The workbook is a publisher-derived cross-format check of the same reporting collection, not an independently collected ground truth. No patient-level information, practitioner validation, deployment benefit, natural explanation defects or causal benefit is established.
