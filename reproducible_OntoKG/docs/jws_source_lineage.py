"""Audit and add explicit workbook-cell lineage in a separate RDF overlay.

Does not change the builder or original graphs. A matching computed value checks
the proposed dependency mapping, not the truth of the upstream source. Run from
any directory; dependencies: openpyxl, rdflib. Outputs evaluation_jws/source_lineage.*.
"""
from pathlib import Path
import sys
import csv
import hashlib
import json
import math
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_market_graph as builder
import openpyxl
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD

CORE = builder.CORE
PROV = Namespace("http://www.w3.org/ns/prov#")
AUD = Namespace("https://w3id.org/ontokg-eq/lineage-audit#")
OUT = ROOT / "evaluation_jws"


def read_rows(cfg, stem):
    paths = sorted(Path(cfg["data_dir"]).glob(f"{cfg['prefix']}{stem}*.xlsx"))
    if len(paths) != 1:
        raise ValueError(f"Expected one workbook for {stem}, found {paths}")
    path = paths[0].resolve()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    header = next(ws.iter_rows(values_only=True))
    rows = []
    for number, vals in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if any(v is not None for v in vals):
            r = dict(zip(header, vals))
            r.update(_path=path, _sheet=ws.title, _row=number,
                     _cols={name: i + 1 for i, name in enumerate(header)})
            rows.append(r)
    wb.close()
    return rows


def date(r):
    return builder.to_date(r["trade_date"])


def mean(vals):
    return sum(vals) / len(vals) if vals else None


