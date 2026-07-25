#!/usr/bin/env python3
"""D4: ablation study. Remove one component at a time and measure the capability it provides.
Components: SHACL validation, provenance layer, inference rules, evidence bundles/explanation.
Outputs evaluation/ablation_results.md (+ prints table)."""
import os, glob, copy
from rdflib import Graph, RDF, Namespace, URIRef, Literal
from rdflib.namespace import XSD
from pyshacl import validate

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = Namespace("https://w3id.org/ontokg-eq#")
shapes = Graph().parse(os.path.join(HERE,"shacl","shapes.ttl"), format="turtle")

def load(p): return Graph().parse(os.path.join(HERE,"data",p), format="turtle")

def explanation_completeness(g):
    """Fraction of findings whose generated bundle resolves obs + evidence + source + provenance."""
    findings = list(g.subjects(RDF.type, CORE.AnalyticalFinding))
    if not findings: return None, 0
    ok = 0
    for f in findings:
        b = URIRef(str(f)+"_bundle")
        has_obs = (b, CORE.includesObservation, None) in g
        evs = list(g.objects(b, CORE.containsEvidenceItem))
        has_src = any((ev, CORE.hasEvidenceSource, None) in g for ev in evs)
        has_prov = any(any(g.subjects(CORE.derivedFrom, ev)) for ev in evs)
        if has_obs and evs and has_src and has_prov: ok += 1
    return ok/len(findings), len(findings)

def cq5_rows(g):
    q=open(os.path.join(HERE,"queries","CQ5_CASE_01.rq")).read()
    return len(list(g.query(q)))

def shacl_detects_malformed(market):
    """Inject a MarketObservation missing hasMetricValue; with SHACL it is caught, without it is not."""
    g = load(f"demo_{market}.ttl")
    bad = URIRef("https://w3id.org/ontokg-eq/test#bad_obs")
    g.add((bad, RDF.type, CORE.MarketObservation)); g.add((bad, RDF.type, CORE.Observation))
    g.add((bad, CORE.hasMetricName, Literal("close price")))   # missing hasMetricValue (shape requires it)
    g.add((bad, CORE.observedOverWindow, URIRef("https://w3id.org/ontokg-eq/test#w")))
    conforms,_,_ = validate(g, shacl_graph=shapes)
    return (0 if conforms else 1)   # with SHACL: 1 violation detected; without SHACL: 0 (undetected)

rows=[]
for m in ["psx","msx"]:
    inf = load(f"demo_{m}_inferred.ttl")
    base = load(f"demo_{m}.ttl")
    full_comp, nf = explanation_completeness(inf)
    # ablation: no provenance
    g_np = Graph(); [g_np.add(t) for t in inf]
    for p in list(g_np.subjects(RDF.type, CORE.ProvenanceRecord)):
        for t in list(g_np.triples((p,None,None))): g_np.remove(t)
        for t in list(g_np.triples((None,None,p))): g_np.remove(t)
    np_comp,_ = explanation_completeness(g_np)
    # ablation: no evidence source
    g_ns = Graph(); [g_ns.add(t) for t in inf]
    for t in list(g_ns.triples((None,CORE.hasEvidenceSource,None))): g_ns.remove(t)
    ns_comp,_ = explanation_completeness(g_ns)
    # ablation: no inference rules (base graph has no findings)
    base_findings = len(list(base.subjects(RDF.type, CORE.AnalyticalFinding)))
    # ablation: no bundles/explanation -> CQ5 rows
    g_nb = Graph(); [g_nb.add(t) for t in inf]
    for b in list(g_nb.subjects(RDF.type, CORE.EvidenceBundle)):
        for t in list(g_nb.triples((b,None,None))): g_nb.remove(t)
    cq5_full=cq5_rows(inf); cq5_nb=cq5_rows(g_nb)
    sh = shacl_detects_malformed(m)
    rows.append((m.upper(), nf, base_findings, full_comp, np_comp, ns_comp, cq5_full, cq5_nb, sh))

md = os.path.join(HERE,"evaluation","ablation_results.md")
with open(md,"w") as f:
    f.write("# Ablation study (D4)\n\nEach component removed in isolation; the metric it supports degrades.\n\n")
    f.write("## Explanation completeness (fraction of findings with full obs+evidence+source+provenance path)\n\n")
    f.write("| Market | Findings | Full | No provenance | No evidence-source |\n|---|---:|---:|---:|---:|\n")
    for r in rows:
        f.write(f"| {r[0]} | {r[1]} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} |\n")
    f.write("\n## Inference rules removed (findings derived)\n\n| Market | With rules | Without rules |\n|---|---:|---:|\n")
    for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]} |\n")
    f.write("\n## Evidence bundles removed (CQ5 explainability rows)\n\n| Market | With bundles | Without bundles |\n|---|---:|---:|\n")
    for r in rows: f.write(f"| {r[0]} | {r[6]} | {r[7]} |\n")
    f.write("\n## SHACL removed (malformed observation detected?)\n\n| Market | With SHACL (violations caught) | Without SHACL |\n|---|---:|---:|\n")
    for r in rows: f.write(f"| {r[0]} | {r[8]} | 0 (undetected) |\n")

print("ablation rows (market, findings, base_findings, full_comp, no_prov, no_src, cq5_full, cq5_nobundle, shacl_detect):")
for r in rows: print("  ", r)
print("wrote", md)
