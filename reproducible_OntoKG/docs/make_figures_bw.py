#!/usr/bin/env python3
"""OntoKG-EQ manuscript figures in a print-safe grayscale scheme.

No in-figure title; captions are supplied in the manuscript. Outputs vector
PDF/SVG and high-resolution PNG files. Text sizes are increased to make better
use of the available box area.

Run: python make_figures_bw.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

matplotlib.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
})

# Print-safe monochrome palette.
BLACK = "#111111"
INK = "#202020"
DARK = "#3a3a3a"
MID_DARK = "#626262"
MID = "#8a8a8a"
EDGE = "#969696"
ARROW = "#686868"
LIGHT = "#eeeeee"
VERY_LIGHT = "#f7f7f7"
CORE_GREYS = ["#f1f1f1", "#e9e9e9", "#e1e1e1", "#d9d9d9", "#d1d1d1", "#c9c9c9"]
HIGHLIGHT = "#d7d7d7"
HIGHLIGHT_EDGE = "#777777"

OUTDIR = Path(__file__).resolve().parent / "figures_bw"
OUTDIR.mkdir(parents=True, exist_ok=True)


def rbox(ax, x, y, w, h, fc, ec, lw=0.9, r=0.015):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        fc=fc, ec=ec, lw=lw, mutation_aspect=1,
    ))


def darrow(ax, x, y0, y1, color=ARROW, lw=1.7, ms=12):
    ax.add_patch(FancyArrowPatch(
        (x, y0), (x, y1), arrowstyle="-|>", mutation_scale=ms,
        lw=lw, color=color,
    ))


# ---------------- Figure 1 ----------------
def figure1():
    fig, ax = plt.subplots(figsize=(7.4, 4.9))
    ax.axis("off")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    rows = [
        ("Query\nexecution",
         r"$\bf{Analyst\ question\ (CQ3)}$" "\nWhich companies outperformed both their sector and the\n"
         "broad-market benchmark over the post-report window?\n(Indonesia / IDX, FY2025)", 15),
        ("Result entity",
         "ISAT (PT Indosat Ooredoo Hutchison)        relative-outperformer", 8.5),
        ("Deciding\nobservations",
         "ISAT post-report window return  =  −0.74%\nTelecommunications sector return  =  −1.61%\n"
         "JCI (Jakarta Composite) benchmark return  =  −9.48%\n"
         r"$\Rightarrow$  −0.74% > −1.61%  and  −0.74% > −9.48%" "\n       outperforms sector and benchmark", 18),
        ("Evidence item", "ISAT FY2025 audited results  (announced 2026-02-09)", 8.5),
        ("Official source", "Indonesia Stock Exchange (IDX) official disclosure", 8.5),
        ("Provenance\nrecord", "Retrieved 2026-06-28 · unadjusted daily close · 83 exact shared trading dates", 8.5),
    ]

    gap = 3.0
    top = 90.0
    lx, lw_ = 1.0, 19.0
    cx, cw = 22.0, 77.0

    rbox(ax, 75.5, 94.5, 23.5, 4.4, VERY_LIGHT, DARK, lw=1.0)
    ax.text(87.25, 96.7, "SHACL: Conforms ✓", ha="center", va="center",
            fontsize=9.0, color=BLACK, fontweight="bold")

    y = top
    ys = []
    for label, content, h in rows:
        rbox(ax, lx, y-h, lw_, h, DARK, BLACK, lw=1.0)
        ax.text(lx + lw_/2, y-h/2, label, ha="center", va="center",
                color="white", fontsize=(10.4 if "\n" in label else 9.8), fontweight="bold", linespacing=1.05)
        rbox(ax, cx, y-h, cw, h, VERY_LIGHT, EDGE, lw=1.0)
        ax.text(cx + 2.2, y-h/2, content, ha="left", va="center",
                color=INK, fontsize=(9.0 if label.startswith("Provenance") else 9.45), linespacing=1.10)
        ys.append((y, y-h))
        y = y-h-gap

    for i in range(len(rows)-1):
        darrow(ax, cx + cw/2, ys[i][1]-0.2, ys[i+1][0]+0.2)

    fig.tight_layout(pad=0.2)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUTDIR / f"figure1_worked_example.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Figure 1 written")


# ---------------- Figure 2 ----------------
def figure2():
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.axis("off")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    layers = [
        ("L0", "Source", "Per-market sheets: scope, fundamentals, market windows,\n"
         "comparators, FX, announcements, provenance, query cases", HIGHLIGHT, HIGHLIGHT_EDGE),
        ("L1", "Materialization", "Provenance-aware RDF aligned to the core ontology", CORE_GREYS[0], EDGE),
        ("L2", "Derived metrics", "window / sector / benchmark return, YoY growth, FX association,\n"
         "event-window abnormal return, event-window abnormal volume", CORE_GREYS[1], EDGE),
        ("L3", "SHACL validation", "gate: Conforms = True", CORE_GREYS[2], EDGE),
        ("L4", "CQ answering", "CQ1–CQ5 SPARQL templates (compute each stated condition)", CORE_GREYS[3], EDGE),
        ("L5", "Inference", "rules R1–R4 → typed AnalyticalFindings", CORE_GREYS[4], EDGE),
        ("L6", "Automated explanation", "EvidenceBundle + QueryExecution (the answer's evidence trail)", CORE_GREYS[5], EDGE),
    ]

    cx, cw = 27.0, 61.0
    top, h, gap = 80.0, 8.4, 1.6

    for i, market in enumerate(["PSX", "MSX", "IDX"]):
        bx = 39.0 + i*13.5
        rbox(ax, bx, 90.5, 10.0, 6.2, MID_DARK, MID_DARK, r=0.03)
        ax.text(bx+5.0, 93.6, market, ha="center", va="center",
                color="white", fontweight="bold", fontsize=10.0)
        ax.add_patch(FancyArrowPatch(
            (bx+5.0, 90.5), (bx+5.0, top+0.8), arrowstyle="-|>",
            mutation_scale=10, lw=1.4, color=EDGE,
        ))

    ys = []
    y = top
    for code, title, desc, fc, ec in layers:
        rbox(ax, cx, y-h, cw, h, fc, ec, lw=1.0)
        ax.text(cx+1.6, y-h/2, code, ha="left", va="center",
                fontweight="bold", fontsize=11.8, color=BLACK)
        ax.text(cx+8.5, y-h*0.33, title, ha="left", va="center",
                fontweight="bold", fontsize=10.3, color=BLACK)
        ax.text(cx+8.5, y-h*0.72, desc, ha="left", va="center",
                fontsize=8.25, color=INK, linespacing=1.04)
        ys.append((y, y-h))
        y = y-h-gap

    rbox(ax, cx+cw+0.7, top-h, 6.0, h, LIGHT, HIGHLIGHT_EDGE, lw=1.0)
    ax.text(cx+cw+3.7, top-h/2, "adapter\nconfig\n(~9 keys)", ha="center", va="center",
            fontsize=7.0, color=BLACK, linespacing=1.02)

    for i in range(len(layers)-1):
        ax.add_patch(FancyArrowPatch(
            (cx+cw/2, ys[i][1]-0.15), (cx+cw/2, ys[i+1][0]+0.15),
            arrowstyle="-|>", mutation_scale=10, lw=1.5, color=ARROW,
        ))

    ax.text(cx, top+1.4, "market-dependent", ha="left", va="bottom",
            fontsize=8.5, fontweight="bold", color=BLACK)

    core = ["Core ontology", "SHACL shapes", "CQ queries", "Inference rules"]
    bx, bw, bh = 12.5, 12.0, 7.0
    for j, name in enumerate(core):
        yy = (top-h)-j*(bh+2.1)
        rbox(ax, bx, yy-bh, bw, bh, VERY_LIGHT, EDGE, lw=1.0)
        ax.text(bx+bw/2, yy-bh/2, name, ha="center", va="center",
                fontsize=8.35, color=INK)

    band_top = ys[1][0]+0.4
    band_bot = ys[-1][1]-0.4
    rbox(ax, 1.2, band_bot, 8.7, band_top-band_bot, LIGHT, EDGE, lw=1.0)
    ax.text(5.5, (band_top+band_bot)/2,
            "market-independent core\nreused byte-identical · 13 artifacts (100%)",
            ha="center", va="center", rotation=90, fontsize=8.5,
            fontweight="bold", color=BLACK, linespacing=1.05)

    rbox(ax, 95.3, ys[-1][1]-0.4, 4.2, top-(ys[-1][1]-0.4), VERY_LIGHT,
         HIGHLIGHT_EDGE, lw=1.0)
    ax.text(97.4, (top+ys[-1][1])/2, "market-dependent\nonly data + adapter",
            ha="center", va="center", rotation=90, fontsize=8.2,
            fontweight="bold", color=BLACK, linespacing=1.05)

    fig.tight_layout(pad=0.2)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUTDIR / f"figure2_architecture.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Figure 2 written")


if __name__ == "__main__":
    figure1()
    figure2()
