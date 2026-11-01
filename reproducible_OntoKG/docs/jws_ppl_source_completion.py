"""Complete only the six pending PPL repairs using a visually reviewed primary PDF.

No archived inputs, previous reports or financial graphs are modified.
"""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import hashlib
import json
import subprocess
import sys
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF
from jws_annual_source_repair import check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/ppl_source_completion'
PDF = ROOT / 'evaluation_jws/source_authentication/evidence/PPL_results_2025_complete.pdf'
HASH = '12b2e2ecdb660e7b068d56d763d5c3a8adb0c7a6a983e15a67fdf983e0f301c5'
URL = 'https://www.psx.com.pk/psx/files-attachment/?file=259574.pdf'
A = Namespace('https://w3id.org/ontokg-eq/ppl-source-completion-v1#')
PROV = Namespace('http://www.w3.org/ns/prov#')
VALUES = {2025: ('242516363', '92027450', '33.82'),
          2024: ('288797413', '114309077', '42.01')}


def validate_pdf(path):
    blob = path.read_bytes()
    if len(blob) != 23576826 or not blob.startswith(b'%PDF-') or b'%%EOF' not in blob[-1024:]:
        raise ValueError('Incomplete or unexpected PDF; no authentication permitted')
    if hashlib.sha256(blob).hexdigest() != HASH:
        raise ValueError('PDF changed: repeat visual review')
    result = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, check=True)
    if result.stderr.strip() or not any(line.startswith('Pages:') and line.split()[-1] == '9'
                                        for line in result.stdout.splitlines()):
        raise ValueError('PDF parse errors or page count mismatch')


def run():
    validate_pdf(PDF)
    oldpath = ROOT / 'evaluation_jws/annual_source_repair/results.json'
    oldblob = oldpath.read_bytes()
    old = json.loads(oldblob)
    facts = []
    graph = Graph()
    graph.bind('pplrepair', A)
    graph.bind('prov', PROV)
    fields = ('sales_thousand_pkr', 'profit_after_tax_thousand_pkr', 'eps')
    for oldfact in old['facts']:
        if oldfact['company'] != 'PPL':
            continue
        fact = dict(oldfact)
        assert fact['status'] == 'pending_financial_page_visual_review'
        expected = VALUES[fact['year']][fields.index(fact['field'])]
        status = check(fact['raw_value'], expected, fact['normalization_multiplier'],
                       fact['period_end'], f"{fact['year']}-06-30", 'company')
        assert status.startswith('exact_')
        fact.update(status=status, normalized_value=expected, replacement_source_url=URL,
                    inspected_pdf_page_1_based=3, source_sha256=HASH,
                    source_document_date='2025-09-19', review_date='2026-10-17',
                    supersedes_status=oldfact['status'],
                    accounting_scope='unconsolidated company statement; not consolidated',
                    source_eligible_for_annual_fact=True,
                    first_publication_timestamp_authenticated=False)
        facts.append(fact)
        node = A[f"PPL_{fact['year']}_{fact['cell']}"]
        graph.add((node, RDF.type, A.AuthenticatedCellRepair))
        graph.add((node, PROV.hadPrimarySource, URIRef(URL)))
        for key, value in fact.items():
            if value is not None:
                graph.add((node, A[key], Literal(value)))
    assert len(facts) == 6
    growth = []
    for field, i in [('yoy_revenue_growth_pct', 0), ('yoy_profit_growth_pct', 1)]:
        current, prior = Decimal(VALUES[2025][i]), Decimal(VALUES[2024][i])
        value = (current-prior)/abs(prior)*100
        archived = next(x for x in old['growth_checks'] if x['company']=='PPL' and x['field']==field)
        assert abs(value-Decimal(archived['archived'])) < Decimal('0.000000001')
        growth.append(dict(field=field, recomputed=str(value), archived=archived['archived'],
                           status='unchanged_common_scale_cancels', source_status='visually_verified'))
    report = dict(version='ppl-source-completion-v1', review_date='2026-10-17',
                  supersedes_report=str(oldpath.relative_to(ROOT)),
                  source=dict(url=URL, canonical_document_url='https://dps.psx.com.pk/download/document/259574.pdf',
                              file=str(PDF.relative_to(ROOT)), sha256=HASH, bytes=23576826,
                              pages=9, inspected_pages=[1,2,3], financial_page=3,
                              date='2025-09-19'),
                  facts=facts, status_counts=dict(Counter(f['status'] for f in facts)), growth_checks=growth,
                  source_eligible_annual_facts_before=6, source_eligible_annual_facts_after=12,
                  coverage_denominator='12 purposively selected OGDC/PPL annual facts only',
                  limitations=['FY2024 verified as FY2025 comparative, not original FY2024 release.',
                               'Source document date is not first publication timestamp.',
                               'No price, benchmark, temporal alignment or market reaction authenticated.',
                               'Hash binds downloaded copy, not a verified publisher digital signature.',
                               'No source redistribution licence established; cite public original.',
                               'Overlay is explicit opt-in; original workbook, graphs and prior report untouched.'],
                  retrieval_attempts=[{'url':'https://www.ppl.com.pk/sites/default/files/2024-10/PPL%20AR%202025.pdf',
                                       'result':'HTTP 403; not used'},
                                      {'url':URL, 'result':'HTTP success, complete PDF, pdfinfo clean, pages visually reviewed'}])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    graph.serialize(OUT/'repairs.ttl', format='turtle')
    assert oldpath.read_bytes() == oldblob
    print(json.dumps(report['status_counts']))


def self_test():
    for year, expected in VALUES.items():
        for field_index, value in enumerate(expected):
            multiplier = 1 if field_index == 2 else 1000000
            raw = Decimal(value)/multiplier
            assert check(raw, value, multiplier, f'{year}-06-30', f'{year}-06-30', 'company').startswith('exact_')
    assert check('33.82', '33.82', 1, '2025-06-30', '2025-12-31', 'company') == 'period_mismatch'
    assert check('33.82', '33.82', 1, '2025-06-30', '2025-06-30', 'consolidated') == 'accounting_scope_mismatch'
    assert check('242.516363', 242516363, 1, '2025-06-30', '2025-06-30', 'company') == 'numeric_mismatch'
    validate_pdf(PDF)
    print('10 PPL authentication checks passed')


if __name__ == '__main__':
    self_test() if '--self-test' in sys.argv else run()
