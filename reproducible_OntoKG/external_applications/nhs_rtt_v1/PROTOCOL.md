# Public-data RTT application protocol

Frozen selection and task specification, 18 October 2026, before inspection of
provider-row outcomes. This is a recorded analysis protocol, not a preregistration.
Public national context may already be known. The month is the latest complete
monthly release visible on the official page when sources were acquired.

## Task and scope

Use NHS England August 2026 aggregate referral-to-treatment (RTT) incomplete
pathways, all treatment functions, at provider level. Evaluate whether the
published-data share within 18 weeks is at least 92%, under the publisher's
indicator definition. This is an audit of a statistical screen and its evidence,
not clinical advice, legal-compliance assessment, hospital-quality ranking or
an estimate of unique patients. Pathways and people are not interchangeable.

The official user guidance, section '92% operational standard', says 'at least
92%'; its reproducibility section specifies the numerator as the sum of weekly
bands 0–1 through 17–18 weeks and denominator Total All. Exactly 18 weeks is
included in the numerator. Avoid percentage rounding by evaluating
`total > 0 AND 100 * within18 >= 92 * total` with exact integer/decimal arithmetic.

## Frozen sources

- Landing page: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2026-27/
- Original full CSV ZIP: https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/10/Full-CSV-data-file-Aug26-ZIP-3M-vjgRdG.zip
- Original provider workbook: https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/10/Incomplete-Provider-Aug26-XLSX-9M-vjgRdG.xlsx
- Indicator/scope guidance: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/
- Host terms: https://www.england.nhs.uk/terms-and-conditions-2/
- Licence: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

Original binaries were obtained through ordinary public browsing; no accounts,
private feeds, access-control bypass or patient records were used. Record byte
hashes and original archive member names. Keep originals immutable. Host terms
permit reuse of information under OGL subject to third-party/image/logo
exceptions. Do not redistribute logos or imply NHS endorsement. Retain the
source-attribution and licence URLs for any redistributed data/derived records.

## Population and missingness

1. Inspect and document actual schema before implementing field mappings.
2. Select every `Part_2` row with treatment-function `Total` and commissioner
   code other than `NONC`; aggregate counts by provider and reporting month.
   Do not mix treatment-function subtotals with the Total row or add aggregate
   commissioner rows twice. Preserve raw-row IDs and commissioner scope.
3. Compare that provider set with the provider workbook's all-specialty rows.
   Preserve unmatched/missing/estimated/zero-denominator records explicitly.
   Do not infer absence of a provider means a genuine missing submission without
   a publisher flag or documented roster. Do not add estimates into provider
   totals or compare a submitted-only total to an estimate-adjusted national total.
4. Genuine zero denominators are not missing counts but make this percentage
   undefined: record not-applicable separately, without labeling success/failure.
   Blank/suppressed/invalid count inputs remain unavailable. Never fill with zero.
5. Verify nonnegative integer counts, within18 <= total, and same provider/month
   across all roles. Do not drop inconvenient records based on their outcome.

## Independent checks and baseline

- Recompute counts and ratio from the CSV independently of the RDF checker and
  compare against the publisher workbook's reported provider totals, within18
  counts and percentage values, at its stored/displayed precision. Report any
  discrepancies; do not silently repair source data or adjust tolerance after seeing results.
- Use exact integer cross-products for the binary threshold oracle; use rational
  arithmetic or sufficient explicit precision for ratio/display reconciliation.
- Independently author an equivalent SHACL-SPARQL and explicit availability
  baseline, using the same records without calling checker expression or
  candidate-selection helpers. Expect and report parity, not superiority.
- Generate explanation bundles as this application's outputs, with deciding
  counts and complete recorded lineage to original source rows/columns. These
  are newly generated views of genuine records, not publisher-provided explanations.
- Optional omission/decoy controls must be separate controlled interventions,
  never described as natural source or explanation defects.

## Honest reuse and technical usefulness

The existing interpreter lacks multiplication. Preserve it and prior results.
If extending arithmetic, version the extension explicitly, document code/config
changes and validate exact multiplication, bounds and all inherited financial
semantics. Do not claim unchanged-engine cross-domain reuse.

Measure actual source/oracle/baseline agreements, eligibility/missingness,
traceable deciding evidence, graph/config/adapter size and descriptive execution
cost. Do not invent authoring-time savings, practitioner adoption, improved
human auditing or independent production deployment. Independent original data
and independent verification code are not independent human implementation or
collection. A clean complete dataset with no natural defects is a valid outcome.
