# Evidence-boundary diagnostics v1

This additive extension preserves the archived v1 checker, contracts, financial
graphs and historical reports. Run `docs/test_jws_boundary_contracts.py` for the
regressions and `docs/jws_boundary_benchmark.py` to regenerate `results.json`.
Dependencies are the existing root `requirements-jws.txt`; no downloads are needed
when the local `.jws_deps` environment is on the module path.

## Executed experiment

Twenty explicitly constructed synthetic sensor cases independently declare expected
ambient/support/delivered labels. Sixty pool evaluations compare the interpreter to
a separately authored, executed SHACL-SPARQL positive-witness constraint plus two
availability ASK queries. All 60 numeric labels agree with the explicit expectations
and comparator. These are diagnostics, not 60 independent empirical observations.
The comparator reconstructs all three pools independently from fixture RDF;
membership sets also agree with the interpreter on all diagnostics.
Metadata readiness is tested separately; the comparator does not evaluate readiness.
Its numeric lexical input subset is ordinary decimal strings used by these fixtures;
the interpreter additionally accepts finite Decimal scientific notation. Do not infer
equivalence for arbitrary RDF literals, SHACL shapes, SPARQL or expressions.

The JSON records exact versions, input/contract/checker hashes, pool memberships,
excluded observations, deciding witness IDs, assignment counts and a single-run
elapsed-time observation. Timings include SHACL engine setup; no controlled speedup
or general scalability result is claimed. Hashes identify local artifacts, not
authentication; graph hashes are not blank-node-canonical RDF signatures.

## Supported fragment and boundary semantics

Contracts specify RDF predicates/types, bounded focus paths, metric roles, shared
window bindings, unit declarations and OR-of-AND numeric comparisons. Arithmetic
is finite Decimal role values, constants, absolute value and exact addition.
Addition selects enough local precision for exact bounded decimal operands; absolute
value is context independent. Numeric representations, expression depth, role/branch
counts and assignment enumeration are bounded; unsupported constructs raise errors.
There is no arbitrary eval, negation, aggregation, unit conversion or source-truth
inference. Negative numeric values and false results are not mapped to missingness.

Ambient means all typed observations; support means only finding-declared support;
delivered means the intersection of actual bundle membership with support, provided
the explicitly linked bundle identifies exactly the finding entity. Bundle members
outside support are excluded and reported. Ambient observations never rescue delivery.
Observation membership is restricted but supporting RDF context (types/entity links)
is retained. Consequently this is **not a standalone RDF subgraph certificate**.

A single passing OR branch is sufficient. False requires a complete compatible
assignment for every branch and no passing assignment in any branch. Otherwise the
result is unknown. This is a declared finite closed-candidate diagnostic policy, not
open-world refutation, proof from absence, general Kleene logic or arbitrary negation.
Any passing witness may establish truth; metadata readiness separately requires at
least one such witness with all required unit declarations. For false, every branch
must have a complete unit-ready assignment. Units are declarations, not conversions.
Window disagreement excludes joint assignments; no temporal anchoring not encoded
in the configuration is inferred.

## Reuse and limits

`contracts/finance_boundary_v1.json` contains four financial predicate configurations;
`contracts/synthetic_sensor_boundary_v1.json` uses a different RDF vocabulary without
changing checker code. Regression tests execute all four financial predicates and a
wrong-window conjunction. Finance configurations use explicit finding-to-bundle and
entity-to-index links rather than silently choosing any ambient market index; an
adapter is required for old graphs lacking those links. Do not assert unchanged
historical-cohort parity without separately executing and reporting that adapter.
The separately executed `boundary_legacy_parity_v1/results.json` records 487
paired numerical/status agreements with disclosed in-memory index/event adapters.
That direct-pool replay is not new independent data or end-to-end bundle-selection,
source-path or metadata-readiness equivalence.
The sensor fixture demonstrates configuration-driven engineering reuse only, not
independent real-world or cross-domain empirical validation. This protocol is
SHACL-SPARQL expressible; its contribution is the explicit auditable pool separation
and diagnostic interface, not greater logical expressiveness or firstness.
