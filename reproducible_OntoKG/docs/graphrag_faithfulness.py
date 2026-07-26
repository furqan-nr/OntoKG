#!/usr/bin/env python3
"""
Empirical explanation-faithfulness experiment: GraphRAG/LLM answering vs the OntoKG-EQ
provenance-grounded path, over the SAME validated knowledge graph.

For every worked CQ result (relative-outperformer / fundamentals-market-divergence findings across
markets) the harness: (1) retrieves the finding's evidence bundle as the ground-truth fact set,
(2) linearizes that subgraph as the GraphRAG context + the analyst question, (3) obtains an answer
(OntoKG-EQ reference rendered from the bundle, or an LLM answer), and (4) scores it automatically:
  numeric_faithfulness   = answer numbers entailed by the graph / answer numbers
  hallucinated_numbers   = answer numbers absent from the graph
  unsupported_assertions = predictive/causal claims with no graph support
  provenance_coverage    = 1 if the official source/announcement is cited, else 0

LLM provider is pluggable via the ONTOKG_LLM env var (no paid key required if you use a local model):
  ONTOKG_LLM=hf:Qwen/Qwen2.5-7B-Instruct   # local open-weight model (Kaggle free GPU) — recommended
  ONTOKG_LLM=openai:gpt-4o-mini            # needs OPENAI_API_KEY
  ONTOKG_LLM=anthropic:claude-3-5-haiku    # needs ANTHROPIC_API_KEY
  ONTOKG_LLM=gemini:gemini-1.5-flash       # needs GOOGLE_API_KEY (free tier from aistudio.google.com)
Output dir via ONTOKG_OUT (default: ../evaluation). With no provider set, only the OntoKG-EQ reference
and controlled answer variants are scored (validates the metric on a machine without model access).
"""
import os, re, glob, csv
from rdflib import Graph, RDF, URIRef
from rdflib.namespace import Namespace
CORE = Namespace("https://w3id.org/ontokg-eq#")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.environ.get("ONTOKG_OUT", os.path.join(HERE, "evaluation"))
PRED = re.compile(r"\b(because|due to|driven by|will|likely|expected to|forecast|predict|target|recommend|buy|sell|cause|outlook|going to|should)\b", re.I)
NUM  = re.compile(r"-?\d+\.\d+")

def short(x): return str(x).split("#")[-1] if x else ""

def build_cases():
    """Yield worked cases across the three markets (CQ3 outperformer + CQ1 divergence findings)."""
    cases=[]
    for m in ["psx","msx","idx"]:
        fp=os.path.join(HERE,"data",f"demo_{m}_inferred.ttl")
        if not os.path.exists(fp): continue
        g=Graph().parse(fp,format="turtle")
        for f in g.subjects(RDF.type, CORE.AnalyticalFinding):
            ftype=str(next(g.objects(f, CORE.hasFindingType),""))
            if ftype not in ("relative-outperformer","fundamentals-market-divergence"): continue
            ent=next(g.objects(f, CORE.concernsEntity), None)
            label=str(next(g.objects(ent, CORE.hasCompanyName), short(ent)))
            bundle=URIRef(str(f)+"_bundle"); atoms=[]; nums=[]
            for o in g.objects(bundle, CORE.includesObservation):
                mn=str(next(g.objects(o, CORE.hasMetricName),"")); v=next(g.objects(o, CORE.hasMetricValue),None)
                tgt=short(next(g.objects(o, CORE.isObservationOf), None))
                if v is not None:
                    fv=round(float(v),2); atoms.append(f"{tgt} {mn} = {fv}"); nums.append(fv)
            ev=next(g.objects(bundle, CORE.containsEvidenceItem), None)
            date=str(next(g.objects(ev, CORE.hasAnnouncementDate),"")) if ev else ""
            src=next(g.objects(ev, CORE.hasEvidenceSource), None) if ev else None
            srctype=str(next(g.objects(src, CORE.hasSourceType),"")) if src else ""
            ctx="Facts present in the validated knowledge graph:\n - " + "\n - ".join(atoms)
            if date: ctx+=f"\n - evidence: {label} FY results announced {date}"
            if src:  ctx+=f"\n - source: {short(src)} ({srctype})"
            if ftype=="relative-outperformer":
                q=f"Did {label} outperform both its sector and the broad-market benchmark over the post-report window? Explain, citing the evidence."
            else:
                q=f"Did {label} show stronger fundamentals but a weaker market response than the benchmark? Explain, citing the evidence."
            onto=(f"{label}: " + "; ".join(atoms) + ". "
                  + (f"Evidence: FY results announced {date} (source: {short(src)})." if src else ""))
            cases.append(dict(market=m,label=label,ftype=ftype,question=q,context=ctx,
                              factnums=set(round(n,2) for n in nums),
                              prov_tokens=[date, short(src) if src else ""],   # specific source/date only (no generic tokens)
                              onto_answer=onto))
    return cases

