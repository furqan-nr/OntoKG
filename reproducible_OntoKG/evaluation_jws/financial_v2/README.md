# Financial v2: separate corrected graphs

Independent arithmetic over existing workbook inputs; no new independent dataset and no source-truth certification. Historical graphs and inputs remain unchanged.

| Market | Recomputed | Incomplete | Changed values | Daily-return checks | Mismatches |
|---|---:|---:|---:|---:|---:|
| psx | 23 | 15 | 25 | 241 | 0 |
| msx | 24 | 2 | 14 | 232 | 0 |
| idx | 38 | 0 | 24 | 398 | 0 |
| idx_scaled | 319 | 0 | 189 | 4366 | 0 |

## Definitions and limits

Company, sector and benchmark returns use identical company close-date endpoints and compound consecutive price changes. This deliberately excludes any first-row supplied return whose prior close is absent. Missing comparator endpoints cause incomplete metrics instead of silently intersecting dates. Observed-date matching is not trading-calendar completeness. Market-adjusted event CAR subtracts the supplied benchmark return on every event date; missing inputs cause incomplete metrics. These are price returns, not verified adjusted total returns. FX correlations use identical date intervals. Volume ratios include legitimate zeros and explicitly retain the post-report baseline dates and overlap flag. This baseline is descriptive and can overlap the event; no significance claim is justified.

Growth is independently recomputed only where same-field current and prior-year PAT inputs exist. Otherwise it remains clearly marked as a supplied workbook metric. Absolute prior PAT is the declared loss-to-profit convention. Accounting scope and uniform scaling require independent source review. Graphs have explicit unit declarations, computation definitions, cell dependencies, actual workbook window anchors and source-register identity paths. These declarations make assumptions inspectable, not externally verified. Market currency context does not mean percentage returns are currency-valued. Missing report dates are never inferred from fiscal year-end.

## Official-source spot check

See source_spot_checks.md for bounded original-document verification. PSX ENGROH supplied PAT magnitudes conflict with the column unit: no silent scaling correction was applied. Workbook record labels such as verified are not treated as independent verification.
