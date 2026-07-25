#!/usr/bin/env python3
"""
Unified market->RDF builder for OntoKG-EQ portability validation.

ONE pipeline, swap only the data: materializes a market's nine spreadsheets into
an RDF graph aligned to the OntoKG-EQ core ontology, computes the DERIVED
analytical metrics the competency questions need (window returns, YoY growth,
relative deltas, FX association, event-window abnormal return/volume), and
constructs CQ1-CQ5 QueryExecutions + EvidenceBundles.

The result entity, evidence item, and CQ family for each worked case come from
sheet 09; the supporting observation set is built by a deterministic,
market-agnostic recipe over the derived metrics, so construction is identical
across markets.

Usage:
    python build_market_graph.py psx
    python build_market_graph.py msx

Output: data/demo_<market>.ttl

The same core ontology, SHACL shapes, and CQ1-CQ5 SPARQL templates are reused
unchanged for every market -> portability evidence.
"""
import os, re, sys, glob
from collections import defaultdict
from datetime import datetime, date
import openpyxl
from rdflib import Graph, Namespace, Literal, RDF, RDFS, URIRef
from rdflib.namespace import XSD, OWL

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------
# Per-market configuration (only thing that differs between markets)
# ----------------------------------------------------------------------------
CONFIG = {
    "psx": dict(
        data_dir=os.path.join(HERE, "..", "PSX data v4"),
        prefix="", ns="https://w3id.org/ontokg-eq/psx#",
        company_id_col="company_symbol", eps_col="eps", fx_rate_col="pkr_usd_rate",
        fx_stem="06_sbp_fx", local_currency="PKR", growth_scale=1.0,  # yoy stored as percent
        scheme_label="PSX / KSE sector classification",
        benchmark_types={"market index"}, benchmark_label="KSE-100",
        ont_label="OntoKG-EQ PSX (KSE-100) Instances",
    ),
    "msx": dict(
        data_dir=os.path.join(HERE, "..", "updated MSX"),
        prefix="MY_", ns="https://w3id.org/ontokg-eq/msx#",
        company_id_col="stock_code", eps_col="eps_myr", fx_rate_col="myr_usd_rate",
        fx_stem="06_bnm_fx", local_currency="MYR", growth_scale=100.0,  # yoy stored as ratio
        scheme_label="Bursa Malaysia sector classification",
        benchmark_types={"broad_market_benchmark_proxy"}, benchmark_label="FBM KLCI (demonstrator proxy)",
        ont_label="OntoKG-EQ MSX (Bursa Malaysia) Instances",
    ),
    "idx": dict(
        data_dir=os.path.join(HERE, "..", "IDX data v1"),
        prefix="", ns="https://w3id.org/ontokg-eq/idx#",
        company_id_col="stock_code", eps_col="eps", fx_rate_col="idr_usd_rate",
        fx_stem="06_fx", local_currency="IDR", growth_scale=1.0,  # yoy stored as percent
        scheme_label="IDX sector classification",
        benchmark_types={"broad_market_benchmark"}, benchmark_label="Jakarta Composite Index (JCI)",
        ont_label="OntoKG-EQ IDX (Indonesia Stock Exchange) Instances",
    ),
    "idx_scaled": dict(
        data_dir=os.path.join(HERE, "..", "scale_up", "IDX_scaled_data"),
        prefix="", ns="https://w3id.org/ontokg-eq/idxscaled#",
        company_id_col="stock_code", eps_col="eps", fx_rate_col="idr_usd_rate",
        fx_stem="06_fx", local_currency="IDR", growth_scale=1.0,
        scheme_label="GICS sector (Yahoo Finance)",
        benchmark_types={"broad_market_benchmark"}, benchmark_label="Jakarta Composite Index (JCI)",
        ont_label="OntoKG-EQ IDX (scaled, ~60 stocks) Instances",
    ),
}

CORE = Namespace("https://w3id.org/ontokg-eq#")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def slug(x):
    return re.sub(r"_+", "_", re.sub(r"[^0-9A-Za-z]+", "_", str(x).strip())).strip("_")
def to_date(v):
    if v is None: return None
    if isinstance(v, (datetime, date)): return v.strftime("%Y-%m-%d")
    return str(v)[:10]
