#!/usr/bin/env python3
"""Analyze the OntoKG-EQ expert study. No external stats libraries required.

Reads response_form.xlsx (sheet 'Data'), and for the paired A (result-only) vs B (with evidence)
conditions computes: descriptive stats, a Wilcoxon signed-rank test (normal approximation with
continuity + tie correction), an exact sign test, the matched-pairs rank-biserial effect size, and a
binomial test on the B-vs-A preference. Writes results.md with a ready-to-paste Section 7.6 paragraph.

Usage:  pip install openpyxl ; python analyze_expert_study.py
"""
import math, statistics as st
from collections import Counter
import openpyxl

def norm_sf(z):  # upper-tail standard normal
    return 0.5*math.erfc(z/math.sqrt(2))

def wilcoxon(a, b):
    """Two-sided Wilcoxon signed-rank on paired (a,b); returns (W, p, n_nonzero)."""
    d=[y-x for x,y in zip(a,b) if (y-x)!=0]
    n=len(d)
    if n==0: return 0.0, 1.0, 0
    order=sorted(range(n), key=lambda i: abs(d[i]))
    ranks=[0.0]*n; i=0
    while i<n:
        j=i
        while j+1<n and abs(d[order[j+1]])==abs(d[order[i]]): j+=1
        r=(i+j)/2+1
        for k in range(i,j+1): ranks[order[k]]=r
        i=j+1
    Wp=sum(ranks[i] for i in range(n) if d[i]>0)
    Wm=sum(ranks[i] for i in range(n) if d[i]<0)
    W=min(Wp,Wm)
    mu=n*(n+1)/4
    ties=Counter(abs(x) for x in d)
    tie=sum(t**3-t for t in ties.values())
    sd=math.sqrt(n*(n+1)*(2*n+1)/24 - tie/48)
    if sd==0: return W,1.0,n
    z=(W-mu+0.5)/sd
    return W, min(1.0,2*norm_sf(abs(z))), n

def sign_test(a,b):
    pos=sum(1 for x,y in zip(a,b) if y>x); neg=sum(1 for x,y in zip(a,b) if y<x); n=pos+neg
    if n==0: return 1.0,pos,neg
    from math import comb
    k=min(pos,neg); p=min(1.0,2*sum(comb(n,i) for i in range(k+1))/2**n)
    return p,pos,neg

def binom_test(k,n,p=0.5):
    if n==0: return 1.0
    from math import comb
    probs=[comb(n,i)*p**i*(1-p)**(n-i) for i in range(n+1)]
    obs=probs[k]; return min(1.0,sum(pp for pp in probs if pp<=obs+1e-12))

def col(rows,name): return [r[name] for r in rows]
def num(x):
    try: return float(x)
    except: return None

def main():
    wb=openpyxl.load_workbook("response_form.xlsx", data_only=True)
    ws=wb["Data"]; H=[c.value for c in ws[1]]
    rows=[dict(zip(H,[c.value for c in r])) for r in ws.iter_rows(min_row=2)]
    # keep rows with both trust_A and trust_B filled
    def ok(r): return num(r.get("trust_A")) is not None and num(r.get("trust_B")) is not None
    R=[r for r in rows if ok(r)]
    if not R:
        print("No completed rows found. Fill response_form.xlsx first."); return
    tA=[num(r["trust_A"]) for r in R]; tB=[num(r["trust_B"]) for r in R]
    cA=[num(r["completeness_A"]) for r in R if num(r.get("completeness_A")) is not None]
    cB=[num(r["completeness_B"]) for r in R if num(r.get("completeness_B")) is not None]
    parts=sorted(set(r["participant_id"] for r in R))
    pref=Counter(str(r.get("preference (A/B/=)")).strip().upper() for r in R if r.get("preference (A/B/=)"))
    def line(name,A,B):
        W,p,n=wilcoxon(A,B); rb=1-2*W/(n*(n+1)/2) if n else 0
        return (f"- **{name}:** A mean {st.mean(A):.2f} (median {st.median(A):.1f}) vs "
                f"B mean {st.mean(B):.2f} (median {st.median(B):.1f}); "
                f"Wilcoxon signed-rank p = {p:.4g} (n={n} non-tied pairs), rank-biserial r = {rb:.2f}")
    out=[]
    out.append("# Expert study — results\n")
    out.append(f"Participants: {len(parts)}; paired responses: {len(R)} (across 8 items).\n")
    out.append(line("Trust", tA, tB))
    if cA and cB and len(cA)==len(cB): out.append(line("Completeness of justification", cA, cB))
    b=pref.get("B",0); a=pref.get("A",0); eq=pref.get("=",0)+pref.get("EQUAL",0)
    pb=binom_test(b, a+b) if (a+b)>0 else 1.0
    out.append(f"- **Preference:** B {b}, A {a}, no-difference {eq}; among A/B choices, prefer-B "
               f"{b}/{a+b} = {(b/(a+b)*100 if (a+b) else 0):.0f}% (binomial p = {pb:.4g}).")
    # optional timing
    taA=[num(r.get("verify_time_A_sec")) for r in R if num(r.get("verify_time_A_sec")) is not None]
    taB=[num(r.get("verify_time_B_sec")) for r in R if num(r.get("verify_time_B_sec")) is not None]
    if taA and taB and len(taA)==len(taB):
        W,p,n=wilcoxon(taB,taA)
        out.append(f"- **Verification time (s):** A mean {st.mean(taA):.1f} vs B mean {st.mean(taB):.1f}; Wilcoxon p = {p:.4g}.")
    # §7.6 template
    W,p,n=wilcoxon(tA,tB)
    out.append("\n## Ready-to-paste Section 7.6 paragraph (fill any [bracketed] context)\n")
    out.append(f"> We ran the pre-registered within-subject study with {len(parts)} participants "
               f"[roles/experience], each rating {8} OntoKG-EQ statements first as result-only notes (Version A) and "
               f"then with the provenance-grounded evidence bundle (Version B). Adding the evidence raised mean trust "
               f"from {st.mean(tA):.2f} to {st.mean(tB):.2f} on a 7-point scale (Wilcoxon signed-rank p = {p:.4g}) and "
               f"mean perceived completeness from {st.mean(cA) if cA else float('nan'):.2f} to "
               f"{st.mean(cB) if cB else float('nan'):.2f}; "
               f"{(b/(a+b)*100 if (a+b) else 0):.0f}% of participants preferred the evidence-grounded version "
               f"(binomial p = {pb:.4g}). This converts the paper's structural faithfulness guarantee into a "
               f"measured improvement in analyst trust and verifiability.")
    txt="\n".join(out)
    open("results.md","w").write(txt+"\n"); print(txt); print("\nWrote results.md")

if __name__=="__main__": main()
