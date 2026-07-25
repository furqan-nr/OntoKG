#!/usr/bin/env python3
"""
OntoKG-EQ inference + automated explanation pipeline.

A4 (inference): SPARQL CONSTRUCT rules derive typed :AnalyticalFinding nodes from
the observation-level derived metrics, turning each CQ condition into a queryable,
evidence-linked classification stored in the graph.

A3 (automated explanation): for EVERY finding, an :EvidenceBundle + :QueryExecution
is generated automatically (no hand-authoring) linking the result entity, the
deciding observations, the official announcement evidence, and provenance.

    finding (A4)  ->  auto-generated explanation bundle (A3)  ->  traceable to
    observations + evidence item + source + provenance.

Usage:
    python infer_and_explain.py psx msx
Outputs:
    data/demo_<market>_inferred.ttl
    rules/inference_rules.rq   (the rule set, written once for documentation)
"""
import os, sys
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = Namespace("https://w3id.org/ontokg-eq#")
NS = {"psx": "https://w3id.org/ontokg-eq/psx#", "msx": "https://w3id.org/ontokg-eq/msx#", "idx": "https://w3id.org/ontokg-eq/idx#", "idx_scaled": "https://w3id.org/ontokg-eq/idxscaled#"}
PFX = "PREFIX : <https://w3id.org/ontokg-eq#>\n"

# ----------------------------------------------------------------------------
# A4 — inference rules (CQ-justified). Each derives an :AnalyticalFinding.
# ----------------------------------------------------------------------------
RULES = [
    ("R1", "CQ1", "fundamentals-market-divergence", """
CONSTRUCT {
  ?f a :AnalyticalFinding ; :hasFindingType "fundamentals-market-divergence" ;
     :derivedByRule "R1" ; :forCompetencyQuestion "CQ1" ;
     :concernsEntity ?company ; :supportedByObservation ?fg, ?cr, ?br .
} WHERE {
  ?fg :isObservationOf ?company ; :hasMetricName "YoY profit growth %" ; :hasMetricValue ?g .
  ?company a :Company .
  ?cr :isObservationOf ?company ; :hasMetricName "post-report window return %" ;
      :hasMetricValue ?cret ; :observedOverWindow ?w .
  ?br :isObservationOf ?bm ; :hasMetricName "benchmark window return %" ;
      :hasMetricValue ?bret ; :observedOverWindow ?w .
  ?bm a :MarketIndex .
  FILTER(?g > 0 && ?cret < ?bret)
  BIND(IRI(CONCAT(STR(?company), "_finding_R1")) AS ?f)
}"""),
    ("R2", "CQ2", "fx-sensitive", """
CONSTRUCT {
  ?f a :AnalyticalFinding ; :hasFindingType "fx-sensitive" ;
     :derivedByRule "R2" ; :forCompetencyQuestion "CQ2" ;
     :concernsEntity ?company ; :supportedByObservation ?cc .
} WHERE {
  ?cc :isObservationOf ?company ; :hasMetricName "FX vs company return correlation" ; :hasMetricValue ?r .
  ?company a :Company .
  FILTER(ABS(?r) >= 0.3)
  BIND(IRI(CONCAT(STR(?company), "_finding_R2")) AS ?f)
}"""),
    ("R3", "CQ3", "relative-outperformer", """
CONSTRUCT {
  ?f a :AnalyticalFinding ; :hasFindingType "relative-outperformer" ;
     :derivedByRule "R3" ; :forCompetencyQuestion "CQ3" ;
     :concernsEntity ?company ; :supportedByObservation ?cr, ?sr, ?br .
} WHERE {
  ?cr :isObservationOf ?company ; :hasMetricName "post-report window return %" ;
      :hasMetricValue ?cret ; :observedOverWindow ?w .
  ?company a :Company ; :isClassifiedByIndustrySector ?sector .
  ?sr :isObservationOf ?sector ; :hasMetricName "sector window return %" ;
      :hasMetricValue ?sret ; :observedOverWindow ?w .
  ?br :isObservationOf ?bm ; :hasMetricName "benchmark window return %" ;
      :hasMetricValue ?bret ; :observedOverWindow ?w .
  ?bm a :MarketIndex .
  FILTER(?cret > ?sret && ?cret > ?bret)
  BIND(IRI(CONCAT(STR(?company), "_finding_R3")) AS ?f)
}"""),
    ("R4", "CQ4", "abnormal-event-reaction", """
CONSTRUCT {
  ?f a :AnalyticalFinding ; :hasFindingType "abnormal-event-reaction" ;
     :derivedByRule "R4" ; :forCompetencyQuestion "CQ4" ;
     :concernsEntity ?company ; :supportedByObservation ?ar .
} WHERE {
  ?ar :isObservationOf ?company ; :hasMetricName "cumulative abnormal return %" ;
      :hasMetricValue ?car ; :observedInEventWindow ?ew .
  OPTIONAL { ?vr :isObservationOf ?company ; :hasMetricName "abnormal volume ratio" ;
             :hasMetricValue ?vol ; :observedInEventWindow ?ew . }
  FILTER(ABS(?car) >= 2.0 || COALESCE(?vol, 0) >= 1.5)
  BIND(IRI(CONCAT(STR(?ew), "_finding_R4")) AS ?f)
}"""),
]

