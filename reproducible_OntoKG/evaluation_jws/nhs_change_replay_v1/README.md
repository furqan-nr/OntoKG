# Bounded NHS requirement-change replay

Only official_92_ge reproduces the published NHS standard. Other policies are explicitly counterfactual.

| Policy | Positive | False | Unknown | Changed provider IDs from official |
|---|---:|---:|---:|---:|
| official_92_ge | 91 | 441 | 1 | 0 |
| counterfactual_90_ge | 118 | 414 | 1 | 27 |
| counterfactual_90_gt | 117 | 415 | 1 | 26 |
| counterfactual_92_gt | 91 | 441 | 1 | 0 |
| counterfactual_95_ge | 67 | 465 | 1 | 24 |
| counterfactual_95_gt | 67 | 465 | 1 | 24 |

All 533 existing frames agree by provider identity, status and readiness with the integer oracle and independent parameterized SPARQL baseline for all six policies. Exact affected-provider lists appear in results.json.

14 separately constructed controls per policy execute 252 actual SHACL pool validations. The delivery-omission control was additionally requested before execution. Cohort results use provider-bound prepared SPARQL, not SHACL validation. Both comparators centralize policy parameters; no duplicated-edit disadvantage is imposed.

Official-policy rollback restores every status/readiness value in every interpreter pool and the direct baseline. Frozen inputs, original outputs, configurations and implementation files retain their recorded hashes. No core-interpreter edit was required.

Here rollback means deterministic re-execution of the original policy over unchanged inputs. It is not an evaluated stateful deployment rollback, transaction or operational recovery procedure.

These results establish bounded change-conformance and affected-result traceability, not general maintainability, independent production use, objective human benefit or superiority. Repeated policies and pools are not independent samples.
