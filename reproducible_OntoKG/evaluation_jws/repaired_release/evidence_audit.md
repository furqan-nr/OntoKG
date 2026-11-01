# Final-graph evidence audit

Run: `python docs/jws_evidence_audit.py`. No production graphs or shapes are changed.

| Market | Findings | Bundles | SHACL conforms | SHACL results | Dependency issues |
|---|---:|---:|---|---:|---:|
| psx | 9 | 14 | True | 0 | 0 |
| msx | 2 | 7 | True | 0 | 0 |
| idx | 10 | 15 | True | 0 | 0 |

| Market | Unique deciding observations | Direct source/derivedFrom link | Temporal context |
|---|---:|---:|---:|
| psx | 19 | 0 | 19 |
| msx | 6 | 0 | 6 |
| idx | 20 | 0 | 20 |

Direct-link counts test hasEvidenceSource, supportedByEvidenceItem, hasProvenanceRecord and incoming/outgoing derivedFrom; they do not establish complete PROV dependency paths or deny the existence of graph-wide sources. An announcement source in the same bundle does not itself identify the raw rows used to compute every deciding financial metric.

## Controlled final-graph faults (PSX)

Each intervention starts from the same unmodified graph. Existing evidence and provenance remain. The dependency column measures newly introduced issues, relative to pre-existing issues.

| Intervention | Existing SHACL detects | Additional dependency audit detects | Snapshot oracle detects |
|---|---|---|---|
| well_typed_numeric_predicate_flip | False | True | True |
| well_typed_numeric_predicate_preserved | False | False | True |
| wrong_existing_valid_window | False | True | True |
| wrong_existing_valid_source | False | False | True |
| missing_one_bundle_dependency | False | True | True |

## Interpretation and limits

This is a controlled ablation of validation policies on the same RDF graph with provenance retained. It is not a comparison with an independently implemented provenance system, and it does not demonstrate novelty or superiority over RDF provenance generally.

The additional imperative audit is newly implemented evaluation code, not a capability of the released SHACL shapes or the original pipeline. It checks the consistency of stored finding witnesses, rule predicates and generated bundles. Existing shapes do not explicitly target AnalyticalFinding or require every deciding observation in a bundle.

The snapshot oracle knows the pre-intervention triples, so it detects changed values and source assignments by construction. It is not an independent raw-data correctness test. A plausible wrong value that leaves a rule predicate true can escape both SHACL and dependency checks. A wrong but well-formed source association cannot be verified without a trusted mapping or external source evidence.

The original R4 rule selected on abnormal volume but constructed only the cumulative-abnormal-return support. Original-release volume-triggered results with |CAR| < 2 therefore lacked explicit support for the deciding volume condition. The repaired rule includes volume support; the same checker accepts a matching volume witness when it satisfies the threshold.

This audit covers explicit support of materialized positive findings, not false negatives, all possible CQ answers, raw-price calculations, source authenticity, or multi-witness provenance. Multiple witnesses require manual review. Timing is one local run and is not a performance benchmark. See JSON for hashes, versions, individual issues and times.
