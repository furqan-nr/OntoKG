# PPL annual-source completion (2026-10-17)

The six pending PPL facts in `annual_source_repair/results.json` are now
visually verified against the complete issuer-authored results letter hosted
by the exchange: https://www.psx.com.pk/psx/files-attachment/?file=259574.pdf .
The older report is retained as historical evidence; consume this overlay
explicitly to supersede its six pending PPL statuses.

Downloaded copy: 23,576,826 bytes; nine pages; SHA-256
`12b2e2ecdb660e7b068d56d763d5c3a8adb0c7a6a983e15a67fdf983e0f301c5`.
The PDF header, end marker, exact byte count, hash and clean `pdfinfo` parse are
checked. Pages 1--3 were rendered and inspected. Page 1 is the issuer letter,
dated September 19, 2025; page 3 is the **unconsolidated** company profit or
loss statement for the year ended June 30, 2025, with 2024 comparative column.
Its monetary unit is rupees in thousand; EPS is rupees per share.

| Fact | FY2025 | FY2024 comparative |
|---|---:|---:|
| Revenue from contracts with customers, thousand PKR | 242,516,363 | 288,797,413 |
| Profit after taxation, thousand PKR | 92,027,450 | 114,309,077 |
| Basic and diluted EPS, PKR/share | 33.82 | 42.01 |

Four monetary workbook cells require a factor of 1,000,000 to match their
declared thousand-PKR unit; both EPS cells match directly. Revenue and profit
growth remain unchanged because the common scale cancels. The bounded
OGDC/PPL set therefore moves from six to twelve source-eligible annual facts,
not twelve independent companies or representative market-wide coverage.

The issuer annual-report URL returned HTTP 403 and was not used. Earlier
partial downloads are not evidence for these statuses. This successful
exchange attachment is a complete public issuer document, not a market-data
feed. Local evidence copies are retained for auditing, but source
redistribution rights have not been established.

No statement date is promoted to an authenticated first-publication timestamp;
the 2024 numbers are verified as comparative disclosures only. No prices,
benchmarks, event timings or market-reaction findings are authenticated here.
Original graphs, workbook and earlier results remain untouched. `repairs.ttl`
is a separate provenance overlay; it does not silently alter inference inputs.

Reproduce using the repository Python dependencies and `pdfinfo` on PATH:

```
python docs/jws_ppl_source_completion.py
python docs/jws_ppl_source_completion.py --self-test
```

`results.json` records cell addresses, source page, period, scope, normalized
values, growth checks and limitations. Ten tests cover six agreements, period,
scope and scale mutations, and complete-source validation.
