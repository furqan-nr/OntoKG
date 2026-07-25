# Correction record — 2026-06-28

## Fixed metadata

| Item | Old value / issue | Corrected value | Reason |
|---|---|---|---|
| CQ3 sector labels | TOWR = `Telecommunications Infrastructure`, ISAT = `Telecommunications` | Both = `Telecommunications` under `CQ3 normalized peer-basket sector` | CQ3 requires a multi-company telecom peer basket. The normalization is explicitly labeled as analysis-specific, so it does not silently overwrite a source taxonomy. |
| TOWR FY2025 `yoy_profit_growth_pct` | `2.99` | `10.28` | The field name denotes year-over-year profit growth. Net income attributable to parent was Rp3,678.3bn (2025) vs Rp3,335.4bn (2024), yielding 10.28%. `2.99%` is EPS growth from the rounded EPS values and is not semantically appropriate for this column. |
| TOWR FY2025 EPS | `69.00` | `69.00` (retained) | The official FY2025 company presentation reports 2025 financial performance consistent with the retained EPS basis; the correction is to the growth metric's meaning, not to the EPS field. |

## Still deliberately blocked

No historical price, FX, or index values have been fabricated. The six `raw_downloads/*_history_source.csv` files are placeholders. The build becomes usable only after actual rows are acquired and the strict builder reports four `COMPLETE` cases.

## Primary evidence used for the TOWR correction

- PT Sarana Menara Nusantara Tbk, *2025 Results Presentation*, official investor material, 2026. It reports consolidated net income attributable to parent of Rp3,678.3bn in 2025 and Rp3,335.4bn in 2024.
- The linked IDX financial statement remains the official announcement/disclosure evidence for the event anchor dated 2026-03-18.
