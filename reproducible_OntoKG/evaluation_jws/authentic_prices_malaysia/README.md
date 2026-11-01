# Malaysia authentic-price recovery — 17 October 2026

## Obtained, not overstated

The [Maybank investor-relations historical-price page](https://maybank.listedcompany.com/historical_price.html?date_start=20260301&date_end=20260529) successfully returned its public month-filtered table and CSV through ordinary browser controls. The response contains 61 daily OHLC/volume rows for 2 March–29 May 2026. All 30 existing post-report company dates match the issuer-published Close values exactly. Two additional baseline observations are available: 31 March Close 11.360 and 1 April Close 11.660 MYR. The first post-date close is 2 April 11.460; final 14 May close is 11.180.

These are **issuer-IR republished prices, not exchange-original authenticated raw closes**. The CSV export has `unadjusted=0`; neither the viewed table nor CSV explains the adjustment convention. Consequently the ledger authenticates what the issuer IR service published, but not the raw-price or dividend-adjustment basis. Corporate-action treatment must be established before a compatible benchmark comparison. No silent change is made to original workbooks or graphs.

`results.json` records URLs, exact dates, CSV line/field locators, values, retrieval date, downloaded-file SHA256 and all original/new comparisons. The downloaded CSV remains a local research capture; public download does not establish a redistribution licence. Its hash establishes capture integrity, not a publisher signature. Source URL: [published CSV](https://maybank.listedcompany.com/historical_price_download.html?date_start=20260302&date_end=20260529&unadjusted=0).

## Benchmark remains unresolved

The [Bursa market statistics route](https://www.bursamalaysia.com/market_information/market_statistic/market_statistics) was inaccessible in the research tool. The [official LSEG index resource page](https://www.lseg.com/en/ftse-russell/indices/bursa-malaysia) provides methodology, monthly factsheets and client/sales routes, but no requested daily levels were recovered. Monthly factsheets cannot substitute for the exact trade dates. No account, purchase, CAPTCHA solution or access-control bypass was attempted.

[Bernama reports](https://bernama.com/bm/news.php?id=2557055) 14 May spot KLCI 1,745.58, explicitly separately from the futures contracts. This is a secondary news lead, **not** an exchange/index-administrator replacement. It is not combined with the old interpolated/proxy series. Accepted primary benchmark coverage stays zero, and the empirical R1 classification remains incomplete.

The company-only endpoint calculations in `results.json` are descriptive **as-published** returns. They do not establish market-adjusted return, CAR, a causal announcement effect or initial earnings reaction. 1 April is the annual-report document date, not a verified publication timestamp. 31 March is an available preceding-date close; whether it precedes the first earnings announcement remains unverified. March volumes are available but no post hoc volume-baseline claim is introduced.

## Reproduce

Run `python docs/jws_malaysia_authentic_prices.py` to regenerate the ledger from the captured CSV and existing read-only cohort report. Run the same command with `--test` for four integrity/endpoint/missing-date/no-benchmark-promotion tests. No network replay is performed by this script: future re-downloads must be separately versioned and reviewed, not silently overwrite the capture.
