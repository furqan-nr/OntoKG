"""Quarantine report-event claims unsupported by actual window semantics.

Read-only over all prior graphs/workbooks; separate decisions and RDF overlay.
No publication date is invented or changed to make a contract pass.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
from rdflib import Graph, Namespace, URIRef, Literal
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/temporal_resolution'
T = Namespace('https://w3id.org/ontokg-eq/temporal-resolution-v1#')
DATE_EVIDENCE = {
    'https://w3id.org/ontokg-eq/msx#company_MY_CO_MAYBANK': dict(date='2026-04-01', status='official_annual_report_announcement_date_matched', url='https://maybank.listedcompany.com/news.html/id/2605866', locator='Announcement Info: Date Announced 01 Apr 2026; reference DCS-01042026-00004', event='Annual Report & CG Report - 2025', first_earnings_release_authenticated=False),
    'https://w3id.org/ontokg-eq/psx#company_2': dict(date='2026-01-29', status='official_financial_results_document_date_matched', url='https://dps.psx.com.pk/download/document/269389.pdf', locator='Page 1, issuer letter Ref 6.12-PSX/S/FFC dated January 29 2026; board meeting 29/01/2026 at 1030', event='FFC financial results year ended December 31 2025', first_earnings_release_authenticated=False),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    values = wb.active.values
    headers = next(values)
    result = [dict(zip(headers, row)) for row in values]
    wb.close()
    return result

def decide(rule, anchor_types, metadata_status, temporal_statuses):
    if rule != 'R1':
        return 'not_a_report_event_claim'
    if 'recent_analysis_window' in anchor_types:
        return 'quarantined_non_report_analysis_window'
    if 'mismatch' in temporal_statuses:
        return 'quarantined_temporal_mismatch'
    if not temporal_statuses or 'absent_or_ambiguous' in temporal_statuses:
        return 'quarantined_missing_temporal_metadata'
    if metadata_status != 'verified_as_declared':
        return 'quarantined_other_metadata'
    return 'declared_alignment_only_not_authenticated'

def controls():
    expected = [
        ('R1', {'recent_analysis_window'}, 'verified_as_declared', ['verified_as_declared'], 'quarantined_non_report_analysis_window'),
        ('R1', {'annual_report_2025'}, 'mismatch', ['mismatch'], 'quarantined_temporal_mismatch'),
        ('R1', {'annual_report_2025'}, 'absent_or_ambiguous', ['absent_or_ambiguous'], 'quarantined_missing_temporal_metadata'),
        ('R1', {'annual_report_2025'}, 'verified_as_declared', ['verified_as_declared'], 'declared_alignment_only_not_authenticated'),
        ('R3', {'recent_analysis_window'}, 'verified_as_declared', [], 'not_a_report_event_claim'),
    ]
    for rule, anchors, metadata, statuses, outcome in expected:
        assert decide(rule, anchors, metadata, statuses) == outcome
    return len(expected)

def main():
    expanded_path = ROOT/'evaluation_jws/expanded_evaluation/results.json'
    metadata_path = ROOT/'evaluation_jws/metadata_v2/results.json'
    expanded = json.loads(expanded_path.read_text(encoding='utf-8'))
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    by_key = {(r['dataset'], r['case_index']): r for r in metadata['records']}
    workbook_paths = [ROOT.parent/'scale_up/IDX_scaled_data/03_fundamentals.xlsx', ROOT.parent/'scale_up/IDX_scaled_data/04_market_windows.xlsx', ROOT.parent/'IDX data v1/03_fundamentals.xlsx', ROOT.parent/'IDX data v1/04_market_windows.xlsx']
    initial_hashes = {str(p.relative_to(ROOT.parent)): digest(p) for p in workbook_paths}
    window_rows = {False: rows(workbook_paths[3]), True: rows(workbook_paths[1])}
    records = []
    overlay = Graph(); overlay.bind('temporalresolution', T)
    for dataset in expanded['datasets']:
        name = dataset['dataset']
        if 'financial_v2' not in name:
            continue
        for index, case in enumerate(dataset['cases']):
            if case['label'] != 'positive':
                continue
            md = by_key[(name, index)]
            symbol = case['company'].split('company_')[-1]
            wr = [r for r in window_rows['scaled' in name] if r.get('company_id') == symbol] if 'idx' in name else []
            anchor_types = sorted({str(r.get('anchor_type')) for r in wr if r.get('anchor_type')})
            temporal = [c for c in md['checks'] if c['check'] in {'report_date_equals_window_anchor', 'post_report_window_starts_on_or_after_anchor', 'fiscal_period_ends_before_or_on_report'}]
            decision = decide(case['rule'], set(anchor_types), md['metadata_status'], [c['status'] for c in temporal])
            rec = dict(dataset=name, case_index=index, company=case['company'], rule=case['rule'], numerical_label='positive', original_metadata_status=md['metadata_status'], workbook_anchor_types=anchor_types, temporal_checks=temporal, decision=decision, publication_date_authenticated=False, eligible_authenticated_report_event=False)
            evidence = DATE_EVIDENCE.get(case['company']) if case['rule'] == 'R1' else None
            if evidence:
                declared = next(c for c in temporal if c['check']=='report_date_equals_window_anchor')
                assert evidence['date'] == declared['report_date'] == declared['anchor_date']
                rec['official_date_evidence'] = evidence
                rec['publication_date_authenticated'] = evidence['status']=='official_annual_report_announcement_date_matched'
                rec['decision'] = evidence['status']
            records.append(rec)
            finding = URIRef(f'https://w3id.org/ontokg-eq/expanded/{name}/{index}')
            overlay.add((finding, T.decision, Literal(rec['decision'])))
            if evidence:
                overlay.add((finding, T.officialDateSource, URIRef(evidence['url'])))
                overlay.add((finding, T.officialDateEvidenceStatus, Literal(evidence['status'])))
            overlay.add((finding, T.authenticatedReportEvent, Literal(False)))
            if decision.startswith('quarantined'):
                overlay.add((finding, T.quarantinedForReportEventUse, Literal(True)))
    summaries = []
    for name in sorted({r['dataset'] for r in records}):
        subset = [r for r in records if r['dataset'] == name]
        summaries.append(dict(dataset=name, numerical_positive=len(subset), decisions=dict(Counter(r['decision'] for r in subset)), authenticated_annual_report_announcement_dates=sum(r['publication_date_authenticated'] for r in subset), official_document_dates_matched=sum('official_date_evidence' in r for r in subset), authenticated_first_earnings_event_positives=0))
    assert initial_hashes == {str(p.relative_to(ROOT.parent)): digest(p) for p in workbook_paths}
    result = dict(version='1.0', scope='Positive corrected cases only; strict report-event quarantine, no relaxed replacement contract', input_hashes={'expanded':digest(expanded_path),'metadata':digest(metadata_path)}, preserved_workbook_sha256=initial_hashes, summaries=summaries, records=records, synthetic_controls_passed=controls(), authenticated_annual_report_publication_dates=1, authenticated_first_earnings_publication_timestamps=0, source_review_date='2026-10-16')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    overlay.serialize(OUT/'quarantine_overlay.ttl', format='turtle')
    lines = ['# Temporal resolution v1', '', 'No historical or financial-v2 date is rewritten. Numerical positives remain numerical positives; a quarantined case is excluded from report-event validation.', '', '| Corrected cohort | Numerical positives | Decision counts | Authenticated first-earnings events |', '|---|---:|---|---:|']
    for s in summaries:
        lines.append(f"| {s['dataset']} | {s['numerical_positive']} | {s['decisions']} | 0 |")
    lines += ['', '## Why dates cannot simply be matched', '', 'The scaled input explicitly calls its market anchors recent_analysis_window. Its latest fundamentals report_date equals fiscal year-end (2025-12-31); this does not authenticate a publication date. All 20 positive scaled R1 cases are quarantined as non-report analysis windows, regardless of whether an equality check could be made to pass. The 22 remaining scaled numerical positives are non-R1 classifications; this is not 22 authenticated report events.', '', 'Curated TOWR has report date 2026-03-18 and window anchor 2026-03-25. Its numerical R1 positive is quarantined. No primary publication timestamp was authenticated in this audit, and neither date is substituted for the other.', '', 'Other aligned declarations remain declared-only, not externally authenticated. A delayed window may be scientifically meaningful but is not the strict release-anchored claim. Recent-window R2/R3 comparisons may be reported descriptively without claiming a report reaction.', '', '## Source reconnaissance (2026-10-16)', '', '[ANTAM official annual report listing](https://antam.com/id/company-report/annual-report) was indexed with “Laporan Tahunan 2025 (30 April 2026)”; the direct text retrieval did not expose that listing. This is a bounded source lead, not an authenticated first-earnings announcement and not used to alter any date. It illustrates the need to distinguish fiscal end, financial-statement authorization, earnings publication, and annual-report upload. TOWR official financial-report URL was inaccessible through the retrieval tool; third-party March 18/March 25 listings were not promoted to primary-source authentication.', '', '## Required recovery procedure', '', 'For each quarantined R1 case obtain the official earnings release or exchange disclosure with publication date/time and timezone; identify the exact accounting period/scope; obtain company and benchmark close endpoints covering the predeclared same-calendar horizon; reconstruct returns on identical observed intervals; document whether a same-day close follows disclosure. Missing horizon coverage stays incomplete. Do not infer publication from fiscal end, auditor signature, search snippet, retrieval date, or annual-report upload alone. Current data do not support an authenticated full-horizon recomputation, so no synthetic replacement result is claimed.', '', 'The overlay is a separate exclusion ledger, not a replacement ontology or modified production finding graph. Reproduce with docs/jws_temporal_resolution.py after metadata_v2. Five synthetic controls assert strict quarantine and ensure recent windows cannot pass merely through matching date declarations.']
    lines += ['', '## Bounded official date matches', '', '[Maybank issuer announcement](https://maybank.listedcompany.com/news.html/id/2605866) explicitly records 01 Apr 2026 for the FY2025 annual report and CG report, reference DCS-01042026-00004. This authenticates the recorded annual-report announcement date and matches the window anchor; observations begin April 2. It does not establish first disclosure of FY2025 earnings, precise upload time, or source truth of market prices.', '', '[FFC exchange-hosted issuer disclosure](https://dps.psx.com.pk/download/document/269389.pdf), page 1, is dated January 29 2026 and reports the FY2025 financial-results board meeting on that date. It matches the PSX R1 anchor; observations begin January 30. This authenticates the issuer document date, not an independently logged exchange upload timestamp or proof of first publication. Both distinctions are preserved in JSON and RDF. Maxis official annual report contains an AGM notice dated April16 2026, but a notice date is not automatically an annual-report publication date; its R1 remains declared-only.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(summaries, indent=2))

if __name__ == '__main__':
    main()
