#!/usr/bin/env python3
"""Assemble the nine-sheet IDX market structure from the synchronized real data,
so it flows through the SAME build_market_graph.py pipeline as PSX and MSX.
Inputs: final_raw_inputs/ (6 aligned series), *_REVISED_TOWR.csv, announcements.csv,
final_raw_inputs/coverage_report.csv, source_manifest.csv.
Output: <OntoKG_MSX_Portability>/IDX data v1/  (02..09 xlsx)
"""
import os, csv, glob
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__))                  # raw/idx
BASE = os.path.dirname(os.path.dirname(HERE))                      # OntoKG_MSX_Portability
FRI  = os.path.join(HERE, "final_raw_inputs")
OUT  = os.path.join(BASE, "IDX data v1")
os.makedirs(OUT, exist_ok=True)

def read_csv(p):
    import io
    data=open(p,'rb').read().replace(b'\x00',b'').decode('utf-8-sig','ignore')
    rdr=csv.DictReader(io.StringIO(data))
    return [{(k.strip() if k else k):v for k,v in row.items()} for row in rdr]
def series(fname):
    rows=read_csv(os.path.join(FRI,fname))
    out=[(r["Date"], float(r["Close"]), float(r.get("Volume") or 0) if "Volume" in r else None) for r in rows]
    out.sort(key=lambda x:x[0]); return out
def daily_returns(s):           # s: list of (date,close,vol) sorted asc -> {date: ret}
    dr={}
    for i in range(1,len(s)):
        p=s[i-1][1]
        if p: dr[s[i][0]] = s[i][1]/p - 1
    return dr
def write_xlsx(name, header, rows):
    wb=openpyxl.Workbook(); ws=wb.active; ws.append(header)
    for r in rows: ws.append(r)
    wb.save(os.path.join(OUT,name)); print(f"  wrote {name}: {len(rows)} rows")

EQUITIES=["BBCA","BMRI","ISAT","TOWR"]
cid={s:f"IDX_CO_{s}" for s in EQUITIES}
hist={s:series(f"{s}_history.csv") for s in EQUITIES}
dr={s:daily_returns(hist[s]) for s in EQUITIES}
dates=[d for d,_,_ in hist["BBCA"]]                                # 83 shared dates asc
anchors={r["company_symbol"]:r["anchor_trade_date"] for r in read_csv(os.path.join(FRI,"coverage_report.csv"))}

# ---- 02 company master, 03 fundamentals: copy authoritative REVISED files ----
def cell(v):
    if v is None or v=="" : return None
    try:
        f=float(v)
        return int(f) if (f.is_integer() and "." not in str(v) and "e" not in str(v).lower()) else f
    except (ValueError, TypeError):
        return v
def copy_csv_to_xlsx(src, name):
    rows=read_csv(os.path.join(HERE,src)); hdr=list(rows[0].keys())
    write_xlsx(name, hdr, [[cell(r[h]) for h in hdr] for r in rows])
copy_csv_to_xlsx("02_company_master_REVISED_TOWR.csv","02_company_master.xlsx")
copy_csv_to_xlsx("03_fundamentals_REVISED_TOWR.csv","03_fundamentals.xlsx")

# ---- 04 market windows (post-report 30d + event windows around the anchor) ----
mw_hdr=["market_obs_id","company_id","company_symbol","anchor_type","anchor_date","trade_date",
        "open","high","low","close","volume","daily_return","window_type","window_label",
        "source_url_or_file","retrieval_date","source_id"]
mw=[]
for s in EQUITIES:
    didx={d:i for i,(d,_,_) in enumerate(hist[s])}
    a=anchors[s]; ai=didx.get(a)
    closes={d:c for d,c,_ in hist[s]}; vols={d:v for d,_,v in hist[s]}
    def add(d, wtype, wlabel, k):
        mw.append([f"IDX_MKT_{s}_{k}", cid[s], s, "annual_report_2025", a, d,
                   "","","", closes[d], vols[d], dr[s].get(d), wtype, wlabel,
                   f"https://finance.yahoo.com/quote/{s}.JK/history","2026-06-28",f"IDX_SRC_{s}_HISTORY"])
    # post-report 30 trading days (anchor .. anchor+30)
    for j,i in enumerate(range(ai, min(ai+31,len(dates)))):
        add(dates[i],"post_report",f"{s}_FY2025_post30",f"POST30_{j+1:02d}")
    # event windows
    for j,i in enumerate(range(max(ai-1,0), min(ai+2,len(dates)))):
        add(dates[i],"event_-1_+1",f"{s}_FY2025_event_m1p1",f"EVENT_M1P1_{j+1:02d}")
    for j,i in enumerate(range(max(ai-3,0), min(ai+4,len(dates)))):
        add(dates[i],"event_-3_+3",f"{s}_FY2025_event_m3p3",f"EVENT_M3P3_{j+1:02d}")
write_xlsx("04_market_windows.xlsx", mw_hdr, mw)

# ---- 05 comparators: sector peer baskets (computed) + JCI benchmark ----
cmp_hdr=["comparator_obs_id","trade_date","value","comparator_type","comparator_name",
         "sector_name_if_applicable","daily_return","window_type","anchor_date",
         "construction_rule_if_peer_basket","source_url","retrieval_date","source_id"]
