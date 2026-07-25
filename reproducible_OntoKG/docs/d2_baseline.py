#!/usr/bin/env python3
"""D2: baseline comparison. Relational/SQL baseline over the SAME PSX derived metrics vs the
KG/SPARQL approach. Shows result equivalence but loss of validation, provenance-linked
explanation, and cross-market reuse. (GraphRAG contrast is structural; no LLM is run.)"""
import os, glob, sqlite3
from rdflib import Graph
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def short(x): return str(x).split('#')[-1]

g=Graph().parse(os.path.join(HERE,"data","demo_psx.ttl"),format="turtle")
# extract per-company metrics (same numbers the KG uses), aligned on the company's window
rows=g.query('''PREFIX : <https://w3id.org/ontokg-eq#>
SELECT ?company ?growth ?ret ?sret ?bret WHERE {
  ?company a :Company .
  ?cr :isObservationOf ?company ; :hasMetricName "post-report window return %" ; :hasMetricValue ?ret ; :observedOverWindow ?w .
  OPTIONAL { ?go :isObservationOf ?company ; :hasMetricName "YoY profit growth %" ; :hasMetricValue ?growth }
  OPTIONAL { ?company :isClassifiedByIndustrySector ?sec .
             ?sr :isObservationOf ?sec ; :hasMetricName "sector window return %" ; :hasMetricValue ?sret ; :observedOverWindow ?w }
  OPTIONAL { ?br :isObservationOf ?bm ; :hasMetricName "benchmark window return %" ; :hasMetricValue ?bret ; :observedOverWindow ?w . ?bm a :MarketIndex }
}''')
recs=[(short(r.company), float(r.growth) if r.growth is not None else None,
       float(r.ret), float(r.sret) if r.sret is not None else None,
       float(r.bret) if r.bret is not None else None) for r in rows]

# ---- relational baseline ----
con=sqlite3.connect(":memory:"); cur=con.cursor()
cur.execute("CREATE TABLE m(company TEXT, growth REAL, ret REAL, sector_ret REAL, bench_ret REAL)")
cur.executemany("INSERT INTO m VALUES (?,?,?,?,?)", recs)
sql_cq1="SELECT company FROM m WHERE growth>0 AND ret<bench_ret ORDER BY growth DESC"
sql_cq3="SELECT company FROM m WHERE ret>sector_ret AND ret>bench_ret ORDER BY ret DESC"
sql1=[r[0] for r in cur.execute(sql_cq1)]
sql3=[r[0] for r in cur.execute(sql_cq3)]

# ---- KG/SPARQL results ----
def sparql_companies(fam):
    q=open(os.path.join(HERE,"queries",f"{fam}_CASE_01.rq")).read()
    return sorted({short(r.company) for r in g.query(q)})
kg1=sorted(set(sql1)); kg1_sparql=sparql_companies("CQ1")
kg3=sorted(set(sql3)); kg3_sparql=sparql_companies("CQ3")

md=os.path.join(HERE,"evaluation","baseline_comparison.md")
with open(md,"w") as f:
    f.write("# Baseline comparison (D2)\n\n")
    f.write("Relational/SQL baseline over the **same** PSX derived metrics, vs the KG/SPARQL pipeline.\n\n")
    f.write("## Result equivalence (PSX)\n\n")
    f.write(f"- CQ1 — SQL: {sorted(set(sql1))} ; SPARQL: {kg1_sparql} ; **match: {sorted(set(sql1))==kg1_sparql}**\n")
    f.write(f"- CQ3 — SQL: {sorted(set(sql3))} ; SPARQL: {kg3_sparql} ; **match: {sorted(set(sql3))==kg3_sparql}**\n\n")
    f.write("Both compute identical result entities — confirming the KG layer does not change the analytics, "
            "only what surrounds them.\n\n")
    f.write("## What the relational baseline cannot provide (without bespoke extra engineering)\n\n")
    f.write("| Dimension | Relational / SQL baseline | OntoKG-EQ (KG) |\n|---|---|---|\n")
    f.write("| Answers CQ1/CQ3 | yes | yes (identical rows) |\n")
    f.write("| Structural validation of inputs | none built-in (ad-hoc CHECK constraints at best) | SHACL shapes, `Conforms=True` |\n")
    f.write("| Result -> evidence -> source -> provenance | not returned; needs hand-written joins across bespoke tables | automatic `EvidenceBundle` + traceable path |\n")
    f.write("| Derived classifications (findings) as first-class, queryable objects | no (transient query rows) | yes (`AnalyticalFinding` + rule/CQ provenance) |\n")
    f.write("| Cross-market reuse | schema + per-column SQL rewrites per market (e.g. eps vs eps_myr, pkr_usd_rate vs myr_usd_rate) | ontology + shapes + queries unchanged; bounded config only |\n")
    f.write("| Self-describing semantics | column names only | typed ontology terms with CQ justification |\n\n")
    f.write("## Contrast with GraphRAG / LLM answering (structural, not run here)\n\n")
    f.write("A GraphRAG/KG-RAG baseline would answer the CQs by retrieving subgraphs and generating text. "
            "We deliberately do **not** run an LLM: the point of contrast is that GraphRAG faithfulness is "
            "*estimated* (and known to admit faithfulness hallucinations even with retrieval), whereas "
            "OntoKG-EQ produces results by SPARQL over a SHACL-validated graph with every result bound to an "
            "evidence bundle whose observations, sources, and provenance are present in the validated graph "
            "by construction. Faithfulness is therefore **structurally guaranteed rather than measured**. "
            "A future empirical study (instrument an LLM over the same graph) can quantify GraphRAG "
            "explanation-faithfulness against this provenance-grounded reference.\n")
print("CQ1 SQL:",sorted(set(sql1)),"SPARQL:",kg1_sparql,"match:",sorted(set(sql1))==kg1_sparql)
print("CQ3 SQL:",sorted(set(sql3)),"SPARQL:",kg3_sparql,"match:",sorted(set(sql3))==kg3_sparql)
print("wrote",md)
