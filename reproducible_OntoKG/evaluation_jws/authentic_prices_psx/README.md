# PSX authentic-price acquisition ledger

Status: acquisition incomplete; zero authenticated daily intervals. No missing value is replaced with zero, interpolation, a proxy, an opening price or a secondary-news quotation.

## Indexed primary-document leads

| Series | Trade date | Indexed value | Evidence |
|---|---|---:|---|
| FFC | 2026-01-29 | 597.10 | [SECP document](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-29-2026/?refresh=6a336fd2d98241781755858&wpdmdl=63558) — Report header 29-Jan-26; Volume Leaders / Fauji Fert / Close Price; repeated Top 10 Index Drivers |
| FFC | 2026-03-13 | 501.02 | [SECP document](https://www.secp.gov.pk/document/daily-stock-market-report-dated-march-13-2026/?refresh=69f1bc4ea41951777450062&wpdmdl=64172) — Report header 13-Mar-26; Top 10 Index Drivers / Fauji FertXD / Close Price |
| KSE100 | 2026-01-28 | 188380.39 | [SECP document](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-29-2026/?refresh=6a336fd2d98241781755858&wpdmdl=63558) — Stock Market Summary / Index / explicitly labelled 28-Jan-26 column |
| KSE100 | 2026-01-29 | 182338.12 | [SECP document](https://www.secp.gov.pk/document/daily-stock-market-report-dated-january-29-2026/?refresh=6a336fd2d98241781755858&wpdmdl=63558) — Stock Market Summary / Index / explicitly labelled 29-Jan-26 column |
| KSE100 | 2026-03-13 | 153866.17 | [SECP document](https://www.secp.gov.pk/document/daily-stock-market-report-dated-march-13-2026/?refresh=69f1bc4ea41951777450062&wpdmdl=64172) — Stock Market Summary / Index / explicitly labelled 13-Mar-26 column |
| KSE100PR | 2026-01-29 | 57275.40 | [PSX document](https://dps.psx.com.pk/download/quote/2026-01-29.pdf) — QUOTATIONS / KSE100PR / current close; PDF date/header not visually verified |

These are search-indexed primary-document leads, NOT downloaded/visually authenticated PDFs. The document hash is explicitly null. SECP is the regulator publisher; its report uses PSX market data. Report-header date and explicitly labelled prior-session column are kept separate from publication date.

## Access and rights

The public PSX historical page was reachable, but its terms prohibit automated collection/caching and redistribution without written permission. No raw PSX data are cached or distributed here. SECP direct downloads returned an HTTP403 challenge; no challenge bypass was attempted. A publicly indexed exchange quotation link is recorded as a retrieval lead only. Before packaging market data, obtain a permissible-use basis or an appropriately licensed research feed. No account, payment or message to a third party was initiated.

## Fail-closed comparison

FFC closes are price-only, whereas KSE100 is a total-return benchmark. The executable gate rejects this substitution regardless of numerical/source availability. KSE100PR is the appropriate price-return candidate, but matching authenticated endpoints and all daily values remain absent. Neither an underperformance conclusion nor an authenticated event-reaction result is emitted. A January29 opening price is not substituted for the January28 baseline close.

## Reproduction and next acquisition

Run `docs/jws_psx_authentic_prices.py`. Six synthetic controls exercise incompatible bases, missing endpoints, unverified leads, zero baselines and exact arithmetic. The required-date inventory comes from the existing FFC cohort and is frozen in JSON. Obtain permitted original quotation PDFs or a licensed historical series for every listed FFC/KSE100PR date; verify PDF header, symbol, close field, adjustment convention and source bytes before admitting values. A verified endpoint pair may support endpoint-only descriptive price returns, not daily CAR or a pre-event volume model.