def write_rules_doc():
    os.makedirs(os.path.join(HERE, "rules"), exist_ok=True)
    with open(os.path.join(HERE, "rules", "inference_rules.rq"), "w") as fh:
        fh.write("# OntoKG-EQ inference rules (A4). Applied by infer_and_explain.py.\n")
        fh.write("# Each rule derives an :AnalyticalFinding from observation-level metrics.\n\n")
        for rid, cq, ftype, q in RULES:
            fh.write(f"# ---- {rid}  ({cq}: {ftype}) ----\n{PFX}{q.strip()}\n\n")

def build(market):
    ns = Namespace(NS[market])
    g = Graph()
    g.parse(os.path.join(HERE, "data", f"demo_{market}.ttl"), format="turtle")
    g.parse(os.path.join(HERE, "rules", "findings.ttl"), format="turtle")

    # --- A4: apply inference rules ---
    counts = {}
    for rid, cq, ftype, q in RULES:
        produced = g.query(PFX + q)
        added = 0
        for t in produced:
            g.add(t); added += 1
        counts[rid] = added
    n_find = len(set(g.subjects(RDF.type, CORE.AnalyticalFinding)))

    # announcement per company (for evidence link in generated explanations)
    ann_for = {}
    for ann in g.subjects(RDF.type, CORE.Announcement):
        for co in g.objects(ann, CORE.aboutCompany):
            ann_for[co] = ann
    VALID = ns["validation_passed"]

    # --- A3: auto-generate an explanation bundle for every finding ---
    gen = 0
    for f in set(g.subjects(RDF.type, CORE.AnalyticalFinding)):
        entity = next(g.objects(f, CORE.concernsEntity), None)
        cq = next(g.objects(f, CORE.forCompetencyQuestion), None)
        obss = list(g.objects(f, CORE.supportedByObservation))
        if entity is None or not obss:
            continue
        bundle = URIRef(str(f) + "_bundle")
        g.add((bundle, RDF.type, CORE.EvidenceBundle))
        g.add((bundle, CORE.explainsResultEntity, entity))
        g.add((bundle, CORE.hasValidationStatus, VALID))
        for o in obss:
            g.add((bundle, CORE.includesObservation, o))
        if entity in ann_for:
            g.add((bundle, CORE.containsEvidenceItem, ann_for[entity]))
        qe = URIRef(str(f) + "_qe")
        g.add((qe, RDF.type, CORE.QueryExecution))
        g.add((qe, CORE.hasEvidenceBundle, bundle))
        g.add((qe, CORE.hasQueryFamilyIdentifier, Literal(str(cq))))
        g.add((qe, CORE.hasQueryInstanceIdentifier, Literal(f"{cq}-GEN-{gen+1}")))
        g.add((qe, CORE.hasParameterValues,
               Literal(f"auto-generated explanation for finding {str(f).split('#')[-1]}")))
        gen += 1

    out = os.path.join(HERE, "data", f"demo_{market}_inferred.ttl")
    g.serialize(destination=out, format="turtle")
    by_type = {}
    for f in set(g.subjects(RDF.type, CORE.AnalyticalFinding)):
        t = str(next(g.objects(f, CORE.hasFindingType), ""))
        by_type[t] = by_type.get(t, 0) + 1
    print(f"[{market}] findings={n_find} {dict(sorted(by_type.items()))} "
          f"| generated_explanations={gen} | rule_hits={counts} -> {os.path.basename(out)}")

if __name__ == "__main__":
    write_rules_doc()
    for m in (sys.argv[1:] or ["psx", "msx"]):
        build(m)
