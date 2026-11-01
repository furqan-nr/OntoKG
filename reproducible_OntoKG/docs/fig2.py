import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
fig=plt.figure(figsize=(12,8.7),dpi=210); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,120); ax.set_ylim(-3,84); ax.axis('off')
def box(x,y,w,h,fc,ec='#888888',lw=1.3): ax.add_patch(Rectangle((x,y),w,h,fc=fc,ec=ec,lw=lw))
def arrow(x1,y1,x2,y2,c='#777777'): ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=13,color=c,lw=1.8))
# market inputs
for i,m in enumerate(['PSX','MSX','IDX']):
    x=44+i*16; box(x,77,12,4.6,'#606060','#606060'); ax.text(x+6,79.3,m,color='white',ha='center',va='center',fontsize=14,fontweight='bold')
    arrow(x+6,76.8,x+6,72.9)
ax.text(31,74.6,'market-dependent',fontsize=12,fontweight='bold')
layers=[('L0','Source','nine per-market sheets: scope, company, fundamentals, market windows,\ncomparators, FX, announcements, provenance, query cases','#d9d9d9'),
('L1','Materialization','provenance-aware RDF aligned to the core ontology','#efefef'),
('L2','Derived metrics','window, sector and benchmark returns; YoY growth; FX association;\nevent-window return sum and volume ratio','#e8e8e8'),
('L3','SHACL validation','gate: Conforms = True (structure only)','#e1e1e1'),
('L4','CQ answering','CQ1–CQ5 SPARQL templates (compute each stated condition)','#dadada'),
('L5','Inference','rules R1–R4 → typed AnalyticalFindings with declared support','#d3d3d3'),
('L6','Explanation','EvidenceBundle + QueryExecution (the delivered evidence)','#cbcbcb')]
x0,w,h,g=31,64,7.0,1.3; y=72.6
for code,title,desc,c in layers:
    h=8.6 if '\n' in desc else 6.6
    box(x0,y-h,w,h,c)
    ax.text(x0+2,y-h/2,code,fontsize=17,fontweight='bold',va='center')
    ax.text(x0+9,y-1.9,title,fontsize=13.5,fontweight='bold',va='center')
    ax.text(x0+9,y-h+(2.6 if '\n' in desc else 1.9),desc,fontsize=10.2,va='center',linespacing=1.15)
    if code!='L6': arrow(x0+w-5,y-h-0.05,x0+w-5,y-h-g+0.05)
    y=y-h-g
yb=y  # bottom of L6
# audit layer
ah=11.0; ay=yb-1.6-ah
arrow(x0+w-5,yb-0.05,x0+w-5,ay+ah+0.05,'#333333')
box(x0,ay,w,ah,'white','#222222',2.2)
ax.text(x0+2,ay+ah/2,'A',fontsize=17,fontweight='bold',va='center')
ax.text(x0+9,ay+ah-2.0,'Evidence-boundary audit (versioned contracts)',fontsize=13.5,fontweight='bold',va='center')
ax.text(x0+9,ay+ah-6.9,'same condition checked over the ambient graph, declared support and\ndelivered bundle \u2192 positive / false / unknown; same-witness unit\nreadiness; workbook-cell lineage overlay (recorded paths, not\nsource authentication)',fontsize=10.2,va='center',linespacing=1.15)
# left core
for i,t in enumerate(['Core ontology','SHACL shapes','CQ queries','Inference rules']):
    box(15,58.5-i*7.2,13,5.2,'#f6f6f6'); ax.text(21.5,61.1-i*7.2,t,ha='center',va='center',fontsize=10.8)
box(3,yb,9,72.6-yb,'#efefef')
ax.text(7.5,(yb+72.6)/2,'market-independent core\nreused byte-identical · 13 artifacts',rotation=90,ha='center',va='center',fontsize=11.5,fontweight='bold',linespacing=1.3)
# right side
box(97,72.6-7.0,9,7.0,'#f6f6f6'); ax.text(101.5,69.1,'adapter\nconfig\n(~9 keys)',ha='center',va='center',fontsize=9.6,linespacing=1.1)
box(108,yb,6,72.6-yb,'#f6f6f6'); ax.text(111,(72.6+yb)/2,'market-dependent:\nonly data + adapter',rotation=90,ha='center',va='center',fontsize=11.2,fontweight='bold',linespacing=1.2)
# NHS
box(97,ay,22,ah,'#606060','#606060')
ax.text(108,ay+ah/2,'NHS RTT public data\nseparate source adapter\n+ two-role contract',color='white',ha='center',va='center',fontsize=10.2,fontweight='bold',linespacing=1.2)
arrow(97,ay+ah/2,x0+w+0.2,ay+ah/2,'#333333')
fig.savefig('figure2.png',dpi=210,facecolor='white')
