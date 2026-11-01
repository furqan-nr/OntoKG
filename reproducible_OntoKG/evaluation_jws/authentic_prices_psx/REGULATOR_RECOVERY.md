# Original SECP PDF recovery, 17 October 2026

This is a subsequent recovery stage, not a rewrite of the earlier indexed-only ledger. Four original one-page SECP daily reports were downloaded through the public trading-data archive and the actual attached-file links. Renderings were visually inspected, including table headings, trade-date columns and close-price fields. The executable ledger records source-file SHA-256 hashes and exact table locators. Article publication dates are not substituted for trading dates.

Eight unique observations are admitted: six KSE100 index levels (27–30 January and 12–13 March) and two FFC closes (597.10 on 29 January and 501.02 on 13 March). Repeated index values in adjacent reports agree. The March FFC row explicitly carries an XD marker.

The FFC January 28 baseline is **not** recovered: FFC is absent from that report's selected spot-price tables. The January 30 report also omits its spot close. Open-interest values and opening prices are not substitute closes.

The two authentic FFC endpoints support only a descriptive unadjusted price change, not total return or an announcement effect. KSE100 remains a total-return series; its authentication does not make it comparable to FFC price-only returns. The comparison gate continues to refuse this mixed-basis comparison. A price-return KSE100PR series, the missing company baseline, daily observations and corporate-action checks are still needed for the proposed report-aligned study.

Run `docs/jws_psx_regulator_recovery.py` to verify retained original source bytes, duplicate agreement, missing-baseline refusal, basis refusal and endpoint arithmetic. Source PDFs/renderings are local research-review captures, not a redistribution licence. No restricted exchange scraping, challenge bypass, payment or external communication was performed.

Reviewed reports: [28 January](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-28-2026/), [29 January](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-29-2026/), [30 January](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-30-2026/), [13 March](https://www.secp.gov.pk/document/daily-stock-market-report-dated-march-13-2026/).