def score(answer, factnums, prov_tokens, tol=0.05):
    nums=[round(float(x),2) for x in NUM.findall(answer)]
    matched=[n for n in nums if any(abs(n-t)<=tol for t in factnums)]
    nf=(len(matched)/len(nums)) if nums else 1.0                  # PRECISION: stated numbers that are correct
    facts=list(factnums)
    recalled=[t for t in facts if any(abs(n-t)<=tol for n in nums)]
    nrec=(len(recalled)/len(facts)) if facts else 1.0            # RECALL/COMPLETENESS: expected facts actually stated
    return {"numbers":len(nums),"num_faithful":round(nf,2),"num_recall":round(nrec,2),
            "halluc_numbers":len(nums)-len(matched),
            "unsupported_assertions":len(PRED.findall(answer)),
            "provenance":1 if any(t and t.lower() in answer.lower() for t in prov_tokens) else 0}

# ---------------- pluggable LLM ----------------
_PIPE=None
def llm_answer(question, context):
    spec=os.environ.get("ONTOKG_LLM","")
    if not spec: return None
    provider,_,model=spec.partition(":")
    prompt=(f"You are a financial analysis assistant. Answer ONLY using the facts in the context; "
            f"cite the official source. Be concise (2-3 sentences).\n\nQuestion: {question}\n\nContext:\n{context}\n\nAnswer:")
    if provider=="hf":
        global _PIPE
        if _PIPE is None:
            from transformers import pipeline
            import torch
            try:
                _PIPE=pipeline("text-generation",model=model,model_kwargs={"load_in_4bit":True},
                               device_map="auto",torch_dtype=torch.float16)
            except Exception:
                _PIPE=pipeline("text-generation",model=model,device_map="auto",torch_dtype=torch.float16)
        msgs=[{"role":"user","content":prompt}]
        out=_PIPE(msgs,max_new_tokens=200,do_sample=False)
        gen=out[0]["generated_text"]
        return gen[-1]["content"] if isinstance(gen,list) else str(gen)
    if provider=="openai":
        from openai import OpenAI
        c=OpenAI()
        r=c.chat.completions.create(model=model or "gpt-4o-mini",messages=[{"role":"user","content":prompt}])
        return r.choices[0].message.content
    if provider=="anthropic":
        import anthropic
        c=anthropic.Anthropic()
        r=c.messages.create(model=model or "claude-3-5-haiku-20241022",max_tokens=300,
                            messages=[{"role":"user","content":prompt}])
        return r.content[0].text
    if provider=="gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        return genai.GenerativeModel(model or "gemini-1.5-flash").generate_content(prompt).text
    return None