def run_market(market):
    cfg = builder.CONFIG[market]
    ns = Namespace(cfg["ns"])
    base_path = ROOT / "data" / f"demo_{market}.ttl"
    base = Graph().parse(base_path)
    overlay = Graph()
    for prefix, uri in [("prov", PROV), ("audit", AUD), ("core", CORE)]:
        overlay.bind(prefix, uri)
    sheets = {stem: read_rows(cfg, stem) for stem in ["02_company_master", "03_fundamentals", "04_market_windows", "05_comparators", cfg["fx_stem"], "08_provenance"]}
    source_rows = defaultdict(list)
    for r in sheets["08_provenance"]:
        source_rows[str(r.get("source_id"))].append(r)
    workbook_hash = {}
    cell_cache = {}
    records = []
    tracked = set()

    def node(local):
        return ns[builder.slug(local)]

    def cell(r, field):
        key = (str(r["_path"]), r["_sheet"], r["_row"], field)
        if key in cell_cache:
            return cell_cache[key]
        path = r["_path"]
        if path not in workbook_hash:
            workbook_hash[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        uri = AUD[f"{market}_{builder.slug(path.stem)}_{builder.slug(r['_sheet'])}_row{r['_row']}_{builder.slug(field)}"]
        cell_cache[key] = uri
        overlay.add((uri, RDF.type, PROV.Entity))
        overlay.add((uri, AUD.workbookPath, Literal(path.relative_to(ROOT.parent).as_posix())))
        overlay.add((uri, AUD.workbookSHA256, Literal(workbook_hash[path])))
        overlay.add((uri, AUD.worksheet, Literal(r["_sheet"])))
        overlay.add((uri, AUD.excelRowNumber, Literal(r["_row"], datatype=XSD.integer)))
        overlay.add((uri, AUD.fieldName, Literal(field)))
        overlay.add((uri, AUD.excelCell, Literal(f"{openpyxl.utils.get_column_letter(r['_cols'][field])}{r['_row']}")))
        overlay.add((uri, AUD.cellValue, Literal(str(r.get(field)))))
        for ident in ("period_id", "market_obs_id", "comparator_obs_id", "fx_obs_id", "company_id"):
            if r.get(ident) is not None:
                overlay.add((uri, AUD.originalRowIdentifier, Literal(f"{ident}={r[ident]}")))
        sid = r.get("source_id")
        if sid is not None:
            overlay.add((uri, AUD.sourceIdentifier, Literal(str(sid))))
            overlay.add((uri, AUD.sourceIdentifierCell, Literal(f"{openpyxl.utils.get_column_letter(r['_cols']['source_id'])}{r['_row']}")))
            register = source_rows.get(str(sid), [])
            if len(register) == 1:
                source = node(f"source_{sid}")
                overlay.add((uri, PROV.hadPrimarySource, source))
                overlay.add((source, RDF.type, PROV.Entity))
                overlay.add((source, CORE.hasSourceIdentifier, Literal(str(sid))))
                sr = register[0]
                if sr["_path"] not in workbook_hash:
                    workbook_hash[sr["_path"]] = hashlib.sha256(sr["_path"].read_bytes()).hexdigest()
                overlay.add((source, AUD.sourceRegisterWorkbook, Literal(sr["_path"].relative_to(ROOT.parent).as_posix())))
                overlay.add((source, AUD.sourceRegisterSHA256, Literal(workbook_hash[sr["_path"]])))
                overlay.add((source, AUD.sourceRegisterWorksheet, Literal(sr["_sheet"])))
                overlay.add((source, AUD.sourceRegisterRow, Literal(sr["_row"], datatype=XSD.integer)))
                if register[0].get("source_url"):
                    overlay.add((source, CORE.hasSourceURL, Literal(str(register[0]["source_url"]), datatype=XSD.anyURI)))
        return uri

    def record(obs, dependencies, expected, formula, note=""):
        if (obs, RDF.type, CORE.Observation) not in base:
            return
        tracked.add(obs)
        deps = list({(str(r["_path"]), r["_row"], f): (r, f) for r, f in dependencies if f in r and r.get(f) is not None}.values())
        stored = base.value(obs, CORE.hasMetricValue)
        error = abs(float(stored) - float(expected)) if stored is not None and expected is not None else None
        value_match = error is not None and error <= 0.000002
        missing = sum(not r.get("source_id") for r, f in deps)
        unresolved = sum(len(source_rows.get(str(r.get("source_id")), [])) != 1 for r, f in deps)
        status = "mapped_value_match" if value_match and deps else "unresolved_value_or_dependencies"
        if value_match and deps:
            for r, field in deps:
                overlay.add((obs, PROV.wasDerivedFrom, cell(r, field)))
            overlay.add((obs, AUD.mappingMethod, Literal(formula)))
            overlay.add((obs, AUD.sourceTruthVerified, Literal(False)))
        records.append(dict(market=market, observation=str(obs), metric=str(base.value(obs, CORE.hasMetricName)),
                            status=status, stored_value=str(stored), recomputed_value=expected,
                            absolute_error=error, dependency_cells=len(deps), missing_source_id_cells=missing,
                            unresolved_source_register_cells=unresolved, formula=formula, caveat=note))

    funds = sheets["03_fundamentals"]
    market_rows = sheets["04_market_windows"]
    comparators = [r for r in sheets["05_comparators"] if r.get("value") is not None]
    fx = sheets[cfg["fx_stem"]]
    # Raw observation IDs must identify one source row; collisions remain unresolved.
    for rows, ident, prefix, field_fn in [
        (funds, "period_id", "fund_", lambda r: cfg["eps_col"] if r.get(cfg["eps_col"]) is not None else "profit_after_tax_million_myr" if r.get("profit_after_tax_million_myr") else "profit_after_tax_thousand_pkr"),
        (market_rows, "market_obs_id", "mkt_", lambda r: "daily_return" if builder.is_event(r["window_type"]) else "close"),
        (comparators, "comparator_obs_id", "comp_", lambda r: "value"),
        (fx, "fx_obs_id", "fx_", lambda r: cfg["fx_rate_col"]),
    ]:
        counts = defaultdict(int)
        for r in rows:
            counts[str(r[ident])] += 1
        for r in rows:
            field = field_fn(r)
            value = r.get(field)
            if prefix == "mkt_" and builder.is_event(r["window_type"]) and value is not None:
                value *= 100
            record(node(prefix + str(r[ident])), [(r, field)] if counts[str(r[ident])] == 1 else [], value,
                   "direct cell" if prefix != "mkt_" or not builder.is_event(r["window_type"]) else "daily_return * 100 (builder labels this abnormal return)",
                   "Row source association is recorded, not independently verified against original source.")

    post = defaultdict(list)
    events = defaultdict(list)
    for r in market_rows:
        (events[(r["company_id"], r["window_type"])] if builder.is_event(r["window_type"]) else post[r["company_id"]]).append(r)
    bench = [r for r in comparators if r["comparator_type"] in cfg["benchmark_types"]]
    sectors = defaultdict(list)
    for r in comparators:
        if r["comparator_type"] not in cfg["benchmark_types"]:
            sectors[r.get("sector_name_if_applicable")].append(r)

    def return_record(obs, rows, dates):
        # Builder chooses last non-null daily_return per date and then sums over
        # the company window date list (including duplicates if present).
        by_date = {date(r): r for r in rows if r.get("daily_return") is not None}
        selected = [by_date[d] for d in dates if d in by_date]
        if selected:
            record(obs, [(r, "daily_return") for r in selected], sum(r["daily_return"] for r in selected) * 100,
                   "sum workbook daily_return over company window dates * 100", "Summed simple returns, not compounded holding-period returns.")

    fx_sorted = sorted([r for r in fx if r.get(cfg["fx_rate_col"]) is not None], key=date)
    fx_returns = {}
    for prev, current in zip(fx_sorted, fx_sorted[1:]):
        if prev[cfg["fx_rate_col"]]:
            fx_returns[date(current)] = (current[cfg["fx_rate_col"]] / prev[cfg["fx_rate_col"]] - 1, prev, current)

    def correlation_record(obs, rows):
        by_date = {date(r): r for r in rows if r.get("daily_return") is not None}
        keys = sorted(set(by_date) & set(fx_returns))
        deps = []
        for d in keys:
            deps.extend([(by_date[d], "daily_return"), (fx_returns[d][1], cfg["fx_rate_col"]), (fx_returns[d][2], cfg["fx_rate_col"])])
        value = builder.pearson({d: fx_returns[d][0] for d in keys}, {d: by_date[d]["daily_return"] for d in keys})
        record(obs, deps, value, "Pearson on shared dates; FX return from consecutive sorted rate cells", "Workbook daily returns are inputs; their upstream price derivation is not reconstructed.")

    for company in sheets["02_company_master"]:
        cid = company["company_id"]
        rows = post[cid]
        dates = [date(r) for r in rows]
        return_record(node(f"derived_post_return_{cid}"), rows, dates)
        # If the builder used close-price endpoint fallback, trace only endpoints.
        if node(f"derived_post_return_{cid}") not in tracked:
            valid = sorted([r for r in rows if r.get("close") is not None], key=date)
            if len(valid) >= 2 and valid[0]["close"]:
                record(node(f"derived_post_return_{cid}"), [(valid[0], "close"), (valid[-1], "close")],
                       (valid[-1]["close"] / valid[0]["close"] - 1) * 100, "close-price endpoint return fallback")
        return_record(node(f"derived_bench_return_{cid}"), bench, dates)
        return_record(node(f"derived_sector_return_{cid}"), sectors[company["sector"]], dates)
        correlation_record(node(f"derived_fx_corr_company_{cid}"), rows)
        eligible = sorted([r for r in funds if r["company_id"] == cid and r.get("yoy_profit_growth_pct") is not None], key=lambda r: int(r["fiscal_year"]), reverse=True)
        if eligible:
            r = eligible[0]
            record(node(f"derived_fund_growth_{cid}"), [(r, "yoy_profit_growth_pct")], r["yoy_profit_growth_pct"] * cfg["growth_scale"],
                   "latest fiscal-year supplied growth cell * market growth_scale", "Supplied growth is not independently recomputed from original profit disclosures.")

    correlation_record(node("derived_fx_corr_bench"), bench)
    if len(fx_sorted) >= 2 and fx_sorted[0][cfg["fx_rate_col"]]:
        field = cfg["fx_rate_col"]
        record(node("derived_fx_change"), [(fx_sorted[0], field), (fx_sorted[-1], field)],
               (fx_sorted[-1][field] / fx_sorted[0][field] - 1) * 100, "FX endpoint percentage change")
    for (cid, wt), rows in events.items():
        selected = [r for r in rows if r.get("daily_return") is not None]
        record(node(f"derived_event_ar_{cid}_{builder.slug(wt)}"), [(r, "daily_return") for r in selected],
               sum(r["daily_return"] for r in selected) * 100, "sum event workbook daily_return * 100",
               "Current builder does not subtract benchmark here. Whether workbook returns are already abnormal requires upstream verification; no announcement is asserted as numeric source.")
        event_vol = [r for r in rows if r.get("volume")]
        base_vol = [r for r in post[cid] if r.get("volume")]
        if event_vol and base_vol:
            record(node(f"derived_event_vol_{cid}_{builder.slug(wt)}"), [(r, "volume") for r in event_vol + base_vol],
                   mean([r["volume"] for r in event_vol]) / mean([r["volume"] for r in base_vol]),
                   "mean event volume / mean nonzero post-report volume")

    for obs in set(base.subjects(RDF.type, CORE.Observation)) - tracked:
        record(obs, [], None, "unresolved observation: no unique implemented mapping")
    overlay.serialize(OUT / f"source_lineage.{market}.ttl", format="turtle")
    reparsed = Graph().parse(OUT / f"source_lineage.{market}.ttl")
    assert len(reparsed) == len(overlay), "Serialized overlay changed triple count"
    for c in cell_cache.values():
        sid = overlay.value(c, AUD.sourceIdentifier)
        if sid is not None and len(source_rows.get(str(sid), [])) == 1:
            source = overlay.value(c, PROV.hadPrimarySource)
            assert source is not None and overlay.value(source, CORE.hasSourceIdentifier) == sid
    inferred_path = ROOT / "data" / f"demo_{market}_inferred.ttl"
    support = {}
    if inferred_path.exists():
        inferred = Graph().parse(inferred_path)
        supported = set(inferred.objects(None, CORE.supportedByObservation))
        covered = {o for o in supported if any(overlay.objects(o, PROV.wasDerivedFrom))}
        support = dict(support_graph_sha256=hashlib.sha256(inferred_path.read_bytes()).hexdigest(),
                       supported_observations=len(supported), supported_mapped=len(covered),
                       supported_unresolved=sorted(str(o) for o in supported - covered))
    # Explicit completeness check is about mapped dependency cells, not sources' truth.
    assert len(records) >= len(set(base.subjects(RDF.type, CORE.Observation)))
    return records, dict(market=market, observations=len(set(base.subjects(RDF.type, CORE.Observation))),
                         mapped_observations=len({r["observation"] for r in records if r["status"] == "mapped_value_match"}),
                         unresolved_observations=len({r["observation"] for r in records if r["status"] != "mapped_value_match"}),
                         mapped_cells=len(cell_cache), overlay_triples=len(overlay),
                         overlay_roundtrip_and_source_id_smoke_check="passed", **support,
                         source_graph_sha256=hashlib.sha256(base_path.read_bytes()).hexdigest(),
                         workbook_sha256={p.relative_to(ROOT.parent).as_posix(): v for p, v in workbook_hash.items()})


def main():
    OUT.mkdir(exist_ok=True)
    records, summary = [], []
    for market in builder.CONFIG:
        rows, result = run_market(market)
        records.extend(rows)
        summary.append(result)
    with (OUT / "source_lineage.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (OUT / "source_lineage.json").write_text(json.dumps(dict(summary=summary, records=records), indent=2), encoding="utf-8")
    lines = ["# Observation source-cell lineage audit and separate overlay", "", "This adds workbook-cell and explicit source-register lineage, not independent verification of original sources. Base graphs remain unchanged. No company announcement is used as evidence for a market metric solely because it concerns the same company.", "", "| Market | Observations | Value-matched mappings | Unresolved mappings | Cells |", "| --- | ---: | ---: | ---: | ---: |"]
    for s in summary:
        lines.append(f"| {s['market']} | {s['observations']} | {s['mapped_observations']} | {s['unresolved_observations']} | {s['mapped_cells']} |")
    lines += ["", "## Coverage of actual finding-support observations", "", "These counts use the current data/demo_<market>_inferred.ttl supportedByObservation links, not all observations or contextual announcements. Graph SHA256 values are recorded in JSON.", "", "| Market | Distinct supporting observations | Source-cell mapped | Unresolved |", "| --- | ---: | ---: | ---: |"]
    for s in summary:
        if "supported_observations" in s:
            lines.append(f"| {s['market']} | {s['supported_observations']} | {s['supported_mapped']} | {len(s['supported_unresolved'])} |")
    lines += ["", "Unresolved finding-support observations:"]
    for s in summary:
        for obs in s.get("supported_unresolved", []):
            lines.append(f"- {s['market']}: `{obs}`")
    lines += ["", "Overlay Turtle round-trip and source_id-to-register identity smoke checks passed for every market."]
    missing = sum(r["missing_source_id_cells"] for r in records if r["status"] == "mapped_value_match")
    unresolved = sum(r["unresolved_source_register_cells"] for r in records if r["status"] == "mapped_value_match")
    lines += ["", f"Across mapped observation-dependency pairs, {missing} cells lack source_id and {unresolved} cells do not resolve to exactly one source-register row (shared cells may be counted repeatedly).", "", "Each mapped observation links through prov:wasDerivedFrom to exact workbook field entities carrying file SHA256, worksheet, Excel cell, original row identifiers and explicit source_id cell. Cell entities link via prov:hadPrimarySource only when their source_id resolves uniquely in sheet 08. The source-register workbook hash, worksheet and row are retained. Registered URLs are recorded rather than treated as checked or official. Dependencies describe the implemented calculations; workbook row lineage is not equivalent to provenance of the original published numbers.", "", "## Remaining gaps", "", "- Current builder uses summed daily returns; the manuscript's compounding claim needs reconciliation.", "- Event metrics sum the supplied event daily_return cells without benchmark subtraction in this builder. Those cells may already represent abnormal returns; their upstream meaning requires verification before an abnormal-return claim is accepted or the implementation changed.", "- Supplied growth and comparator cells are traced to their workbook/source IDs, but upstream construction from original disclosures or peer constituent data is not certified.", "- Value matches check the proposed mapping against archived graph values; correlation uses the existing Pearson helper, so this is not a fully independent analytical correctness audit.", "- The overlay supplements rather than changes existing CQ5 bundles. Source evidence should be rendered through these dependency links, while official announcements remain contextual event evidence unless a metric-specific relationship is demonstrated.", "- The present unresolved mappings are missing input values represented as default zero observations by the builder (including empty event-return aggregations). They are not certified source-backed zero measurements.", "- Duplicate row identifiers, missing values or unmatched derived values remain unresolved. No fallback attachment to a company disclosure is made.", "", "Reproduce: run docs/jws_source_lineage.py with openpyxl and rdflib installed. Inspect source_lineage.csv for observation-level status and source_lineage.<market>.ttl for the separate overlay."]
    (OUT / "source_lineage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
