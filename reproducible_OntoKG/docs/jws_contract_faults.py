"""Controlled validation-policy ablation; never changes production artifacts.

Run with the same rdflib/pyshacl dependencies as jws_contracts.py.
The snapshot oracle detects changed triples by construction, not source truth.
"""
from pathlib import Path
import hashlib
import json

from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from pyshacl import validate
from jws_contracts import evaluate_finding, load_contracts

ROOT = Path(__file__).resolve().parents[1]
C = Namespace("https://w3id.org/ontokg-eq#")
PROV = Namespace("http://www.w3.org/ns/prov#")
AUD = Namespace("https://w3id.org/ontokg-eq/lineage-audit#")


def clone(g):
    h = Graph()
    for triple in g:
        h.add(triple)
    return h


def one(g, s, p):
    return g.value(s, p)


def run():
    out = ROOT / "evaluation_jws/contracts_faults"
    out.mkdir(parents=True, exist_ok=True)
    path = ROOT / "data/demo_psx_inferred.ttl"
    g = Graph().parse(path)
    lineage_path = ROOT / "evaluation_jws/source_lineage.psx.ttl"
    lineage = Graph().parse(lineage_path)
    load_contracts()  # Fail early if the contract registry is unreadable.
    findings = sorted(g.subjects(RDF.type, C.AnalyticalFinding), key=str)
    f = next(f for f in findings if str(one(g, f, C.derivedByRule)) == "R3")
    supports = list(g.objects(f, C.supportedByObservation))
    obs = next(o for o in supports if str(one(g, o, C.hasMetricName)) == "post-report window return %")
    benchmark = next(o for o in supports if str(one(g, o, C.hasMetricName)) == "benchmark window return %")
    sector = next(o for o in supports if str(one(g, o, C.hasMetricName)) == "sector window return %")
    bundle = URIRef(str(f) + "_bundle")
    variants = [("positive_control", clone(g), clone(lineage), f, "Unmodified positive finding.")]

    h = clone(g)
    alternate = next(c for c in sorted(g.subjects(RDF.type, C.Company), key=str) if c != one(g, obs, C.isObservationOf))
    h.set((obs, C.isObservationOf, alternate))
    variants.append(("wrong_valid_company", h, clone(lineage), f, "Observation points to another existing Company."))
    h = clone(g)
    alternate = next(w for w in sorted(g.subjects(RDF.type, C.AnalysisWindow), key=str) if w != one(g, obs, C.observedOverWindow))
    h.set((obs, C.observedOverWindow, alternate))
    variants.append(("wrong_valid_window", h, clone(lineage), f, "Company return and comparators now use different valid windows."))
    h = clone(g)
    h.remove((f, C.supportedByObservation, benchmark))
    h.remove((bundle, C.includesObservation, benchmark))
    variants.append(("missing_deciding_comparator", h, clone(lineage), f, "Remove benchmark from both finding and bundle to preserve their agreement."))
    h = clone(g)
    h.remove((bundle, C.includesObservation, benchmark))
    variants.append(("missing_bundle_only_comparator", h, clone(lineage), f, "Keep finding support intact but remove the comparator from the actual explanation bundle."))
    h = clone(g)
    h.set((obs, C.hasMetricName, Literal("cumulative abnormal return %")))
    variants.append(("wrong_metric_same_number", h, clone(lineage), f, "Replace the metric label while preserving its numeric value."))
    h = clone(g)
    h.set((obs, C.hasMetricValue, Literal(str(float(one(g, obs, C.hasMetricValue)) + .000001), datatype=XSD.decimal)))
    variants.append(("plausible_numeric_predicate_preserved", h, clone(lineage), f, "A tiny value corruption retains the true condition; no independent source recomputation is claimed."))
    h = clone(g)
    h.set((obs, C.hasMetricValue, one(g, sector, C.hasMetricValue)))
    variants.append(("strict_threshold_equal_sector", h, clone(lineage), f, "Strict company > sector must reject equality."))
    sector_value = float(one(g, sector, C.hasMetricValue))
    benchmark_value = float(one(g, benchmark, C.hasMetricValue))
    if sector_value != benchmark_value:
        h = clone(g)
        h.set((obs, C.hasMetricValue, Literal(str((sector_value + benchmark_value) / 2), datatype=XSD.decimal)))
        variants.append(("cq3_or_only_witness", h, clone(lineage), f, "Company exceeds exactly one comparator: would pass an OR query but fails the intended AND contract."))
    h = clone(g)
    for o in supports:
        h.remove((f, C.supportedByObservation, o))
        h.remove((bundle, C.includesObservation, o))
    variants.append(("missing_all_evidence", h, clone(lineage), f, "Expect explicit insufficient evidence, never a confirmed explanation."))
    # Change only a well-formed overlay source assignment. A complete path is
    # still a path: without a trusted mapping it cannot establish source truth.
    l = clone(lineage)
    cell = next(cell for cell in l.objects(obs, PROV.wasDerivedFrom) if one(l, cell, PROV.hadPrimarySource) is not None)
    old_source = one(l, cell, PROV.hadPrimarySource)
    alternate = next(s for s in sorted(set(l.objects(None, PROV.hadPrimarySource)), key=str) if s != old_source)
    l.set((cell, PROV.hadPrimarySource, alternate))
    variants.append(("incoherent_source_identifier_overlay", clone(g), clone(l), f, "Substitute only the existing source edge while retaining the original declared source identifier; internal mismatch is detectable."))
    # Keep the declared identifier internally coherent with the wrong source.
    # This remains a false attribution against the known original, but internal
    # identity consistency alone cannot establish upstream source truth.
    l.set((cell, AUD.sourceIdentifier, one(l, alternate, C.hasSourceIdentifier)))
    variants.append(("wrong_valid_source_overlay", clone(g), l, f, "Existing source and its matching declared identifier substituted together; internally coherent false attribution cannot be authenticated by path checks."))
    l = clone(lineage)
    for dependency in l.objects(obs, PROV.wasDerivedFrom):
        l.remove((dependency, PROV.hadPrimarySource, None))
    variants.append(("broken_source_path_overlay", clone(g), l, f, "Remove primary-source edges from company-return dependency cells. Numerical sufficiency may remain while source sufficiency fails."))

    # OR sufficiency control: remove CAR only when a passing volume witness is
    # already present in a released R4 finding. No invented witness is added.
    for event in findings:
        if str(one(g, event, C.derivedByRule)) != "R4":
            continue
        obs4 = list(g.objects(event, C.supportedByObservation))
        volume = [o for o in obs4 if str(one(g, o, C.hasMetricName)) == "abnormal volume ratio" and float(one(g, o, C.hasMetricValue)) >= 1.5]
        if volume:
            h = clone(g)
            for o in obs4:
                if str(one(g, o, C.hasMetricName)) == "cumulative abnormal return %":
                    h.remove((event, C.supportedByObservation, o))
                    h.remove((URIRef(str(event) + "_bundle"), C.includesObservation, o))
            variants.append(("r4_volume_only_sufficient", h, clone(lineage), event, "OR predicate has a passing volume witness; CAR is unnecessary to establish this branch."))
            break

    rows = []
    for name, h, l, target, note in variants:
        conforms, report, _ = validate(h, shacl_graph=str(ROOT / "shacl/shapes.ttl"), inference="none", do_owl_imports=False)
        result = evaluate_finding(h, target, lineage_graph=l)
        rows.append({"case": name, "finding": str(target), "existing_shacl_conforms": bool(conforms),
                     "rdf_evidence_without_contract_policy": "accepted_without_semantic_checks",
                     "contract_result": result, "known_snapshot_changed": set(h) != set(g) or set(l) != set(lineage), "note": note})
    query = (ROOT / "queries/CQ3_CASE_01.rq").read_text(encoding="utf-8")
    drifted = query.replace("&&", "||")
    assert drifted != query
    artifact = {"case": "cq3_and_to_or_artifact_drift", "original_sha256": hashlib.sha256(query.encode()).hexdigest(),
                "mutated_sha256": hashlib.sha256(drifted.encode()).hexdigest(), "hash_drift_detected": query != drifted,
                "condition_checker_on_unchanged_finding": evaluate_finding(g, f, lineage_graph=lineage),
                "note": "Artifact hash drift is separate from evaluating a stored result. No claim that a positive witness reveals an edited query."}
    payload = {"graph_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "lineage_sha256": hashlib.sha256(lineage_path.read_bytes()).hexdigest(),
               "comparison": "same-data validation-policy ablation; not a head-to-head provenance-system benchmark", "cases": rows, "artifact_drift": artifact,
               "controlled_corruption_summary": {"cases": sum(r["case"] not in {"positive_control", "r4_volume_only_sufficient"} for r in rows), "existing_shacl_rejected": sum(not r["existing_shacl_conforms"] for r in rows if r["case"] not in {"positive_control", "r4_volume_only_sufficient"}),
                                                  "contract_rejected_or_incomplete": sum(r["contract_result"]["status"] != "sufficient" for r in rows if r["case"] not in {"positive_control", "r4_volume_only_sufficient"}),
                                                  "bundle_rejected_or_incomplete": sum(not r["contract_result"].get("bundle_sufficient", False) for r in rows if r["case"] not in {"positive_control", "r4_volume_only_sufficient"}),
                                                  "source_path_policy_failed": sum(not r["contract_result"].get("source_sufficient_witness", False) for r in rows if r["case"] not in {"positive_control", "r4_volume_only_sufficient"}),
                                                  "any_contract_policy_failed": sum(r["contract_result"]["status"] != "sufficient" or not r["contract_result"].get("bundle_sufficient", False) or not r["contract_result"].get("source_sufficient_witness", False) for r in rows if r["case"] not in {"positive_control", "r4_volume_only_sufficient"}),
                                                  "note": "Selected deterministic PSX interventions only; this is not a detection-rate estimate for naturally occurring errors."},
               "untestable": [{"case": "wrong_currency_unit", "reason": "Released deciding observations lack explicit machine-readable currency/unit metadata; no values or metadata invented."}],
               "limits": "Snapshot differences detect interventions by construction. Neither source existence nor a known snapshot authenticates upstream sources. Positive findings only; no recall claim."}
    (out / "results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    lines = ["# CQ contract controlled faults", "", payload["comparison"], "", "| Case | Existing SHACL conforms | Contract result | Snapshot changed |", "|---|---|---|---|"]
    for row in rows:
        result = row['contract_result']
        lines.append(f"| {row['case']} | {row['existing_shacl_conforms']} | finding={result['status']}; bundle={result.get('bundle_status', 'not_reported')}; source={result.get('source_sufficient_witness', 'not_reported')} | {row['known_snapshot_changed']} |")
    lines += ["", "Condition replay, actual-bundle sufficiency and source-path completeness are separate policies. The source substitution and plausible numerical corruption remain undetected by the semantic policies. Two separate controls establish ordinary positive acceptance and sufficiency of the volume-only R4 OR branch. These deliberately selected cases are not an estimate of natural-error detection rates.", "", "## Intervention definitions", ""]
    lines.extend(f"- `{r['case']}`: {r['note']}" for r in rows)
    lines += ["", "The RDF-evidence ablation preserves the same triples and provenance but performs no semantic contract checks. Its acceptance is a defined policy, not a claim about another provenance implementation.", "", artifact["note"], "", payload["limits"], "", "Currency/unit corruption is untestable because the deciding observations lack explicit metadata."]
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    expected = {"positive_control": "sufficient", "wrong_valid_company": "incomplete", "wrong_valid_window": "incomplete",
                "missing_deciding_comparator": "incomplete", "wrong_metric_same_number": "incomplete",
                "plausible_numeric_predicate_preserved": "sufficient", "strict_threshold_equal_sector": "predicate_false",
                "missing_all_evidence": "incomplete", "wrong_valid_source_overlay": "sufficient",
                "cq3_or_only_witness": "predicate_false", "r4_volume_only_sufficient": "sufficient",
                "missing_bundle_only_comparator": "sufficient", "broken_source_path_overlay": "sufficient",
                "incoherent_source_identifier_overlay": "sufficient"}
    for row in rows:
        assert row["contract_result"]["status"] == expected[row["case"]], row["case"]
        if row['case'] == 'missing_bundle_only_comparator':
            assert row['contract_result']['bundle_status'] == 'incomplete_bundle', row['contract_result']
        if row['case'] in {'broken_source_path_overlay', 'incoherent_source_identifier_overlay'}:
            assert not row['contract_result']['source_sufficient_witness'], row['contract_result']
        if row['case'] == 'wrong_valid_source_overlay':
            assert row['contract_result']['source_sufficient_witness'], row['contract_result']
    print(json.dumps({"cases": [{"case": r["case"], "shacl_conforms": r["existing_shacl_conforms"], "status": r["contract_result"]["status"]} for r in rows], "assertions": "passed"}, indent=2))


if __name__ == "__main__":
    run()