def main():
    os.makedirs(OUT, exist_ok=True)
    cases=build_cases()
    print(f"worked cases: {len(cases)}  ({sum(c['ftype']=='relative-outperformer' for c in cases)} outperformer, "
          f"{sum(c['ftype']=='fundamentals-market-divergence' for c in cases)} divergence)")
    spec=os.environ.get("ONTOKG_LLM","")

    rows=[]  # aggregate rows
    # OntoKG-EQ reference across all cases (faithful by construction)
    onto=[score(c["onto_answer"],c["factnums"],c["prov_tokens"]) for c in cases]
    def agg(ss,name):
        n=len(ss)
        return [name,n,round(sum(s["num_faithful"] for s in ss)/n,3),
                round(sum(s["num_recall"] for s in ss)/n,3),
                round(sum(s["halluc_numbers"] for s in ss)/n,2),
                round(sum(s["unsupported_assertions"] for s in ss)/n,2),
                round(sum(s["provenance"] for s in ss)/n,2)]
    rows.append(agg(onto,"OntoKG-EQ (provenance-grounded)"))

    live=[]
    if spec:
        print(f"LLM provider: {spec} — generating answers for {len(cases)} cases ...")
        for c in cases:
            a=llm_answer(c["question"],c["context"])
            if a: live.append(score(a,c["factnums"],c["prov_tokens"]))
        if live: rows.append(agg(live,f"GraphRAG/LLM [{spec}]"))

    # controlled metric-validation variants on the first case (always; validates the scorer)
    c0=cases[0]; nums=sorted(c0["factnums"])
    variants={
      "  variant: faithful": c0["onto_answer"],
      "  variant: numeric hallucination": f"{c0['label']}: return 99.99; "+ "; ".join(f"x = {n}" for n in nums[:2]) + f". Source: {c0['prov_tokens'][1]}.",
      "  variant: unsupported assertion": c0["onto_answer"]+" It is likely to keep rising because of strong momentum.",
      "  variant: missing provenance": "; ".join(f"x = {n}" for n in nums)+".",
      "  variant: omission (no numbers)": f"{c0['label']} outperformed both its sector and the broad-market benchmark over the window. Source: {c0['prov_tokens'][1]}.",
    }
    vrows=[(k,score(v,c0["factnums"],c0["prov_tokens"])) for k,v in variants.items()]

    # write outputs
    with open(os.path.join(OUT,"graphrag_faithfulness.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["method","cases/answers","numeric precision (mean)","numeric recall (mean)",
            "hallucinated numbers (mean)","unsupported assertions (mean)","provenance coverage (mean)"])
        for r in rows: w.writerow(r)
        for k,sc in vrows: w.writerow([k.strip(),1,sc["num_faithful"],sc["num_recall"],sc["halluc_numbers"],sc["unsupported_assertions"],sc["provenance"]])
    with open(os.path.join(OUT,"graphrag_faithfulness.md"),"w") as f:
        f.write("# Explanation faithfulness: GraphRAG/LLM vs OntoKG-EQ (D5)\n\n")
        f.write(f"Worked cases: {len(cases)} (CQ3 outperformer + CQ1 divergence findings across PSX/MSX/IDX). "
                "Scored automatically against the validated graph.\n\n")
        f.write("| Method | cases | numeric precision | numeric recall | halluc. numbers | unsupported assertions | provenance |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for r in rows: f.write(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} | {r[6]:.2f} |\n")
        f.write("\n*Controlled metric-validation variants (single case; confirm each failure detector):*\n\n")
        f.write("| Variant | numeric precision | numeric recall | halluc. numbers | unsupported assertions | provenance |\n|---|---:|---:|---:|---:|---:|\n")
        for k,sc in vrows: f.write(f"| {k.strip()} | {sc['num_faithful']:.2f} | {sc['num_recall']:.2f} | {sc['halluc_numbers']} | {sc['unsupported_assertions']} | {sc['provenance']} |\n")
        if not spec:
            f.write("\n> No LLM provider set (ONTOKG_LLM unset): only the OntoKG-EQ reference and controlled "
                    "variants are scored. Set ONTOKG_LLM (e.g. `hf:Qwen/Qwen2.5-7B-Instruct` on a free GPU) "
                    "to append a live GraphRAG/LLM row.\n")
    print("rows:"); [print("  ",r) for r in rows]
    print("wrote", os.path.join(OUT,"graphrag_faithfulness.md"))

if __name__ == "__main__":
    main()
