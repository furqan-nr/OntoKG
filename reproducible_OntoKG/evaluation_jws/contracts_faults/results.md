# CQ contract controlled faults

same-data validation-policy ablation; not a head-to-head provenance-system benchmark

| Case | Existing SHACL conforms | Contract result | Snapshot changed |
|---|---|---|---|
| positive_control | True | finding=sufficient; bundle=sufficient; source=True | False |
| wrong_valid_company | True | finding=incomplete; bundle=incomplete_bundle; source=False | True |
| wrong_valid_window | True | finding=incomplete; bundle=incomplete_bundle; source=False | True |
| missing_deciding_comparator | True | finding=incomplete; bundle=incomplete_bundle; source=False | True |
| missing_bundle_only_comparator | True | finding=sufficient; bundle=incomplete_bundle; source=False | True |
| wrong_metric_same_number | True | finding=incomplete; bundle=incomplete_bundle; source=False | True |
| plausible_numeric_predicate_preserved | True | finding=sufficient; bundle=sufficient; source=True | True |
| strict_threshold_equal_sector | True | finding=predicate_false; bundle=predicate_false; source=False | True |
| cq3_or_only_witness | True | finding=predicate_false; bundle=predicate_false; source=False | True |
| missing_all_evidence | True | finding=incomplete; bundle=incomplete_bundle; source=False | True |
| incoherent_source_identifier_overlay | True | finding=sufficient; bundle=sufficient; source=False | True |
| wrong_valid_source_overlay | True | finding=sufficient; bundle=sufficient; source=True | True |
| broken_source_path_overlay | True | finding=sufficient; bundle=sufficient; source=False | True |
| r4_volume_only_sufficient | True | finding=sufficient; bundle=sufficient; source=True | True |

Condition replay, actual-bundle sufficiency and source-path completeness are separate policies. The source substitution and plausible numerical corruption remain undetected by the semantic policies. Two separate controls establish ordinary positive acceptance and sufficiency of the volume-only R4 OR branch. These deliberately selected cases are not an estimate of natural-error detection rates.

## Intervention definitions

- `positive_control`: Unmodified positive finding.
- `wrong_valid_company`: Observation points to another existing Company.
- `wrong_valid_window`: Company return and comparators now use different valid windows.
- `missing_deciding_comparator`: Remove benchmark from both finding and bundle to preserve their agreement.
- `missing_bundle_only_comparator`: Keep finding support intact but remove the comparator from the actual explanation bundle.
- `wrong_metric_same_number`: Replace the metric label while preserving its numeric value.
- `plausible_numeric_predicate_preserved`: A tiny value corruption retains the true condition; no independent source recomputation is claimed.
- `strict_threshold_equal_sector`: Strict company > sector must reject equality.
- `cq3_or_only_witness`: Company exceeds exactly one comparator: would pass an OR query but fails the intended AND contract.
- `missing_all_evidence`: Expect explicit insufficient evidence, never a confirmed explanation.
- `incoherent_source_identifier_overlay`: Substitute only the existing source edge while retaining the original declared source identifier; internal mismatch is detectable.
- `wrong_valid_source_overlay`: Existing source and its matching declared identifier substituted together; internally coherent false attribution cannot be authenticated by path checks.
- `broken_source_path_overlay`: Remove primary-source edges from company-return dependency cells. Numerical sufficiency may remain while source sufficiency fails.
- `r4_volume_only_sufficient`: OR predicate has a passing volume witness; CAR is unnecessary to establish this branch.

The RDF-evidence ablation preserves the same triples and provenance but performs no semantic contract checks. Its acceptance is a defined policy, not a claim about another provenance implementation.

Artifact hash drift is separate from evaluating a stored result. No claim that a positive witness reveals an edited query.

Snapshot differences detect interventions by construction. Neither source existence nor a known snapshot authenticates upstream sources. Positive findings only; no recall claim.

Currency/unit corruption is untestable because the deciding observations lack explicit metadata.
