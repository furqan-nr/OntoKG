#!/usr/bin/env python3
"""Controlled scaling benchmark on Oxigraph (on-disk). Replicates the 64-stock IDX graph K times
(distinct instance IRIs) to hit target sizes; measures ingest + unchanged-CQ latency."""
import sys, os, time, tempfile, shutil
from rdflib import Graph, URIRef, Literal
import pyoxigraph as ox
INST="https://w3id.org/ontokg-eq/idxscaled#"
base=Graph().parse("data/demo_idx_scaled.ttl",format="turtle")
def ntlit(t):
    v=str(t).replace("\\","\\\\").replace('"','\\"').replace("\n","\\n")
    if t.language: return f'"{v}"@{t.language}'
    if t.datatype: return f'"{v}"^^<{t.datatype}>'
    return f'"{v}"'
# precompute templates: (s_base, s_inst, p_str, o_base, o_inst)
TPL=[]
for s,p,o in base:
    s_inst=isinstance(s,URIRef) and str(s).startswith(INST)
    o_inst=isinstance(o,URIRef) and str(o).startswith(INST)
    s_b=str(s) if s_inst else (f"<{s}>" if isinstance(s,URIRef) else ntlit(s))
    o_b=str(o) if o_inst else (f"<{o}>" if isinstance(o,URIRef) else ntlit(o))
    TPL.append((s_b,s_inst,f"<{p}>",o_b,o_inst))
def build_nt(K,path):
    with open(path,"w",encoding="utf-8") as f:
        for k in range(K):
            suf=f"_r{k}>"
            buf=[]
            for s_b,s_i,p,o_b,o_i in TPL:
                s=f"<{s_b}{suf}" if s_i else s_b
                o=f"<{o_b}{suf}" if o_i else o_b
                buf.append(f"{s} {p} {o} .")
            f.write("\n".join(buf)+"\n")
CQ={n:open(f"queries/CQ{n}_CASE_01.rq").read() for n in (1,3)}
Ks=[int(x) for x in (sys.argv[1] if len(sys.argv)>1 else "3").split(",")]
import json
results_path="evaluation_faithfulness/_scaling_rows.json"
rows=[]   # fresh each run (no append: avoids duplicate rows on re-run)
for K in Ks:
    d=tempfile.mkdtemp(); nt=os.path.join(d,"g.nt"); sd=os.path.join(d,"store")
    t0=time.perf_counter(); build_nt(K,nt); bt=time.perf_counter()-t0
    store=ox.Store(sd); t0=time.perf_counter()
    with open(nt,"rb") as fp: store.load(fp, format=ox.RdfFormat.N_TRIPLES)
    ingest=time.perf_counter()-t0; n=len(store)
    lat={}
    for cq,q in CQ.items():
        best=1e9;c=0
        for _ in range(3):
            s=time.perf_counter(); r=list(store.query(q)); best=min(best,(time.perf_counter()-s)*1000); c=len(r)
        lat[cq]=[c,round(best,1)]
    rows.append({"triples":n,"build_s":round(bt,1),"ingest_s":round(ingest,1),"lat":lat})
    json.dump(rows,open(results_path,"w"))
    print(f"triples={n:,} build={bt:.1f}s ingest={ingest:.1f}s CQ1={lat[1]} CQ3={lat[3]}",flush=True)
    del store; shutil.rmtree(d,ignore_errors=True)

# regenerate committed artifacts (JSON + Markdown) from THIS run
os.makedirs("evaluation_faithfulness", exist_ok=True)
json.dump(rows, open(results_path,"w"), indent=2)
with open("evaluation_faithfulness/scaling_benchmark.md","w") as f:
    f.write("# Controlled scaling benchmark (Oxigraph, on-disk) - unchanged CQ1/CQ3\n\n")
    f.write("Replicated 64-stock IDX graph to larger sizes. On-disk Oxigraph store; "
            "latency = best of 3 timed runs per scale. Representative run.\n\n")
    f.write("| Triples | Ingest (s) | CQ1 rows | CQ1 latency (ms) | CQ3 rows | CQ3 latency (ms) |\n")
    f.write("|---:|---:|---:|---:|---:|---:|\n")
    for r in rows:
        f.write(f"| {r['triples']:,} | {r['ingest_s']} | {r['lat'][1][0]} | {r['lat'][1][1]} | {r['lat'][3][0]} | {r['lat'][3][1]} |\n")
print("wrote evaluation_faithfulness/scaling_benchmark.md")
