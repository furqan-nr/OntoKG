#!/usr/bin/env python3
"""Evaluate CQ1-CQ5 on a large graph where the multi-join SPARQL (CQ1/CQ3) is engine-bound on the
in-memory store (see Section 7.5). CQ2/CQ4/CQ5 run via SPARQL; CQ1/CQ3 are computed by the equivalent
direct evaluation over the derived-metric observations (identical semantics). Writes evaluation_idx_scaled/."""
import os, glob, csv
from rdflib import Graph
from rdflib.namespace import Namespace
C=Namespace("https://w3id.org/ontokg-eq#")
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTL=os.path.join(HERE,"data","demo_idx_scaled.ttl"); OUT=os.path.join(HERE,"evaluation_idx_scaled")
def short(x): return str(x).split("#")[-1]
g=Graph().parse(TTL,format="turtle")
# SPARQL for the cheap families
res={}
for fam in ["CQ2","CQ4","CQ5"]:
    res[fam]=list(g.query(open(os.path.join(HERE,"queries",f"{fam}_CASE_01.rq")).read()))
# direct evaluation for CQ1/CQ3 (engine-bound in SPARQL at this scale)
post={}; bench={}; sect={}; growth={}
for o in g.subjects(C.hasMetricName,None):
    m=str(next(g.objects(o,C.hasMetricName))); v=next(g.objects(o,C.hasMetricValue),None)
    if v is None: continue
    val=float(v); ent=next(g.objects(o,C.isObservationOf),None); w=next(g.objects(o,C.observedOverWindow),None)
    if   m=="post-report window return %" and w is not None: post[w]=(ent,val)
    elif m=="benchmark window return %"  and w is not None: bench[w]=val
    elif m=="sector window return %"     and w is not None: sect[w]=val
    elif m=="YoY profit growth %": growth[ent]=val
cq1=[]; cq3=[]
for w,(ent,cret) in post.items():
    br=bench.get(w); sr=sect.get(w); gr=growth.get(ent)
    if br is None: continue
    if gr is not None and gr>0 and cret<br: cq1.append((short(ent),round(gr,2),round(cret,2),round(br,2)))
    if sr is not None and cret>sr and cret>br: cq3.append((short(ent),round(cret,2),round(sr,2),round(br,2)))
# write
def wcsv(name,header,rows):
    with open(os.path.join(OUT,name),"w",newline="") as f:
        w=csv.writer(f); w.writerow(header); [w.writerow(r) for r in rows]
wcsv("CQ1_CASE_01_results.csv",["company","yoy_profit_growth_pct","company_return","benchmark_return"],sorted(cq1,key=lambda x:-x[1]))
wcsv("CQ3_CASE_01_results.csv",["company","company_return","sector_return","benchmark_return"],sorted(cq3,key=lambda x:-x[1]))
for fam in ["CQ2","CQ4","CQ5"]:
    rr=res[fam]; vars=[str(v) for v in (rr[0].labels if rr else [])] if rr else []
    with open(os.path.join(OUT,f"{fam}_CASE_01_results.csv"),"w",newline="") as f:
        w=csv.writer(f)
        if rr:
            keys=list(rr[0].asdict().keys()); w.writerow(keys)
            for row in rr: w.writerow([short(row[k]) if row[k] and '#' in str(row[k]) else row[k] for k in keys])
counts={"CQ1":len(cq1),"CQ2":len(res["CQ2"]),"CQ3":len(cq3),"CQ4":len(res["CQ4"]),"CQ5":len(res["CQ5"])}
with open(os.path.join(OUT,"_summary.md"),"w") as f:
    f.write("# Scaled IDX (64 stocks) CQ results\n\n")
    f.write(f"Triples: {len(g)}. CQ2/CQ4/CQ5 via SPARQL; CQ1/CQ3 via direct evaluation (SPARQL engine-bound at this scale, Section 7.5).\n\n")
    f.write("| CQ | rows |\n|---|---:|\n")
    for k in ["CQ1","CQ2","CQ3","CQ4","CQ5"]: f.write(f"| {k} | {counts[k]} |\n")
    f.write(f"\nJCI benchmark window return over the common window: {round(list(bench.values())[0],2)}%\n")
print("counts:",counts,"-> wrote",OUT)
