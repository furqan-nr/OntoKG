#!/usr/bin/env python3
"""OntoKG-EQ figures (vector PDF/SVG + PNG), styled to standard journal conventions
(no in-figure title; 'Fig. N.' caption supplied in the manuscript; clean sans-serif;
coherent limited palette with the market-dependent layer highlighted). Vector PDF+SVG + PNG.
Run: python make_figures.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
matplotlib.rcParams.update({"pdf.fonttype":42, "ps.fonttype":42,
                            "font.family":"DejaVu Sans", "font.size":9})

NAVY="#16334f"; INK="#1a2730"; EDGE="#9aa7b3"; ARROW="#5f7488"
BLUE="#dCE6F2"; CORE_BLUES=["#e3edf6","#d7e4f1","#cbdcec","#bfd4e7","#b3cce2","#a7c4dd"]
ORANGE="#f3d6b0"; ORANGE_EDGE="#c79a6a"; GREEN_OK="#3a7d44"

def rbox(ax,x,y,w,h,fc,ec,lw=0.9,r=0.015):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",
                 fc=fc,ec=ec,lw=lw,mutation_aspect=1))
def darrow(ax,x,y0,y1,color=ARROW,lw=1.7,ms=12):
    ax.add_patch(FancyArrowPatch((x,y0),(x,y1),arrowstyle="-|>",mutation_scale=ms,lw=lw,color=color))

# ---------------- Figure 1 ----------------
def figure1():
    fig,ax=plt.subplots(figsize=(7.4,4.9)); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,100)
    rows=[
        ("Query\nexecution",
         r"$\bf{Analyst\ question\ (CQ3)}$" "\nWhich companies outperformed both their sector and the\n"
         "broad-market benchmark over the post-report window?  (IDX, FY2025)", 15),
        ("Result entity",
         "ISAT (PT Indosat Ooredoo Hutchison)        relative-outperformer", 8.5),
        ("Deciding\nobservations",
         "ISAT post-report window return  =  −0.74%\nTelecommunications sector return  =  −1.61%\n"
         "JCI (Jakarta Composite) benchmark return  =  −9.48%\n"
         r"$\Rightarrow$  −0.74% beats sector (−1.61%) and benchmark (−9.48%)", 18),
        ("Evidence item","ISAT FY2025 audited results  (announced 2026-02-09)", 8.5),
        ("Official source","Indonesia Stock Exchange (IDX) official disclosure", 8.5),
        ("Provenance\nrecord","Retrieved 2026-06-28 · unadjusted daily close · 83 exact shared trading dates", 8.5),
    ]
    gap=3.0; top=90.0; lx=1.0; lw_=18.0; cx=20.5; cw=78.5
    rbox(ax,80.0,94.5,19.0,4.4,"#eaf3ea",GREEN_OK,lw=0.9)
    ax.text(89.5,96.7,"SHACL: Conforms ✓",ha="center",va="center",fontsize=8,color="#2f5d36")
    y=top; ys=[]
    for label,content,h in rows:
        rbox(ax,lx,y-h,lw_,h,NAVY,NAVY)
        ax.text(lx+lw_/2,y-h/2,label,ha="center",va="center",color="white",fontsize=9.5,fontweight="bold")
        rbox(ax,cx,y-h,cw,h,"#eef3f8",EDGE,lw=0.9)
        ax.text(cx+2.0,y-h/2,content,ha="left",va="center",color=INK,fontsize=8.0)
        ys.append((y,y-h)); y=y-h-gap
    for i in range(len(rows)-1):
        darrow(ax,cx+cw/2,ys[i][1]-0.2,ys[i+1][0]+0.2)
    fig.tight_layout(pad=0.2)
    for e in ("pdf","svg","png"): fig.savefig(f"figures/figure1_worked_example.{e}",dpi=300,bbox_inches="tight")
    plt.close(fig); print("Figure 1 written")

# ---------------- Figure 2 ----------------
def figure2():
    fig,ax=plt.subplots(figsize=(7.0,4.5)); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,100)
    layers=[
        ("L0","Source","Per-market sheets: fundamentals, FX, disclosures", ORANGE, ORANGE_EDGE, True),
        ("L1","Materialization","Provenance-aware RDF aligned to core ontology", CORE_BLUES[0], EDGE, False),
        ("L2","Derived metrics","returns, YoY growth, FX, event-window metrics", CORE_BLUES[1], EDGE, False),
        ("L3","SHACL validation","gate: Conforms = True", CORE_BLUES[2], EDGE, False),
        ("L4","CQ answering","CQ1–CQ5 SPARQL templates (stated conditions)", CORE_BLUES[3], EDGE, False),
        ("L5","Inference","rules R1–R4 → typed AnalyticalFindings", CORE_BLUES[4], EDGE, False),
        ("L6","Automated explanation","EvidenceBundle + QueryExecution (evidence trail)", CORE_BLUES[5], EDGE, False),
    ]
    cx=27.0; cw=61.0; top=80.0; h=8.4; gap=1.6
    # market chips (one muted family) feeding L0
    for i,m in enumerate(["PSX","MSX","IDX"]):
        bx=39.0+i*13.5
        rbox(ax,bx,90.5,10.0,6.2,"#5f7488","#5f7488",r=0.03)
        ax.text(bx+5.0,93.6,m,ha="center",va="center",color="white",fontweight="bold",fontsize=10.5)
        ax.add_patch(FancyArrowPatch((bx+5.0,90.5),(bx+5.0,top+0.8),arrowstyle="-|>",
                     mutation_scale=10,lw=1.4,color="#9aa7b3"))
    ys=[]; y=top
    for code,title,desc,fc,ec,dep in layers:
        rbox(ax,cx,y-h,cw,h,fc,ec,lw=0.9)
        ax.text(cx+1.6,y-h/2,code,ha="left",va="center",fontweight="bold",fontsize=12,color=NAVY)
        ax.text(cx+8.5,y-h*0.34,title,ha="left",va="center",fontweight="bold",fontsize=10.5,color=INK)
        ax.text(cx+8.5,y-h*0.72,desc,ha="left",va="center",fontsize=8.5,color="#33414d")
        ys.append((y,y-h)); y=y-h-gap
    rbox(ax,88.6,top-h,6.6,h,ORANGE,ORANGE_EDGE,lw=0.9)
    ax.text(91.9,top-h/2,"adapter\nconfig",ha="center",va="center",fontsize=8.0,color=INK)
    for i in range(len(layers)-1):
        ax.add_patch(FancyArrowPatch((cx+cw/2,ys[i][1]-0.15),(cx+cw/2,ys[i+1][0]+0.15),
                     arrowstyle="-|>",mutation_scale=10,lw=1.5,color=ARROW))
    ax.text(cx,top+1.4,"market-dependent",ha="left",va="bottom",fontsize=8.6,fontweight="bold",color="#a8631e")
    # left core column + band
    core=["Core ontology","SHACL shapes","CQ queries","Inference rules"]
    bx=12.5; bw=12.0; bh=7.0
    for j,name in enumerate(core):
        yy=(top-h)-j*(bh+2.1)
        rbox(ax,bx,yy-bh,bw,bh,"#eef2f6",EDGE,lw=0.9)
        ax.text(bx+bw/2,yy-bh/2,name,ha="center",va="center",fontsize=8.8,color=INK)
    band_top=ys[1][0]+0.4; band_bot=ys[-1][1]-0.4
    rbox(ax,1.2,band_bot,8.7,band_top-band_bot,"#e7eef5",EDGE,lw=0.9)
    ax.text(5.5,(band_top+band_bot)/2,"market-independent core\nreused byte-identical · 13 artifacts (100%)",
            ha="center",va="center",rotation=90,fontsize=8.8,fontweight="bold",color=NAVY)
    rbox(ax,95.6,ys[-1][1]-0.4,3.6,top-(ys[-1][1]-0.4),"#fbeede",ORANGE_EDGE,lw=0.9)
    ax.text(97.4,(top+ys[-1][1])/2,"market-dependent\nonly data + adapter",
            ha="center",va="center",rotation=90,fontsize=8.2,fontweight="bold",color="#a8631e")
    fig.tight_layout(pad=0.2)
    for e in ("pdf","svg","png"): fig.savefig(f"figures/figure2_architecture.{e}",dpi=300,bbox_inches="tight")
    plt.close(fig); print("Figure 2 written")

figure1(); figure2()
