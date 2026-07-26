#!/usr/bin/env python3
"""Canonical, dependency-light reproduction of the Section 7.6 human-utility study.

Reads the raw Google Form export ("Form responses (17).xlsx") and computes the *participant-level*
statistics reported in Section 7.6 (each participant contributes one mean per condition, avoiding
pseudoreplication of the 8 nested item ratings). Uses only openpyxl + the standard library:
  * exact Wilcoxon signed-rank test (full sign enumeration; valid for n<=~20),
  * a participant bootstrap 95% CI (fixed seed for reproducibility),
  * an exact two-sided sign/binomial test on the per-participant preference.

Usage:  pip install openpyxl
        python analyze_expert_study.py ["Form responses (17).xlsx"]
Writes results.md (the paragraph reported in Section 7.6).
"""
import sys, os, statistics, random
from itertools import product
from math import comb
import openpyxl

SEED, BOOT = 12345, 10000
DEFAULT = "Form responses (17).xlsx"

def num(x):
    try: return float(x)
    except Exception: return None

def rankavg(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i]); ranks=[0.0]*len(vals); i=0
    while i < len(vals):
        j=i
        while j+1 < len(vals) and vals[order[j+1]]==vals[order[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i, j+1): ranks[order[k]]=avg
        i=j+1
    return ranks

def wilcoxon_exact(diffs):
    d=[x for x in diffs if x!=0]; n=len(d); r=rankavg([abs(x) for x in d])
    Wplus=sum(r[i] for i in range(n) if d[i]>0); mean=sum(r)/2; obs=abs(Wplus-mean)
    cnt=sum(1 for s in product((0,1), repeat=n)
            if abs(sum(r[i] for i in range(n) if s[i])-mean) >= obs-1e-9)
    return n, Wplus, cnt/(2**n)

def boot_ci(diffs, seed=SEED, B=BOOT):
    rnd=random.Random(seed); n=len(diffs); out=[]
    for _ in range(B):
        out.append(sum(diffs[rnd.randrange(n)] for _ in range(n))/n)
    out.sort(); return out[int(0.025*B)], out[int(0.975*B)-1]

def binom_two_sided(k, n, p=0.5):
    pr=[comb(n,i)*p**i*(1-p)**(n-i) for i in range(n+1)]
    return sum(x for x in pr if x <= pr[k]+1e-12)

def main():
    path=sys.argv[1] if len(sys.argv)>1 else DEFAULT
    if not os.path.exists(path):
        print(f"Raw export not found: {path}"); return
    ws=openpyxl.load_workbook(path, data_only=True).active
    rows=list(ws.iter_rows(values_only=True))[1:]
    P=[]
    for r in rows:
        if r[0] is None: continue
        TA=TB=CA=CB=None; ta=[];tb=[];ca=[];cb=[];pref=[]
        for k in range(8):
            b=4+6*k
            for lst,idx in ((ta,b),(ca,b+1),(tb,b+3),(cb,b+4)):
                v=num(r[idx])
                if v is not None: lst.append(v)
            p=str(r[b+5]); pref.append(p)
        P.append(dict(role=r[2], yrs=num(r[3]),
                      tA=statistics.mean(ta), tB=statistics.mean(tb),
                      cA=statistics.mean(ca), cB=statistics.mean(cb),
                      prefB=sum(1 for p in pref if p and p.strip().startswith('B'))))
    n=len(P)
    td=[p['tB']-p['tA'] for p in P]; cd=[p['cB']-p['cA'] for p in P]
    nt,Wt,pt=wilcoxon_exact(td); nc,Wc,pc=wilcoxon_exact(cd)
    tlo,thi=boot_ci(td); clo,chi=boot_ci(cd)
    allB=sum(1 for p in P if p['prefB']==8); majB=sum(1 for p in P if p['prefB']>4)
    yrs=[p['yrs'] for p in P if p['yrs'] is not None]
    L=[]
    L.append(f"# User study — results (executed, n = {n}; participant-level analysis)\n")
    L.append("Within-subject design; 8 real OntoKG-EQ statements; ad-hoc 7-point scales. "
             "Version A = result-only note, Version B = same statement with its provenance-grounded "
             "evidence bundle. **Analysis is at the participant level** (each participant contributes one "
             "mean per condition) to avoid pseudoreplicating the 8 nested item ratings.\n")
    L.append(f"| Measure | A (mean) | B (mean) | Δ (95% CI, participant bootstrap) | Test (participant-level, exact) |")
    L.append("|---|---:|---:|---|---|")
    L.append(f"| Trust | {statistics.mean([p['tA'] for p in P]):.2f} | {statistics.mean([p['tB'] for p in P]):.2f} "
             f"| +{statistics.mean(td):.2f} [{tlo:.2f}, {thi:.2f}] | Wilcoxon p = {pt:.1e} (n={nt}) |")
    L.append(f"| Completeness of justification | {statistics.mean([p['cA'] for p in P]):.2f} | {statistics.mean([p['cB'] for p in P]):.2f} "
             f"| +{statistics.mean(cd):.2f} [{clo:.2f}, {chi:.2f}] | Wilcoxon p = {pc:.1e} (n={nc}) |")
    L.append(f"| Preference | — | {allB}/{n} prefer B on all 8 items; {majB}/{n} on a majority | — "
             f"| sign test p = {binom_two_sided(majB,n):.1e} |")
    L.append("")
    if yrs: L.append(f"Participants: {n}; median experience {statistics.median(yrs):.0f} years (range {min(yrs):.0f}–{max(yrs):.0f}).")
    L.append(f"Completeness uses n={nc}: {sum(1 for d in cd if d==0)} participant(s) rated completeness "
             "identically for both versions (a zero difference the signed-rank test excludes).\n")
    L.append("NOTE: an earlier version reported item-level p-values (~1e-22); those were pseudoreplicated "
             "(treating the 8 nested ratings per participant as independent) and are superseded by the "
             "participant-level analysis above.")
    open("results.md","w",encoding="utf-8").write("\n".join(L)+"\n")
    print("\n".join(L)); print("\nWrote results.md")

if __name__ == "__main__":
    main()