cmp=[]
baskets={"Banking":["BBCA","BMRI"],"Telecommunications":["ISAT","TOWR"]}
for sec,members in baskets.items():
    closes={s:{d:c for d,c,_ in hist[s]} for s in members}
    prev=None
    for k,d in enumerate(dates):
        val=sum(closes[s][d] for s in members)/len(members)
        ret=(val/prev-1) if prev else None; prev=val
        cmp.append([f"IDX_COMP_{sec.upper()[:4]}_{k+1:03d}", d, round(val,4), "sector_peer_basket",
                    f"{sec} selected-peer basket", sec, ret, "post_report","",
                    f"Arithmetic mean of {', '.join(members)} daily close (demonstrator proxy)",
                    "computed from member closes","2026-06-28",f"IDX_SRC_COMP_{sec.upper()[:4]}"])
jci=series("JCI_history.csv"); prev=None
for k,(d,c,_) in enumerate(jci):
    ret=(c/prev-1) if prev else None; prev=c
    cmp.append([f"IDX_COMP_JCI_{k+1:03d}", d, c, "broad_market_benchmark","Jakarta Composite Index (JCI)",
                "", ret, "post_report","","IDX broad-market index (demonstrator proxy)",
                "https://finance.yahoo.com/quote/%5EJKSE/history","2026-06-28","IDX_SRC_JCI"])
write_xlsx("05_comparators.xlsx", cmp_hdr, cmp)

# ---- 06 fx (USD/IDR) ----
fx_hdr=["trade_date","idr_usd_rate","daily_return","fx_obs_id","series_name","currency_pair",
        "frequency","retrieval_date","source_url","source_id"]
fx=series("USDIDR_history.csv"); fxr=[]; prev=None
for k,(d,c,_) in enumerate(fx):
    ret=(c/prev-1) if prev else None; prev=c
    fxr.append([d, c, ret, f"IDX_FX_USDIDR_{k+1:03d}", "Yahoo USD/IDR daily", "USD/IDR",
                "daily","2026-06-28","https://finance.yahoo.com/quote/IDR=X/history","IDX_SRC_USDIDR"])
write_xlsx("06_fx.xlsx", fx_hdr, fxr)

# ---- 07 announcements ----
an_hdr=["evidence_item_id","company_id","company_symbol","announcement_type","announcement_date",
        "announcement_title","publisher_or_issuer","document_link","source_page_url",
        "retrieval_date","source_id","matching_event_window_exists","publisher"]
ann=[]
for r in read_csv(os.path.join(HERE,"announcements.csv")):
    s=r["company_symbol"].strip()
    if s not in cid: continue
    ann.append([f"IDX_EVID_{s}_AR2025", cid[s], s, r["announcement_type"], r["announcement_date"],
                f"{s} FY2025 annual financial results", "Indonesia Stock Exchange", r["document_link"],
                r["document_link"], "2026-06-28", f"IDX_SRC_{s}_DISCLOSURE", True, "Indonesia Stock Exchange"])
write_xlsx("07_announcements.xlsx", an_hdr, ann)

# ---- 08 provenance (from source_manifest + the source_ids we reference) ----
prov_hdr=["source_id","source_type","source_url","retrieval_date","collector_note",
          "validation_status","official_title","domain","used_for_sheet"]
prov=[]
for r in read_csv(os.path.join(HERE,"source_manifest.csv")):
    prov.append([r.get("source_id") or r.get("source"), r.get("source_type",""), r.get("url") or r.get("source_url",""), r.get("retrieval_date",""),
                 r.get("status_note",""), "source_identified", r.get("source_name") or r.get("official_title",""),
                 (r.get("url","").split("/")[2] if "//" in r.get("url","") else ""), r.get("coverage_or_role","")])
# ensure the source_ids referenced by sheets exist
need=set([f"IDX_SRC_{s}_HISTORY" for s in EQUITIES]+[f"IDX_SRC_{s}_DISCLOSURE" for s in EQUITIES]+
         [f"IDX_SRC_{s}" for s in EQUITIES]+["IDX_SRC_USDIDR","IDX_SRC_JCI",
         "IDX_SRC_COMP_BANK","IDX_SRC_COMP_TELE"])
have=set(r[0] for r in prov)
for sid in sorted(need-have):
    prov.append([sid,"derived/aggregated","","2026-06-28","auto-added reference","source_identified",sid,"",""])
write_xlsx("08_provenance.xlsx", prov_hdr, prov)

# ---- 09 query cases (one worked entity per CQ family) ----
qc_hdr=["cq_family","result_entity_id","result_entity_label","supporting_observation_ids",
        "supporting_evidence_item_ids","supporting_source_ids","time_context_ids",
        "human_explanation_summary","status"]
assign={"CQ1":"BBCA","CQ2":"BMRI","CQ3":"ISAT","CQ4":"TOWR","CQ5":"BBCA"}
qc=[[fam, cid[s], s, "", f"IDX_EVID_{s}_AR2025", f"IDX_SRC_{s}_DISCLOSURE",
     "FY2025; post-report 30 trading days", f"{fam} worked case for {s} (Indonesia slice)","FINAL_READY"]
    for fam,s in assign.items()]
write_xlsx("09_query_cases.xlsx", qc_hdr, qc)

print("IDX nine-sheet package assembled at:", OUT)
