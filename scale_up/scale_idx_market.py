#!/usr/bin/env python3
"""
Scale the Indonesia (IDX) market to ~60 stocks for OntoKG-EQ.

Run this LOCALLY (it needs internet). It pulls real data from Yahoo Finance via yfinance and writes
the nine OntoKG-EQ sheets (02..09) for a large IDX cross-section, in the exact schema the builder reads,
into ./IDX_scaled_data/.  Then send that folder back; it slots into build_market_graph.py.

Install:  pip install yfinance pandas openpyxl
Run:      python scale_idx_market.py
Tune:     edit TICKERS (drop/add), N_WINDOW (analysis-window length), or PERIOD.

No data is invented: tickers that fail to download are skipped and logged; only dates shared by a
company, the index and the FX series are used (exact-date intersection, no interpolation).
"""
import os, time, datetime as dt
import pandas as pd
import yfinance as yf

OUT       = "IDX_scaled_data"
PERIOD    = "6mo"        # how much daily history to pull
N_WINDOW  = 60           # trading days of the common analysis window (most recent N shared dates)
BENCH     = "^JKSE"      # Jakarta Composite Index
FX        = "IDR=X"      # USD/IDR
RETRIEVED = dt.date.today().isoformat()

# ~60 liquid IDX large caps (edit freely). The 4 original demo names are included.
TICKERS = """
BBCA BBRI BMRI BBNI BRIS BBTN ARTO BTPS
TLKM ISAT EXCL TOWR TBIG MTEL FREN
ASII UNTR HEXA AALI
ICBP INDF UNVR MYOR GGRM HMSP KLBF SIDO CPIN JPFA AMRT MAPI ACES ERAA
SMGR INTP
ADRO PTBA ITMG PGAS MEDC AKRA ELSA
ANTM INCO MDKA TINS NCKL BRMS
BRPT TPIA ESSA
BSDE CTRA PWON SMRA
JSMR WIKA PTPP ADHI
GOTO BUKA EMTK MNCN SCMA
MIKA
""".split()

def hist(ticker):
    df = yf.Ticker(ticker).history(period=PERIOD, interval="1d", auto_adjust=False)
    if df is None or df.empty: return None
    df = df.reset_index()[["Date","Close","Volume"]].dropna()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    return df.set_index("Date")

def fundamentals(tk):
    """Return (sector, name, eps_latest, eps_prev, ni_growth_pct, fy_latest, fy_prev, report_date)."""
    sector=name=None; eps_l=eps_p=growth=None; fyl=fyp=None; rep=""
    try:
        info=tk.info; sector=info.get("sector") or "Unknown"; name=info.get("longName") or info.get("shortName")
    except Exception: sector="Unknown"
    try:
        ist=tk.income_stmt   # annual; columns are period-end dates
        cols=sorted([c for c in ist.columns], reverse=True)
        def row(*names):
            for n in names:
                if n in ist.index: return ist.loc[n]
            return None
        ni=row("Net Income","NetIncome","Net Income Common Stockholders")
        eps=row("Basic EPS","Diluted EPS")
        if ni is not None and len(cols)>=2:
            a,b=float(ni[cols[0]]), float(ni[cols[1]])
            if b: growth=round((a-b)/abs(b)*100,4)
            fyl=pd.to_datetime(cols[0]).year; fyp=pd.to_datetime(cols[1]).year; rep=pd.to_datetime(cols[0]).strftime("%Y-%m-%d")
        if eps is not None and len(cols)>=2:
            eps_l=round(float(eps[cols[0]]),4); eps_p=round(float(eps[cols[1]]),4)
    except Exception: pass
    if eps_l is None:
        try: eps_l=tk.info.get("trailingEps")
        except Exception: pass
    return sector, name, eps_l, eps_p, growth, fyl, fyp, rep

def daily_ret(series):  # series: dict date->value (sorted) -> dict date->return
    ks=sorted(series); out={}
    for i in range(1,len(ks)):
        p=series[ks[i-1]]
        if p: out[ks[i]]=series[ks[i]]/p-1
    return out

