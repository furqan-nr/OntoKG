#!/usr/bin/env python3
"""Audit released final graphs, without changing the production pipeline.

Run from any directory: python docs/jws_evidence_audit.py
Requires rdflib and pyshacl. Outputs are confined to evaluation_jws/.
The Python dependency checks are an additional audit, NOT existing SHACL features.
Snapshot comparisons are controlled corruption oracles, NOT source verification.
"""
import csv
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

import rdflib
import pyshacl
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
C = Namespace("https://w3id.org/ontokg-eq#")
REQUIRED = {
    "R1": {"YoY profit growth %", "post-report window return %", "benchmark window return %"},
    "R2": {"FX vs company return correlation"},
    "R3": {"post-report window return %", "sector window return %", "benchmark window return %"},
    "R4": {"cumulative abnormal return %"},
}


def one(g, s, p):
    return next(iter(g.objects(s, p)), None)


def audit(g):
    """Independent imperative checks of stored finding/bundle dependencies.

    Checks explicit supports, windows, subjects and rule predicates; does not
    recompute financial metrics from raw prices or verify external sources.
    """
    errors = []
    findings = sorted(set(g.subjects(RDF.type, C.AnalyticalFinding)), key=str)
    for f in findings:
        rid = str(one(g, f, C.derivedByRule))
        entity = one(g, f, C.concernsEntity)
        supports = set(g.objects(f, C.supportedByObservation))
        by_name = {}
        for obs in supports:
            by_name.setdefault(str(one(g, obs, C.hasMetricName)), []).append(obs)
        def fail(code):
            errors.append({"finding": str(f), "code": code})
        if rid not in REQUIRED:
            fail("unknown_rule")
            continue
        if not REQUIRED[rid].issubset(by_name):
            fail("missing_deciding_metric")
        bundle = URIRef(str(f) + "_bundle")
        if (bundle, RDF.type, C.EvidenceBundle) not in g:
            fail("missing_generated_bundle")
        if set(g.objects(bundle, C.includesObservation)) != supports:
            fail("bundle_support_mismatch")
        if entity not in set(g.objects(bundle, C.explainsResultEntity)):
            fail("bundle_result_mismatch")
        for ev in g.objects(bundle, C.containsEvidenceItem):
            if entity not in set(g.objects(ev, C.aboutCompany)):
                fail("evidence_company_mismatch")
            if not list(g.objects(ev, C.hasEvidenceSource)):
                fail("missing_evidence_source")
        if not REQUIRED[rid].issubset(by_name):
            continue
        # Multiple witnesses are possible; these releases normally have one
        # witness per metric. Avoid silently selecting a convenient witness.
        if any(len(by_name[n]) != 1 for n in REQUIRED[rid]):
            fail("ambiguous_witness_requires_review")
            continue
        obs = {n: by_name[n][0] for n in REQUIRED[rid]}
        try:
            vals = {n: float(one(g, o, C.hasMetricValue)) for n, o in obs.items()}
        except (TypeError, ValueError):
            fail("invalid_numeric_witness")
            continue
        for n, o in obs.items():
            subject = one(g, o, C.isObservationOf)
            if n in {"YoY profit growth %", "post-report window return %", "FX vs company return correlation", "cumulative abnormal return %"} and subject != entity:
                fail("observation_company_mismatch")
            if n == "sector window return %" and subject not in set(g.objects(entity, C.isClassifiedByIndustrySector)):
                fail("sector_mismatch")
            if n == "benchmark window return %" and (subject, RDF.type, C.MarketIndex) not in g:
                fail("benchmark_class_mismatch")
        if rid in {"R1", "R3"}:
            windows = {one(g, o, C.observedOverWindow) for n, o in obs.items() if n != "YoY profit growth %"}
            if None in windows or len(windows) != 1:
                fail("deciding_window_mismatch")
        if rid == "R1" and not (vals["YoY profit growth %"] > 0 and vals["post-report window return %"] < vals["benchmark window return %"]):
            fail("rule_predicate_false")
        if rid == "R2" and abs(vals["FX vs company return correlation"]) < .3:
            fail("rule_predicate_false")
        if rid == "R3" and not (vals["post-report window return %"] > vals["sector window return %"] and vals["post-report window return %"] > vals["benchmark window return %"]):
            fail("rule_predicate_false")
        if rid == "R4" and abs(vals["cumulative abnormal return %"]) < 2:
            # R4 can also fire from volume. The released CONSTRUCT includes
            # only CAR; a volume-triggered finding then omits its deciding fact.
            volumes = by_name.get("abnormal volume ratio", [])
            event_window = one(g, obs["cumulative abnormal return %"], C.observedInEventWindow)
            valid_volume = any(one(g, v, C.isObservationOf) == entity and one(g, v, C.observedInEventWindow) == event_window and float(one(g, v, C.hasMetricValue) or 0) >= 1.5 for v in volumes)
            if not valid_volume:
                fail("volume_trigger_not_in_explicit_support")
    return errors


