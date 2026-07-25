#!/usr/bin/env python3
"""Faithfulness experiment across the SCALED IDX cohort (64 stocks).
Builds a worked case for every CQ3 outperformer and CQ1 divergence company directly from the scaled
graph's derived metrics (the inference CONSTRUCTs are engine-bound at 37k triples, Section 7.5/7.2.1),
then scores OntoKG-EQ reference answers (faithful by construction) and, if an LLM is configured via
ONTOKG_LLM, GraphRAG/LLM answers. Reports a distribution over ~41 cases.
Env: ONTOKG_LLM (e.g. hf:Qwen/Qwen2.5-7B-Instruct); ONTOKG_TTL (default data/demo_idx_scaled.ttl);
ONTOKG_OUT (default ../evaluation_idx_scaled). Run on a GPU for the LLM rows."""
import os, re, glob, csv
from rdflib import Graph
from rdflib.namespace import Namespace, RDF
C=Namespace("https://w3id.org/ontokg-eq#")
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTL=os.environ.get("ONTOKG_TTL", os.path.join(HERE,"data","demo_idx_scaled.ttl"))
OUT=os.environ.get("ONTOKG_OUT", os.path.join(HERE,"evaluation_idx_scaled"))
PRED=re.compile(r"\b(because|due to|driven by|will|likely|expected to|forecast|predict|target|recommend|buy|sell|cause|outlook|going to|should)\b",re.I)
NUM=re.compile(r"-?\d+\.\d+")
def short(x): return str(x).split("#")[-1] if x else ""

def build_scaled_cases(g):
    post={}; bench={}; sect={}; growth={}
    for o in g.subjects(C.hasMetricName,None):
        m=str(next(g.objects(o,C.hasMetricName))); v=next(g.objects(o,C.hasMetricValue),None)
        if v is None: continue
        val=float(v); ent=next(g.objects(o,C.isObservationOf),None); w=next(g.objects(o,C.observedOverWindow),None)
        if   m=="post-report window return %" and w is not None: post[w]=(ent,val)
        elif m=="benchmark window return %"  and w is not None: bench[w]=val
        elif m=="sector window return %"     and w is not None: sect[w]=val
        elif m=="YoY profit growth %": growth[ent]=val
    ann={}
    for a in g.subjects(RDF.type, C.Announcement):
        e=next(g.objects(a,C.aboutCompany),None)
        d=str(next(g.objects(a,C.hasAnnouncementDate),"")); s=next(g.objects(a,C.hasEvidenceSource),None)
        ann[e]=(d, short(s) if s else "", str(next(g.objects(s,C.hasSourceType),"")) if s else "")
    cases=[]
    for w,(ent,cret) in post.items():
        br=bench.get(w); sr=sect.get(w); gr=growth.get(ent)
        label=str(next(g.objects(ent,C.hasCompanyName),short(ent)))
        d,src,st=ann.get(ent,("","",""))
        prov=[d,src,"Yahoo","Indonesia Stock Exchange","disclosure"]
        if sr is not None and br is not None and cret>sr and cret>br:
            atoms=[f"{label} return = {round(cret,2)}", f"sector return = {round(sr,2)}", f"benchmark return = {round(br,2)}"]
            cases.append(dict(cq="CQ3",label=label,facts={round(cret,2),round(sr,2),round(br,2)},
                question=f"Did {label} outperform both its sector and the broad-market benchmark over the window? Explain, citing the source.",
                context="Facts in the validated graph:\n - "+"\n - ".join(atoms)+(f"\n - evidence: FY results announced {d} (source: {src})" if d else ""),
                onto=f"{label}: "+"; ".join(atoms)+f". Evidence: FY results announced {d} (source: {src}).", prov=prov))
        if gr is not None and br is not None and gr>0 and cret<br:
            atoms=[f"{label} YoY profit growth = {round(gr,2)}", f"{label} return = {round(cret,2)}", f"benchmark return = {round(br,2)}"]
            cases.append(dict(cq="CQ1",label=label,facts={round(gr,2),round(cret,2),round(br,2)},
                question=f"Did {label} report stronger fundamentals but a weaker market response than the benchmark? Explain, citing the source.",
                context="Facts in the validated graph:\n - "+"\n - ".join(atoms)+(f"\n - evidence: FY results announced {d} (source: {src})" if d else ""),
                onto=f"{label}: "+"; ".join(atoms)+f". Evidence: FY results announced {d} (source: {src}).", prov=prov))
    return cases

def score(ans,facts,prov,tol=0.05):
    ns=[round(float(x),2) for x in NUM.findall(ans)]
    mt=[n for n in ns if any(abs(n-t)<=tol for t in facts)]
    return {"nf":round(len(mt)/len(ns),3) if ns else 1.0,"halluc":len(ns)-len(mt),
            "unsup":len(PRED.findall(ans)),"prov":1 if any(t and str(t).lower() in ans.lower() for t in prov) else 0}

def main():
    os.makedirs(OUT,exist_ok=True)
    g=Graph().parse(TTL,format="turtle"); cases=build_scaled_cases(g)
    n=len(cases); n3=sum(c["cq"]=="CQ3" for c in cases); n1=sum(c["cq"]=="CQ1" for c in cases)
    print(f"scaled cases: {n}  (CQ3={n3}, CQ1={n1})")
    spec=os.environ.get("ONTOKG_LLM","")
    onto=[score(c["onto"],c["facts"],c["prov"]) for c in cases]
    def agg(ss,name):
        k=len(ss)
        return [name,k,round(sum(s["nf"] for s in ss)/k,3),round(sum(s["halluc"] for s in ss)/k,2),
                round(sum(s["unsup"] for s in ss)/k,2),round(sum(s["prov"] for s in ss)/k,2)]
    rows=[agg(onto,"OntoKG-EQ (provenance-grounded)")]
    if spec:
        import importlib; ga=importlib.import_module("graphrag_faithfulness")  # reuse llm_answer
        live=[score(ga.llm_answer(c["question"],c["context"]),c["facts"],c["prov"]) for c in cases]
        rows.append(agg(live,f"GraphRAG/LLM [{spec}]"))
    md=os.path.join(OUT,"graphrag_faithfulness_scaled.md")
    with open(md,"w") as f:
        f.write(f"# Faithfulness across the scaled IDX cohort ({n} cases: {n3} CQ3 + {n1} CQ1)\n\n")
        f.write("| Method | cases | numeric faithfulness | halluc. numbers | unsupported assertions | provenance |\n|---|---:|---:|---:|---:|---:|\n")
        for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} |\n")
        if not spec: f.write("\n> No LLM set; OntoKG-EQ reference only. Set ONTOKG_LLM=hf:Qwen/Qwen2.5-7B-Instruct on a GPU for live rows.\n")
    for r in rows: print("  ",r)
    print("wrote",md)

if __name__=="__main__": main()