def to_dt(v):
    if v is None: return None
    if isinstance(v, datetime): return v.strftime("%Y-%m-%dT%H:%M:%S")
    t = str(v); return t[:19] if "T" in t else t[:10] + "T00:00:00"
def dec(v):
    if v is None: return None
    return Literal(str(round(float(v), 6)), datatype=XSD.decimal)
def lit(v):
    return Literal(str(v))
def is_post(wt):  return "post_report" in str(wt)
def is_event(wt): return "event" in str(wt)
def win_type_label(wt):
    if "-1_+1" in str(wt): return "(-1,+1)"
    if "-3_+3" in str(wt): return "(-3,+3)"
    return wt

def window_return(series):
    """series: list of (date, value) -> percentage change first->last."""
    s = [(d, v) for d, v in series if v is not None]
    s.sort(key=lambda x: x[0] or "")
    if len(s) < 2 or not s[0][1]: return None
    return (s[-1][1] - s[0][1]) / s[0][1] * 100.0

def daily_returns(series):
    """series: list of (date, value) -> dict date->pct return vs previous day."""
    s = [(d, v) for d, v in series if v is not None]
    s.sort(key=lambda x: x[0] or "")
    out = {}
    for i in range(1, len(s)):
        prev = s[i-1][1]
        if prev: out[s[i][0]] = (s[i][1] - prev) / prev
    return out

def pearson(a, b):
    """a,b: dict date->return. Correlate on shared dates."""
    keys = sorted(set(a) & set(b))
    n = len(keys)
    if n < 3: return None
    xs = [a[k] for k in keys]; ys = [b[k] for k in keys]
    mx = sum(xs)/n; my = sum(ys)/n
    sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    sxx = sum((x-mx)**2 for x in xs); syy = sum((y-my)**2 for y in ys)
    if sxx == 0 or syy == 0: return None
    return sxy / (sxx**0.5 * syy**0.5)

# Generic, market-agnostic metric names (so one query set works for all markets)
M_POST_RET   = "post-report window return %"
M_FUND_GROW  = "YoY profit growth %"
M_SECT_RET   = "sector window return %"
M_BENCH_RET  = "benchmark window return %"
M_FX_CHANGE  = "FX window change %"
M_FX_CORR_CO = "FX vs company return correlation"
M_FX_CORR_BM = "FX vs benchmark return correlation"
M_EVENT_AR   = "cumulative abnormal return %"
M_EVENT_VOL  = "abnormal volume ratio"