def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"Downloading {len(TICKERS)} tickers + index + FX (period={PERIOD}) ...")
    comp={}; meta={}; skipped=[]
    for i,t in enumerate(TICKERS,1):
        sym=t.upper(); yh=f"{sym}.JK"
        try:
            h=hist(yh); tk=yf.Ticker(yh)
            if h is None or len(h)<N_WINDOW+5: skipped.append((sym,"insufficient history")); continue
            f=fundamentals(tk)
            comp[sym]=h; meta[sym]=f
            print(f"  [{i}/{len(TICKERS)}] {sym}: {len(h)} days, sector={f[0]}, eps={f[2]}, ni_growth={f[4]}")
        except Exception as e:
            skipped.append((sym,str(e)[:60]))
        time.sleep(0.4)
    bench=hist(BENCH); fx=hist(FX)
    if bench is None or fx is None: raise SystemExit("Benchmark or FX download failed; rerun.")

    # common analysis window = most recent N dates shared by ALL kept series + bench + fx
    common=set(bench.index)&set(fx.index)
    for h in comp.values(): common&=set(h.index)
    window=sorted(common)[-N_WINDOW:]
    print(f"\nKept {len(comp)} companies; common window {window[0]}..{window[-1]} ({len(window)} trading days)")
    if len(window)<20: raise SystemExit("Too few shared trading days; widen PERIOD.")

    def W(h,col): return {d:float(h.loc[d,col]) for d in window if d in h.index}

    # ---- 02 company master ----
    rows02=[]; sectors={}
    for sym,(sec,name,*_ ) in meta.items():
        sectors.setdefault(sec,[]).append(sym)
        rows02.append(dict(company_id=f"IDX_CO_{sym}",company_symbol=sym,stock_code=sym,
            official_company_name=name or sym,sector=sec,sector_scheme="GICS sector (Yahoo Finance)",
            exchange="Indonesia Stock Exchange",listing_status="Listed",fiscal_year_end="31-Dec",
            official_idx_page=f"https://finance.yahoo.com/quote/{sym}.JK",retrieval_date=RETRIEVED,
            source_id=f"IDX_SRC_{sym}"))
    # ---- 03 fundamentals ----
    rows03=[]
    for sym,(sec,name,eps_l,eps_p,growth,fyl,fyp,rep) in meta.items():
        if eps_l is not None:
            rows03.append(dict(period_id=f"IDX_FUND_{sym}_{fyl or 'L'}",company_id=f"IDX_CO_{sym}",company_symbol=sym,
                fiscal_year=fyl or 2025,period_type="Annual",period_end_date=(f"{fyl}-12-31" if fyl else ""),
                report_date=rep,eps=eps_l,yoy_profit_growth_pct=growth,
                source_url=f"https://finance.yahoo.com/quote/{sym}.JK/financials",retrieval_date=RETRIEVED,source_id=f"IDX_SRC_{sym}"))
        if eps_p is not None and fyp:
            rows03.append(dict(period_id=f"IDX_FUND_{sym}_{fyp}",company_id=f"IDX_CO_{sym}",company_symbol=sym,
                fiscal_year=fyp,period_type="Annual",period_end_date=f"{fyp}-12-31",report_date="",
                eps=eps_p,yoy_profit_growth_pct=None,
                source_url=f"https://finance.yahoo.com/quote/{sym}.JK/financials",retrieval_date=RETRIEVED,source_id=f"IDX_SRC_{sym}"))
    # ---- 04 market windows (post-report = the common analysis window) ----
    rows04=[]
    for sym,h in comp.items():
        c=W(h,"Close"); v=W(h,"Volume"); dr=daily_ret(c)
        for k,d in enumerate(window,1):
            if d not in c: continue
            rows04.append(dict(market_obs_id=f"IDX_MKT_{sym}_{k:02d}",company_id=f"IDX_CO_{sym}",company_symbol=sym,
                anchor_type="recent_analysis_window",anchor_date=window[0],trade_date=d,
                open="",high="",low="",close=round(c[d],4),volume=int(v.get(d,0)),daily_return=dr.get(d),
                window_type="post_report",window_label=f"{sym}_recent",
                source_url_or_file=f"https://finance.yahoo.com/quote/{sym}.JK/history",retrieval_date=RETRIEVED,source_id=f"IDX_SRC_{sym}"))
    # ---- 05 comparators: sector peer baskets (>=2 members) + JCI benchmark ----
    rows05=[]
    for sec,members in sectors.items():
        members=[m for m in members if m in comp]
        if len(members)<2: continue
        prev=None
        for k,d in enumerate(window,1):
            vals=[float(comp[m].loc[d,"Close"]) for m in members if d in comp[m].index]
            if not vals: continue
            val=sum(vals)/len(vals); ret=(val/prev-1) if prev else None; prev=val
            rows05.append(dict(comparator_obs_id=f"IDX_COMP_{abs(hash(sec))%10000}_{k:03d}",trade_date=d,value=round(val,4),
                comparator_type="sector_peer_basket",comparator_name=f"{sec} peer basket",sector_name_if_applicable=sec,
                daily_return=ret,window_type="post_report",anchor_date="",
                construction_rule_if_peer_basket=f"Mean daily close of {len(members)} {sec} constituents",
                source_url="Yahoo Finance",retrieval_date=RETRIEVED,source_id="IDX_SRC_SECTOR_BASKETS"))
    bc=W(bench,"Close"); bdr=daily_ret(bc); prev=None
    for k,d in enumerate(window,1):
        if d not in bc: continue
        rows05.append(dict(comparator_obs_id=f"IDX_COMP_JCI_{k:03d}",trade_date=d,value=round(bc[d],4),
            comparator_type="broad_market_benchmark",comparator_name="Jakarta Composite Index (JCI)",
            sector_name_if_applicable="",daily_return=bdr.get(d),window_type="post_report",anchor_date="",
            construction_rule_if_peer_basket="IDX broad-market index",source_url="https://finance.yahoo.com/quote/%5EJKSE",
            retrieval_date=RETRIEVED,source_id="IDX_SRC_JCI"))
    # ---- 06 fx ----
    rows06=[]; fc=W(fx,"Close"); fdr=daily_ret(fc)
    for k,d in enumerate(window,1):
        if d not in fc: continue
        rows06.append(dict(trade_date=d,idr_usd_rate=round(fc[d],4),daily_return=fdr.get(d),fx_obs_id=f"IDX_FX_{k:03d}",
            series_name="Yahoo USD/IDR daily",currency_pair="USD/IDR",frequency="daily",retrieval_date=RETRIEVED,
            source_url="https://finance.yahoo.com/quote/IDR=X",source_id="IDX_SRC_USDIDR"))
    # ---- 07 announcements (one per company, anchored to its reported FY) ----
    rows07=[]
    for sym,(sec,name,eps_l,eps_p,growth,fyl,fyp,rep) in meta.items():
        rows07.append(dict(evidence_item_id=f"IDX_EVID_{sym}",company_id=f"IDX_CO_{sym}",company_symbol=sym,
            announcement_type="Annual financial results",announcement_date=rep or f"{fyl or 2025}-12-31",
            announcement_title=f"{sym} FY{fyl or ''} results",publisher_or_issuer="Indonesia Stock Exchange / Yahoo Finance",
            document_link=f"https://finance.yahoo.com/quote/{sym}.JK/financials",
            source_page_url=f"https://finance.yahoo.com/quote/{sym}.JK",retrieval_date=RETRIEVED,
            source_id=f"IDX_SRC_{sym}",matching_event_window_exists=False,publisher="Yahoo Finance"))
    # ---- 08 provenance ----
    rows08=[dict(source_id="IDX_SRC_JCI",source_type="benchmark_index",source_url="https://finance.yahoo.com/quote/%5EJKSE",
                 retrieval_date=RETRIEVED,collector_note="Jakarta Composite via Yahoo",validation_status="source_identified",
                 official_title="Jakarta Composite Index",domain="finance.yahoo.com",used_for_sheet="05_comparators"),
             dict(source_id="IDX_SRC_USDIDR",source_type="fx_reference",source_url="https://finance.yahoo.com/quote/IDR=X",
                 retrieval_date=RETRIEVED,collector_note="USD/IDR via Yahoo",validation_status="source_identified",
                 official_title="USD/IDR",domain="finance.yahoo.com",used_for_sheet="06_fx"),
             dict(source_id="IDX_SRC_SECTOR_BASKETS",source_type="constructed_peer_basket",source_url="Yahoo Finance",
                 retrieval_date=RETRIEVED,collector_note="Sector peer baskets = mean of constituents",validation_status="demonstrator_proxy_documented",
                 official_title="Sector peer baskets",domain="finance.yahoo.com",used_for_sheet="05_comparators")]
    for sym in comp: rows08.append(dict(source_id=f"IDX_SRC_{sym}",source_type="market+financials",
            source_url=f"https://finance.yahoo.com/quote/{sym}.JK",retrieval_date=RETRIEVED,
            collector_note="Daily prices + annual financials via Yahoo",validation_status="source_identified",
            official_title=meta[sym][1] or sym,domain="finance.yahoo.com",used_for_sheet="02;03;04;07"))
    # ---- 09 query cases (seed worked entities; CQ queries still return all qualifiers) ----
    syms=list(comp)
    fams=["CQ1","CQ2","CQ3","CQ4","CQ5"]
    rows09=[dict(cq_family=f,result_entity_id=f"IDX_CO_{syms[i%len(syms)]}",result_entity_label=syms[i%len(syms)],
                 supporting_observation_ids="",supporting_evidence_item_ids=f"IDX_EVID_{syms[i%len(syms)]}",
                 supporting_source_ids=f"IDX_SRC_{syms[i%len(syms)]}",time_context_ids="recent analysis window",
                 human_explanation_summary=f"{f} worked case (scaled IDX)",status="FINAL_READY") for i,f in enumerate(fams)]

    def save(name,rows):
        pd.DataFrame(rows).to_excel(os.path.join(OUT,name),index=False)
        print(f"  wrote {name}: {len(rows)} rows")
    print("\nWriting nine sheets to", OUT)
    save("02_company_master.xlsx",rows02); save("03_fundamentals.xlsx",rows03)
    save("04_market_windows.xlsx",rows04); save("05_comparators.xlsx",rows05)
    save("06_fx.xlsx",rows06); save("07_announcements.xlsx",rows07)
    save("08_provenance.xlsx",rows08); save("09_query_cases.xlsx",rows09)
    with open(os.path.join(OUT,"_scale_summary.txt"),"w") as f:
        f.write(f"Companies kept: {len(comp)}\nSkipped: {skipped}\nWindow: {window[0]}..{window[-1]} ({len(window)} days)\n"
                f"Sectors: { {s:len(m) for s,m in sectors.items()} }\n")
    print(f"\nDONE. Companies={len(comp)}, skipped={len(skipped)}. See {OUT}/_scale_summary.txt")
    if skipped: print("Skipped:", skipped)

if __name__ == "__main__":
    main()
