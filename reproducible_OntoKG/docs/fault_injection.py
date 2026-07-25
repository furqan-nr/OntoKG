#!/usr/bin/env python3
"""Fault-injection ablation: inject realistic data errors into a VALID market graph and measure
whether SHACL detects them. Unlike component-removal ablations, this tests error-detection capability.
Usage: pip install rdflib pyshacl ; python fault_injection.py [data/demo_psx.ttl]"""
import sys, copy
from rdflib import Graph, Namespace, Literal, URIRef, XSD
from rdflib.namespace import RDF
from pyshacl import validate
C=Namespace("https://w3id.org/ontokg-eq#")
TTL=sys.argv[1] if len(sys.argv)>1 else "data/demo_psx.ttl"
SH="shacl/shapes.ttl"
base=Graph().parse(TTL,format="turtle")
def first(cls): return next(base.subjects(RDF.type, cls), None)
def first_with(pred): 
    for s,p,o in base.triples((None,pred,None)): return s,o
    return None,None
def fresh(): return copy.deepcopy(base)
def check(g):
    conf,_,txt=validate(g, shacl_graph=SH, shacl_graph_format="turtle")
    # extract first violated shape/path
    tag=""
    for ln in txt.splitlines():
        ln=ln.strip()
        if ln.startswith("Source Shape:") or ln.startswith("Result Path:") or ln.startswith("Constraint Component:"):
            tag=ln; break
    return conf, tag

FAULTS=[]
# 1) wrong metric datatype (decimal -> string)
def f1():
    g=fresh(); s,o=first_with(C.hasMetricValue)
    g.remove((s,C.hasMetricValue,o)); g.add((s,C.hasMetricValue,Literal("not-a-number"))); return g,"wrong metric value datatype (decimal->string)"
# 2) missing company name
def f2():
    g=fresh(); c=first(C.Company); nm=next(g.objects(c,C.hasCompanyName),None)
    if nm is not None: g.remove((c,C.hasCompanyName,nm)); return g,"company missing hasCompanyName"
# 3) missing observation subject link
def f3():
    g=fresh(); s=first(C.MarketObservation); o=next(g.objects(s,C.isObservationOf),None)
    if o is not None: g.remove((s,C.isObservationOf,o)); return g,"market observation missing isObservationOf"
# 4) malformed announcement date (date -> string)
def f4():
    g=fresh(); a=first(C.Announcement); d=next(g.objects(a,C.hasAnnouncementDate),None)
    if d is not None: g.remove((a,C.hasAnnouncementDate,d)); g.add((a,C.hasAnnouncementDate,Literal("26 Feb 2026"))); return g,"malformed announcement date (date->string)"
# 5) observation missing metric name
def f5():
    g=fresh(); s=first(C.MarketObservation); mn=next(g.objects(s,C.hasMetricName),None)
    if mn is not None: g.remove((s,C.hasMetricName,mn)); return g,"observation missing hasMetricName"
# 6) wrong reporting-period class (link to a non-ReportingPeriod node)
def f6():
    g=fresh(); s=first(C.FundamentalObservation); p=next(g.objects(s,C.observedInPeriod),None)
    if p is not None:
        g.remove((s,C.observedInPeriod,p)); g.add((s,C.observedInPeriod,URIRef("https://w3id.org/ontokg-eq/psx#NOT_A_PERIOD"))); return g,"fundamental linked to wrong reporting-period class"
# 7) duplicate metric value (violates maxCount 1)
def f7():
    g=fresh(); s,o=first_with(C.hasMetricValue); g.add((s,C.hasMetricValue,Literal(999.99,datatype=XSD.decimal))); return g,"duplicate hasMetricValue (maxCount 1)"
# 8) evidence item missing source
def f8():
    g=fresh(); e=first(C.EvidenceItem) or first(C.Announcement); src=next(g.objects(e,C.hasEvidenceSource),None)
    if src is not None: g.remove((e,C.hasEvidenceSource,src)); return g,"evidence item missing hasEvidenceSource"

rows=[]
for fn in [f1,f2,f3,f4,f5,f6,f7,f8]:
    r=fn()
    if not r: continue
    g,desc=r; conf,tag=check(g)
    detected = (conf is False)
    rows.append((desc, "DETECTED" if detected else "missed"))
det=sum(1 for _,s in rows if s=="DETECTED")
print(f"Injected faults: {len(rows)}  |  Detected by SHACL: {det}/{len(rows)}\n")
for d,s in rows: print(f"  [{s:8s}] {d}")
# save
with open("evaluation_faithfulness/fault_injection.md","w") as f:
    f.write("# Fault-injection ablation (error-detection, not component removal)\n\n")
    f.write(f"Valid graph: `{TTL}` (SHACL-conformant). Each row injects one realistic data error into a fresh copy; we report whether SHACL detects it. **Detected {det}/{len(rows)}.**\n\n")
    f.write("| Injected fault | SHACL result |\n|---|---|\n")
    for d,s in rows: f.write(f"| {d} | {'detected (non-conformant)' if s=='DETECTED' else 'not detected'} |\n")
print("\nsaved evaluation_faithfulness/fault_injection.md")
