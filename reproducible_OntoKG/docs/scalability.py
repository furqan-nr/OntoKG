#!/usr/bin/env python3
import os, glob, time
from rdflib import Graph, URIRef
from pyshacl import validate
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSX_NS="https://w3id.org/ontokg-eq/psx#"
base=Graph().parse(os.path.join(HERE,"data","demo_psx.ttl"),format="turtle")
shapes=Graph().parse(os.path.join(HERE,"shacl","shapes.ttl"),format="turtle")
queries=[(os.path.basename(q).split('_')[0],open(q).read()) for q in sorted(glob.glob(os.path.join(HERE,"queries","CQ*_CASE_01.rq")))]
def scaled(k):
    g=Graph()
    for c in range(k):
        suf=f"_c{c}"
        for s,p,o in base:
            ns=URIRef(str(s)+suf) if isinstance(s,URIRef) and str(s).startswith(PSX_NS) else s
            no=URIRef(str(o)+suf) if isinstance(o,URIRef) and str(o).startswith(PSX_NS) else o
            g.add((ns,p,no))
    return g
md=os.path.join(HERE,"evaluation","scalability_results.md")
f=open(md,"w")
f.write("# Scalability (C3)\n\nPSX graph replicated (constant schema, multiplied instances); rdflib in-memory + pySHACL on the VM.\n\n")
f.write("## Per-CQ query latency vs graph size (seconds)\n\n| scale x | triples | CQ1 | CQ2 | CQ3 | CQ4 | CQ5 | SHACL | conforms |\n|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
f.flush()
for k in [1,5,10]:
    g=scaled(k); n=len(g); times={}
    for fam,q in queries:
        t0=time.perf_counter(); list(g.query(q)); times[fam]=time.perf_counter()-t0
    t0=time.perf_counter(); c,_,_=validate(g,shacl_graph=shapes); sh=time.perf_counter()-t0
    line=f"| {k} | {n:,} | "+" | ".join(f"{times[fam]:.2f}" for fam,_ in queries)+f" | {sh:.2f} | {c} |\n"
    f.write(line); f.flush()
    print(f"x{k} n={n} done", flush=True)
f.close(); print("wrote",md,flush=True)