def shacl(g):
    start = perf_counter()
    conforms, report, _ = validate(g, shacl_graph=str(ROOT / "shacl/shapes.ttl"), inference="none", do_owl_imports=False)
    return bool(conforms), len(list(report.subjects(RDF.type, Namespace("http://www.w3.org/ns/shacl#").ValidationResult))), perf_counter() - start


def clone(g):
    other = Graph()
    for t in g:
        other.add(t)
    return other


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="current", help="Output subdirectory under evaluation_jws (e.g. original_release or repaired_release)")
    args = parser.parse_args()
    if not args.label.replace("_", "").replace("-", "").isalnum():
        parser.error("label must contain only letters, numbers, hyphens or underscores")
    out = ROOT / "evaluation_jws" / args.label
    out.mkdir(parents=True, exist_ok=True)
    summaries, details, faults = [], {}, []
    for market in ("psx", "msx", "idx", "idx_scaled"):
        path = ROOT / "data" / f"demo_{market}_inferred.ttl"
        if not path.exists():
            continue
        g = Graph().parse(path)
        conf, results, elapsed = shacl(g)
        start = perf_counter()
        errors = audit(g)
        audit_elapsed = perf_counter() - start
        supporting_obs = set(g.objects(None, C.supportedByObservation))
        source_linked = {o for o in supporting_obs if list(g.objects(o, C.hasEvidenceSource)) or list(g.objects(o, C.supportedByEvidenceItem)) or list(g.objects(o, C.hasProvenanceRecord)) or list(g.objects(o, C.derivedFrom)) or list(g.subjects(C.derivedFrom, o))}
        window_linked = {o for o in supporting_obs if any(list(g.objects(o, p)) for p in (C.observedOverWindow, C.observedInEventWindow, C.observedInPeriod, C.hasObservationDate))}
        summaries.append({"market": market, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "triples": len(g), "findings": len(set(g.subjects(RDF.type, C.AnalyticalFinding))), "bundles": len(set(g.subjects(RDF.type, C.EvidenceBundle))), "shacl_conforms": conf, "shacl_results": results, "shacl_seconds": elapsed, "dependency_issues": len(errors), "dependency_seconds": audit_elapsed, "unique_supporting_observations": len(supporting_obs), "supporting_observations_with_direct_source_or_derivedFrom_link": len(source_linked), "supporting_observations_with_temporal_context": len(window_linked)})
        details[market] = errors
        if market != "psx":
            continue
        # Deterministic single-target interventions on the released final graph.
        f = next(f for f in sorted(g.subjects(RDF.type, C.AnalyticalFinding), key=str) if str(one(g, f, C.derivedByRule)) == "R3")
        obs = next(o for o in g.objects(f, C.supportedByObservation) if str(one(g, o, C.hasMetricName)) == "post-report window return %")
        bundle = URIRef(str(f) + "_bundle")
        ev = next(g.objects(bundle, C.containsEvidenceItem))
        variants = []
        h = clone(g); h.set((obs, C.hasMetricValue, Literal("-999", datatype=XSD.decimal)))
        variants.append(("well_typed_numeric_predicate_flip", h, obs, C.hasMetricValue))
        h = clone(g); h.set((obs, C.hasMetricValue, Literal(str(float(one(g, obs, C.hasMetricValue)) + 0.000001), datatype=XSD.decimal)))
        variants.append(("well_typed_numeric_predicate_preserved", h, obs, C.hasMetricValue))
        window = one(g, obs, C.observedOverWindow)
        alternate = next(w for w in sorted(g.subjects(RDF.type, C.AnalysisWindow), key=str) if w != window)
        h = clone(g); h.set((obs, C.observedOverWindow, alternate))
        variants.append(("wrong_existing_valid_window", h, obs, C.observedOverWindow))
        source = one(g, ev, C.hasEvidenceSource)
        alternate = next(s for s in sorted(g.subjects(RDF.type, C.EvidenceSource), key=str) if s != source)
        h = clone(g); h.set((ev, C.hasEvidenceSource, alternate))
        variants.append(("wrong_existing_valid_source", h, ev, C.hasEvidenceSource))
        h = clone(g); h.remove((bundle, C.includesObservation, obs))
        variants.append(("missing_one_bundle_dependency", h, bundle, C.includesObservation))
        for name, h, target, predicate in variants:
            c, n, t = shacl(h)
            before = {(e["finding"], e["code"]) for e in errors}
            extra = [e for e in audit(h) if (e["finding"], e["code"]) not in before]
            faults.append({"fault": name, "target": str(target), "predicate": str(predicate), "shacl_detected": not c, "dependency_detected": bool(extra), "new_dependency_issues": extra, "snapshot_change_detected": set(h.objects(target, predicate)) != set(g.objects(target, predicate))})
    payload = {"rdflib_version": rdflib.__version__, "pyshacl_version": pyshacl.__version__, "graphs": summaries, "dependency_issues": details, "controlled_faults": faults}
    (out / "evidence_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (out / "evidence_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    lines = ["# Final-graph evidence audit", "", "Run: `python docs/jws_evidence_audit.py`. No production graphs or shapes are changed.", "", "| Market | Findings | Bundles | SHACL conforms | SHACL results | Dependency issues |", "|---|---:|---:|---|---:|---:|"]
    for r in summaries:
        lines.append(f"| {r['market']} | {r['findings']} | {r['bundles']} | {r['shacl_conforms']} | {r['shacl_results']} | {r['dependency_issues']} |")
    lines += ["", "| Market | Unique deciding observations | Direct source/derivedFrom link | Temporal context |", "|---|---:|---:|---:|"]
    for r in summaries:
        lines.append(f"| {r['market']} | {r['unique_supporting_observations']} | {r['supporting_observations_with_direct_source_or_derivedFrom_link']} | {r['supporting_observations_with_temporal_context']} |")
    lines += ["", "Direct-link counts test hasEvidenceSource, supportedByEvidenceItem, hasProvenanceRecord and incoming/outgoing derivedFrom; they do not establish complete PROV dependency paths or deny the existence of graph-wide sources. An announcement source in the same bundle does not itself identify the raw rows used to compute every deciding financial metric.", "", "## Controlled final-graph faults (PSX)", "", "Each intervention starts from the same unmodified graph. Existing evidence and provenance remain. The dependency column measures newly introduced issues, relative to pre-existing issues.", "", "| Intervention | Existing SHACL detects | Additional dependency audit detects | Snapshot oracle detects |", "|---|---|---|---|"]
    for r in faults:
        lines.append(f"| {r['fault']} | {r['shacl_detected']} | {r['dependency_detected']} | {r['snapshot_change_detected']} |")
    lines += ["", "## Interpretation and limits", "", "This is a controlled ablation of validation policies on the same RDF graph with provenance retained. It is not a comparison with an independently implemented provenance system, and it does not demonstrate novelty or superiority over RDF provenance generally.", "", "The additional imperative audit is newly implemented evaluation code, not a capability of the released SHACL shapes or the original pipeline. It checks the consistency of stored finding witnesses, rule predicates and generated bundles. Existing shapes do not explicitly target AnalyticalFinding or require every deciding observation in a bundle.", "", "The snapshot oracle knows the pre-intervention triples, so it detects changed values and source assignments by construction. It is not an independent raw-data correctness test. A plausible wrong value that leaves a rule predicate true can escape both SHACL and dependency checks. A wrong but well-formed source association cannot be verified without a trusted mapping or external source evidence.", "", "The R4 production rule can select on abnormal volume but constructs only the cumulative-abnormal-return support. Volume-triggered results with |CAR| < 2 therefore lack explicit support for the deciding volume condition. The audit reports this rather than silently repairing the release.", "", "This audit covers explicit support of materialized positive findings, not false negatives, all possible CQ answers, raw-price calculations, source authenticity, or multi-witness provenance. Multiple witnesses require manual review. Timing is one local run and is not a performance benchmark. See JSON for hashes, versions, individual issues and times."]
    lines = [line.replace("The R4 production rule can select on abnormal volume but constructs only the cumulative-abnormal-return support. Volume-triggered results with |CAR| < 2 therefore lack explicit support for the deciding volume condition. The audit reports this rather than silently repairing the release.", "The original R4 rule selected on abnormal volume but constructed only the cumulative-abnormal-return support. Original-release volume-triggered results with |CAR| < 2 therefore lacked explicit support for the deciding volume condition. The repaired rule includes volume support; the same checker accepts a matching volume witness when it satisfies the threshold.") for line in lines]
    (out / "evidence_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"graphs": summaries, "faults": faults}, indent=2))


if __name__ == "__main__":
    run()