# ----------------------------------------------------------------------------
def build(market):
    cfg = CONFIG[market]
    MKT = Namespace(cfg["ns"]); P = cfg["prefix"]; DDIR = cfg["data_dir"]
    g = Graph(); g.bind("", CORE); g.bind(market, MKT); g.bind("owl", OWL)

    def n(local): return MKT[slug(local)]
    def rows(stem):
        f = glob.glob(os.path.join(DDIR, f"{P}{stem}*.xlsx"))[0]
        wb = openpyxl.load_workbook(f, data_only=True); ws = wb.active
        rr = list(ws.iter_rows(values_only=True)); h = rr[0]
        out = [dict(zip(h, r)) for r in rr[1:] if any(c is not None for c in r)]
        wb.close(); return out
    def obs_types(node, *ts):
        for t in ts: g.add((node, RDF.type, CORE[t]))
    def add_obs(node, kind, entity, metric, value, window=None, event=False, period=None, date=None):
        """Materialize an Observation with the SHACL-required shape."""
        obs_types(node, kind, "Observation")
        if entity is not None: g.add((node, CORE.isObservationOf, entity))
        g.add((node, CORE.hasMetricName, lit(metric)))
        g.add((node, CORE.hasMetricValue, dec(value)))
        if period is not None: g.add((node, CORE.observedInPeriod, period))
        if window is not None:
            g.add((node, CORE.observedInEventWindow if event else CORE.observedOverWindow, window))
        if date is not None: g.add((node, CORE.hasObservationDate, Literal(date, datatype=XSD.date)))
        return node

    # ontology header
    ONT = URIRef(cfg["ns"].rstrip("#"))
    g.add((ONT, RDF.type, OWL.Ontology))
    g.add((ONT, OWL.imports, URIRef("https://w3id.org/ontokg-eq/core")))
    g.add((ONT, OWL.imports, URIRef("https://w3id.org/ontokg-eq/alignment")))
    g.add((ONT, RDFS.label, Literal(cfg["ont_label"], lang="en")))

    VALID = n("validation_passed")
    g.add((VALID, RDF.type, CORE.ValidationStatus)); g.add((VALID, CORE.hasValidationFlag, lit("passed")))

    SCHEME = n("sector_scheme")
    g.add((SCHEME, RDF.type, CORE.IndustrySectorClassificationScheme))
    g.add((SCHEME, RDFS.label, Literal(cfg["scheme_label"], lang="en")))
    def sector_classifier(sector):
        node = n(f"sector_classifier_{slug(sector)}")
        if (node, RDF.type, CORE.IndustrySectorClassifier) not in g:
            g.add((node, RDF.type, CORE.IndustrySectorClassifier)); g.add((node, RDF.type, CORE.ObservedEntity))
            g.add((node, RDFS.label, Literal(f"{sector} Sector Classifier", lang="en")))
            g.add((node, CORE.isDefinedInIndustrySectorScheme, SCHEME))
        return node

    BENCH = n("market_index_benchmark")
    g.add((BENCH, RDF.type, CORE.MarketIndex)); g.add((BENCH, RDF.type, CORE.ObservedEntity))
    g.add((BENCH, RDFS.label, Literal(cfg["benchmark_label"], lang="en")))
    LOCAL = cfg["local_currency"]
    CUR_LOCAL = n(f"currency_{LOCAL}"); g.add((CUR_LOCAL, RDF.type, CORE.Currency)); g.add((CUR_LOCAL, CORE.hasCurrencyCode, lit(LOCAL)))
    CUR_USD = n("currency_USD"); g.add((CUR_USD, RDF.type, CORE.Currency)); g.add((CUR_USD, CORE.hasCurrencyCode, lit("USD")))
    FXPAIR = n("observed_fx_pair"); g.add((FXPAIR, RDF.type, CORE.ObservedEntity)); g.add((FXPAIR, RDFS.label, Literal(f"USD/{LOCAL} currency pair", lang="en")))

    # --- sources (08) ---
    src_node = {}
    for r in rows("08_provenance"):
        sid = r["source_id"]; node = n(f"source_{sid}"); src_node[sid] = node
        g.add((node, RDF.type, CORE.EvidenceSource)); g.add((node, CORE.hasSourceIdentifier, lit(sid)))
        if r.get("source_type"): g.add((node, CORE.hasSourceType, lit(r["source_type"])))
        if r.get("source_url"): g.add((node, CORE.hasSourceURL, Literal(str(r["source_url"]), datatype=XSD.anyURI)))
    def get_source(sid):
        if sid not in src_node:
            node = n(f"source_{sid}"); g.add((node, RDF.type, CORE.EvidenceSource)); g.add((node, CORE.hasSourceIdentifier, lit(sid))); src_node[sid] = node
        return src_node[sid]

    # --- companies (02) ---
    co_node = {}; co_sector = {}
    for r in rows("02_company_master"):
        cid = r["company_id"]; node = n(f"company_{cid}"); co_node[cid] = node; co_sector[cid] = r["sector"]
        g.add((node, RDF.type, CORE.Company)); g.add((node, RDF.type, CORE.ObservedEntity))
        g.add((node, RDFS.label, Literal(str(r["official_company_name"]), lang="en")))
        g.add((node, CORE.hasCompanyIdentifier, lit(r.get(cfg["company_id_col"]) or r["company_symbol"])))
        g.add((node, CORE.hasCompanyName, lit(r["official_company_name"])))
        g.add((node, CORE.isClassifiedByIndustrySector, sector_classifier(r["sector"])))

    # --- publishers + announcements (07) ---
    pub_node = {}
    def get_pub(name):
        if name not in pub_node:
            node = n(f"publisher_{slug(name)}"); g.add((node, RDF.type, CORE.Publisher)); g.add((node, RDFS.label, Literal(str(name), lang="en"))); pub_node[name] = node
        return pub_node[name]
    evid_node = {}; co_announcement = {}
    for r in rows("07_announcements"):
        eid = r["evidence_item_id"]; node = n(f"evid_{eid}"); evid_node[eid] = node
        g.add((node, RDF.type, CORE.Announcement)); g.add((node, RDF.type, CORE.EvidenceItem))
        g.add((node, RDFS.label, Literal(str(r.get("announcement_title") or eid), lang="en")))
        g.add((node, CORE.aboutCompany, co_node[r["company_id"]]))
        g.add((node, CORE.publishedBy, get_pub(r.get("publisher") or r.get("publisher_or_issuer") or "Exchange")))
        g.add((node, CORE.hasEvidenceSource, get_source(r["source_id"])))
        g.add((node, CORE.hasEvidenceIdentifier, lit(eid)))
        if r.get("document_link"): g.add((node, CORE.hasEvidenceURL, Literal(str(r["document_link"]), datatype=XSD.anyURI)))
        if r.get("announcement_type"): g.add((node, CORE.hasAnnouncementType, lit(r["announcement_type"])))
        g.add((node, CORE.hasAnnouncementDate, Literal(to_date(r["announcement_date"]), datatype=XSD.date)))
        co_announcement[r["company_id"]] = node
        prov = n(f"prov_evid_{eid}"); g.add((prov, RDF.type, CORE.ProvenanceRecord))
        g.add((prov, CORE.derivedFrom, node)); g.add((prov, CORE.hasRetrievalDate, Literal(to_dt(r.get("retrieval_date")), datatype=XSD.dateTime)))

    # --- fundamentals (03) ---
    co_funds = defaultdict(list); co_fund_rows = defaultdict(list)
    for r in rows("03_fundamentals"):
        pid = r["period_id"]; period = n(f"period_{pid}")
        g.add((period, RDF.type, CORE.ReportingPeriod))
        g.add((period, CORE.hasStartDate, Literal(f"{int(r['fiscal_year'])}-01-01", datatype=XSD.date)))
        g.add((period, CORE.hasEndDate, Literal(to_date(r["period_end_date"]), datatype=XSD.date)))
        if r.get("report_date"): g.add((period, CORE.hasReportDate, Literal(to_date(r["report_date"]), datatype=XSD.date)))
        obs = n(f"fund_{pid}")
        eps = r.get(cfg["eps_col"])
        add_obs(obs, "FundamentalObservation", co_node[r["company_id"]],
                "EPS" if eps is not None else "profit after tax",
                eps if eps is not None else (r.get("profit_after_tax_million_myr") or r.get("profit_after_tax_thousand_pkr") or 0),
                period=period, date=to_date(r.get("report_date") or r["period_end_date"]))
        co_funds[r["company_id"]].append((to_date(r.get("report_date") or r["period_end_date"]), obs))
        co_fund_rows[r["company_id"]].append((int(r["fiscal_year"]), r, period))

    # --- market windows (04): raw close / event observations + window entities ---
    mw = rows("04_market_windows")
    by_label = defaultdict(list)
    for r in mw: by_label[(r["company_id"], r["window_label"], r["window_type"])].append(r)
    win_node = {}
    for (cid, label, wt), rs in by_label.items():
        dates = sorted(to_date(x["trade_date"]) for x in rs); ev = is_event(wt)
        node = n(f"window_{cid}_{slug(label)}_{slug(wt)}"); win_node[(cid, label, wt)] = (node, ev)
        g.add((node, RDF.type, CORE.EventWindow if ev else CORE.AnalysisWindow))
        g.add((node, CORE.hasStartDate, Literal(dates[0], datatype=XSD.date)))
        g.add((node, CORE.hasEndDate, Literal(dates[-1], datatype=XSD.date)))
        g.add((node, CORE.hasWindowType, lit(win_type_label(wt) if ev else wt)))
    co_post_window = {}; co_event_window = defaultdict(dict)
    co_post_raw = defaultdict(list); co_event_raw = defaultdict(lambda: defaultdict(list))
    for r in mw:
        cid = r["company_id"]; oid = r["market_obs_id"]; obs = n(f"mkt_{oid}")
        wnode, ev = win_node[(cid, r["window_label"], r["window_type"])]; d = to_date(r["trade_date"])
        if ev:
            dr = r.get("daily_return")
            add_obs(obs, "MarketObservation", co_node[cid], "abnormal return",
                    dr*100 if dr is not None else 0.0, window=wnode, event=True, date=d)
            co_event_window[cid][r["window_type"]] = wnode
            co_event_raw[cid][r["window_type"]].append((d, dr, r.get("volume")))
        else:
            close = r.get("close")
            add_obs(obs, "MarketObservation", co_node[cid], "close price",
                    close if close is not None else 0.0, window=wnode, date=d)
            co_post_window[cid] = wnode
            co_post_raw[cid].append((d, close, r.get("daily_return"), r.get("volume")))

    # --- comparators (05): raw + window entities ---
    cmp_rows = rows("05_comparators")
    cwin = {}; cmp_by_name = defaultdict(list)
    for r in cmp_rows: cmp_by_name[r["comparator_name"]].append(r)
    for name, rs in cmp_by_name.items():
        dates = sorted(to_date(x["trade_date"]) for x in rs)
        node = n(f"window_comp_{slug(name)}"); cwin[name] = node
        g.add((node, RDF.type, CORE.AnalysisWindow))
        g.add((node, CORE.hasStartDate, Literal(dates[0], datatype=XSD.date)))
        g.add((node, CORE.hasEndDate, Literal(dates[-1], datatype=XSD.date)))
        g.add((node, CORE.hasWindowType, lit(rs[0].get("window_type") or "comparator-window")))
    sector_window = {}; bench_window = None
    sector_raw = defaultdict(list); bench_raw = []
    for r in cmp_rows:
        if r.get("value") is None: continue
        oid = r["comparator_obs_id"]; obs = n(f"comp_{oid}"); d = to_date(r["trade_date"]); name = r["comparator_name"]
        if r["comparator_type"] in cfg["benchmark_types"]:
            add_obs(obs, "MarketObservation", BENCH, "comparator value", r["value"], window=cwin[name], date=d)
            bench_raw.append((d, r["value"], r.get("daily_return"))); bench_window = cwin[name]
        else:
            sec = r.get("sector_name_if_applicable")
            add_obs(obs, "MarketObservation", sector_classifier(sec), "comparator value", r["value"], window=cwin[name], date=d)
            sector_raw[sec].append((d, r["value"], r.get("daily_return"))); sector_window[sec] = cwin[name]

    # --- fx (06): raw + window ---
    fx_all_raw = []
    fx_dates = []
    for r in rows(cfg["fx_stem"]):
        oid = r["fx_obs_id"]; obs = n(f"fx_{oid}"); d = to_date(r["trade_date"]); rate = r[cfg["fx_rate_col"]]
        obs_types(obs, "ExchangeRateObservation", "Observation")
        g.add((obs, CORE.isObservationOf, FXPAIR))
        g.add((obs, CORE.hasBaseCurrency, CUR_USD)); g.add((obs, CORE.hasDealtCurrency, CUR_LOCAL))
        g.add((obs, CORE.hasMetricName, lit("exchange rate"))); g.add((obs, CORE.hasMetricValue, dec(rate)))
        g.add((obs, CORE.hasObservationDate, Literal(d, datatype=XSD.date)))
        fx_all_raw.append((d, rate)); fx_dates.append(d)
    fx_window = n("window_fx_series")
    if fx_dates:
        fx_dates.sort()
        g.add((fx_window, RDF.type, CORE.AnalysisWindow))
        g.add((fx_window, CORE.hasStartDate, Literal(fx_dates[0], datatype=XSD.date)))
        g.add((fx_window, CORE.hasEndDate, Literal(fx_dates[-1], datatype=XSD.date)))
        g.add((fx_window, CORE.hasWindowType, lit("fx-series-window")))

    # ==================================================================
    # DERIVED ANALYTICAL METRICS  (the inputs the CQs actually need)
    # ==================================================================
    d_post_ret = {}; d_fund_grow = {}; d_sect_ret = {}; d_bench_ret = {}
    d_fx_corr_co = {}; d_event_ar = defaultdict(dict); d_event_vol = defaultdict(dict)
    d_fx_corr_bm = None; d_fx_change = None
    gscale = cfg.get("growth_scale", 1.0)

    fx_ret = daily_returns(fx_all_raw)                                  # date -> fx daily return
    bench_dr = {d: dr for d, v, dr in bench_raw if dr is not None}      # date -> benchmark daily return
    sector_dr = {sec: {d: dr for d, v, dr in series if dr is not None}  # sector -> date -> daily return
                 for sec, series in sector_raw.items()}

    def cum_ret(dr_by_date, dates):
        vals = [dr_by_date[d] for d in dates if d in dr_by_date]
        return sum(vals) * 100.0 if vals else None

    for cid in co_node:
        recs = co_post_raw.get(cid, [])
        win_dates = [d for d, _, _, _ in recs]
        co_dr = {d: dr for d, _, dr, _ in recs if dr is not None}
        last = sorted(win_dates)[-1] if win_dates else None
        sec = co_sector.get(cid)
        # company post-report window return % (cumulative daily return over its window)
        cr = cum_ret(co_dr, win_dates)
        if cr is None:
            cr = window_return([(d, c) for d, c, _, _ in recs])
        if cr is not None and cid in co_post_window:
            node = n(f"derived_post_return_{cid}")
            add_obs(node, "MarketObservation", co_node[cid], M_POST_RET, cr, window=co_post_window[cid], date=last)
            d_post_ret[cid] = node
        # benchmark return over THIS company's window
        br = cum_ret(bench_dr, win_dates)
        if br is not None and cid in co_post_window:
            node = n(f"derived_bench_return_{cid}")
            add_obs(node, "MarketObservation", BENCH, M_BENCH_RET, br, window=co_post_window[cid], date=last)
            d_bench_ret[cid] = node
        # sector return over THIS company's window
        if sec in sector_dr:
            sr = cum_ret(sector_dr[sec], win_dates)
            if sr is not None and cid in co_post_window:
                node = n(f"derived_sector_return_{cid}")
                add_obs(node, "MarketObservation", sector_classifier(sec), M_SECT_RET, sr, window=co_post_window[cid], date=last)
                d_sect_ret[cid] = node
        # FX vs company daily-return correlation
        corr = pearson(fx_ret, co_dr)
        if corr is not None and cid in co_post_window:
            node = n(f"derived_fx_corr_company_{cid}")
            add_obs(node, "MarketObservation", co_node[cid], M_FX_CORR_CO, corr, window=co_post_window[cid], date=sorted(co_dr)[-1])
            d_fx_corr_co[cid] = node
        # fundamentals YoY profit growth % (latest fiscal year with a value)
        for fy, r, period in sorted(co_fund_rows.get(cid, []), key=lambda x: x[0], reverse=True):
            grow = r.get("yoy_profit_growth_pct")
            if grow is not None:
                node = n(f"derived_fund_growth_{cid}")
                add_obs(node, "FundamentalObservation", co_node[cid], M_FUND_GROW, grow * gscale,
                        period=period, date=to_date(r.get("report_date") or r["period_end_date"]))
                d_fund_grow[cid] = node
                break

    # FX vs benchmark correlation + FX window change %
    bcorr = pearson(fx_ret, bench_dr)
    if bcorr is not None and bench_window is not None:
        d_fx_corr_bm = n("derived_fx_corr_bench")
        add_obs(d_fx_corr_bm, "MarketObservation", BENCH, M_FX_CORR_BM, bcorr, window=bench_window,
                date=sorted(bench_dr)[-1] if bench_dr else None)
    fxc = window_return(fx_all_raw)
    if fxc is not None and fx_dates:
        d_fx_change = n("derived_fx_change")
        obs_types(d_fx_change, "ExchangeRateObservation", "Observation")
        g.add((d_fx_change, CORE.isObservationOf, FXPAIR))
        g.add((d_fx_change, CORE.hasBaseCurrency, CUR_USD)); g.add((d_fx_change, CORE.hasDealtCurrency, CUR_LOCAL))
        g.add((d_fx_change, CORE.hasMetricName, lit(M_FX_CHANGE))); g.add((d_fx_change, CORE.hasMetricValue, dec(fxc)))
        g.add((d_fx_change, CORE.observedOverWindow, fx_window))
        g.add((d_fx_change, CORE.hasObservationDate, Literal(fx_dates[-1], datatype=XSD.date)))

    # event-window cumulative abnormal return % and abnormal volume ratio
    for cid, by_wt in co_event_raw.items():
        base_vols = [v for _, _, _, v in co_post_raw.get(cid, []) if v]
        base_vol = (sum(base_vols)/len(base_vols)) if base_vols else None
        for wt, recs in by_wt.items():
            wnode = co_event_window[cid][wt]
            ar = sum((dr*100.0) for _, dr, _ in recs if dr is not None)
            node = n(f"derived_event_ar_{cid}_{slug(wt)}")
            add_obs(node, "MarketObservation", co_node[cid], M_EVENT_AR, ar, window=wnode, event=True,
                    date=sorted(d for d, _, _ in recs)[-1])
            d_event_ar[cid][wt] = node
            vols = [v for _, _, v in recs if v]
            if base_vol and vols:
                ratio = (sum(vols)/len(vols)) / base_vol
                vnode = n(f"derived_event_vol_{cid}_{slug(wt)}")
                add_obs(vnode, "MarketObservation", co_node[cid], M_EVENT_VOL, ratio, window=wnode, event=True,
                        date=sorted(d for d, _, _ in recs)[-1])
                d_event_vol[cid][wt] = vnode

    # ------------------------------------------------------------------
    # CQ recipe over DERIVED metrics (entity/evidence from sheet 09)
    # ------------------------------------------------------------------
    def recipe(fam, cid):
        out = []
        if fam == "CQ1":   out += [d_fund_grow.get(cid), d_post_ret.get(cid), d_bench_ret.get(cid)]
        elif fam == "CQ2": out += [d_fx_corr_co.get(cid), d_fx_corr_bm, d_fx_change]
        elif fam == "CQ3": out += [d_post_ret.get(cid), d_sect_ret.get(cid), d_bench_ret.get(cid)]
        elif fam == "CQ4": out += list(d_event_ar.get(cid, {}).values()) + list(d_event_vol.get(cid, {}).values())
        elif fam == "CQ5": out += [d_fund_grow.get(cid), d_post_ret.get(cid), d_bench_ret.get(cid)]
        return [o for o in out if o is not None]

    BENCH_FAM = {"CQ1", "CQ2", "CQ3"}
    def parse_ids(v):
        return [x.strip() for x in re.split(r"[;,\[\]]", str(v)) if x.strip()]
    for r in rows("09_query_cases"):
        fam = r["cq_family"]; cid = r["result_entity_id"]
        bundle = n(f"evidence_bundle_{fam}_1")
        g.add((bundle, RDF.type, CORE.EvidenceBundle)); g.add((bundle, CORE.hasValidationStatus, VALID))
        g.add((bundle, CORE.explainsResultEntity, co_node[cid]))
        for o in recipe(fam, cid): g.add((bundle, CORE.includesObservation, o))
        evids = []
        for raw in parse_ids(r.get("supporting_evidence_item_ids")):
            key = raw
            try: key = int(raw)
            except: pass
            if key in evid_node: evids.append(evid_node[key])
        if not evids and cid in co_announcement: evids = [co_announcement[cid]]
        for e in evids: g.add((bundle, CORE.containsEvidenceItem, e))
        qe = n(f"query_exec_{fam}_1")
        g.add((qe, RDF.type, CORE.QueryExecution)); g.add((qe, CORE.hasEvidenceBundle, bundle))
        g.add((qe, CORE.hasQueryFamilyIdentifier, lit(fam)))
        g.add((qe, CORE.hasQueryInstanceIdentifier, lit(f"{fam}-001")))
        g.add((qe, CORE.hasParameterValues, lit(f"market={market}; resultEntity={cid}; timeContext={r.get('time_context_ids')}")))
        if fam in BENCH_FAM: g.add((qe, CORE.usesMarketIndexBenchmark, BENCH))

    out = os.path.join(HERE, "data", f"demo_{market}.ttl")
    g.serialize(destination=out, format="turtle")
    print(f"[{market}] triples={len(g)} post_ret={len(d_post_ret)} bench_ret={len(d_bench_ret)} "
          f"sect_ret={len(d_sect_ret)} fund_grow={len(d_fund_grow)} event_ar={sum(len(v) for v in d_event_ar.values())}")
    return out

if __name__ == "__main__":
    for m in (sys.argv[1:] or ["psx", "msx"]):
        build(m)
