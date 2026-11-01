import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
fig=plt.figure(figsize=(10,6.35),dpi=220); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(18.5,82); ax.axis('off')
DARK='#383838'; LIGHT='#f6f6f6'; EDGE='#999999'
rows=[
 ("Query\nexecution",[("Analyst question (CQ3)",True),("Which companies outperformed both their sector and the",False),("broad-market benchmark over the post-report window?",False),("(Indonesia / IDX, FY2025)",False)],9.5),
 ("Result entity",[("ISAT (PT Indosat Ooredoo Hutchison)   →   relative-outperformer (R3)",False)],5.2),
 ("Deciding\nobservations",[("ISAT post-report window return  =  −0.47%",False),("Telecommunications sector return  =  −1.59%",False),("JCI (Jakarta Composite) benchmark return  =  −10.55%",False),("⇒  −0.47 > −1.59  and  −0.47 > −10.55  (same window)",False)],10.2),
 ("Evidence-\nboundary audit",[("Ambient graph: positive  ·  declared support: positive  ·  delivered bundle: positive",False),("Unit readiness (same witness): percent, as declared",False)],7.0),
 ("Numeric\nlineage",[("Each value → workbook cell (file SHA-256, sheet, cell) → source-register entry",False),("Recorded path, not independent verification of the source values",False)],7.0),
 ("Contextual\nevidence",[("ISAT FY2025 audited results, IDX disclosure (announced 2026-02-09)",False),("Context for the result; not the source of the numeric values",False)],7.0),
]
y=74.5; gap=1.7
for lab,lines,h in rows:
    ax.add_patch(Rectangle((2,y-h),19,h,fc=DARK,ec='black',lw=1.2))
    ax.text(11.5,y-h/2,lab,color='white',ha='center',va='center',fontsize=12.5,fontweight='bold',linespacing=1.15)
    ax.add_patch(Rectangle((23,y-h),75,h,fc=LIGHT,ec=EDGE,lw=1.2))
    n=len(lines); step=2.15; top=y-h/2+(n-1)*step/2
    for i,(t,b) in enumerate(lines):
        ax.text(25,top-i*step,t,ha='left',va='center',fontsize=11.6,fontweight='bold' if b else 'normal',color='#1a1a1a')
    if lab!=rows[-1][0]:
        ax.add_patch(FancyArrowPatch((60.5,y-h-0.1),(60.5,y-h-gap+0.1),arrowstyle='-|>',mutation_scale=14,color='#666666',lw=2))
    y=y-h-gap
ax.add_patch(Rectangle((66,76.3),32,4.2,fc=LIGHT,ec='#333333',lw=1.3))
ax.text(82,78.4,"SHACL: Conforms (structure only)",ha='center',va='center',fontsize=11.5,fontweight='bold')
ax.text(2,78.4,"Corrected financial-v2 graph",ha='left',va='center',fontsize=11,style='italic',color='#444444')
fig.savefig('figure1.png',dpi=220,facecolor='white')
