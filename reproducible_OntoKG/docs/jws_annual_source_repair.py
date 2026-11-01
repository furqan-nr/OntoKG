"""Versioned, bounded annual-source repairs; never edits archived inputs.

Issuer-original statement transcriptions visually reviewed on 2026-10-16.
Run with --self-test for mutation tests, or normally to reproduce the overlay.
"""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import hashlib, json, sys
import openpyxl
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'evaluation_jws/annual_source_repair'
EVIDENCE = ROOT/'evaluation_jws/source_authentication/evidence'
A = Namespace('https://w3id.org/ontokg-eq/annual-source-repair-v1#')
PROV = Namespace('http://www.w3.org/ns/prov#')
SOURCES = {
 'OGDC': dict(file='OGDC_259805.pdf',sha256='f1213c77a62b1a4873fb4bb2c995f262e2211cd6c786b79f737e320d82032172',
   url='https://dps.psx.com.pk/download/document/259805.pdf',page=3,date='2025-09-23',scope='company separate statement; not consolidated'),
 'PPL': dict(file=None,sha256=None,
   url='https://dps.psx.com.pk/download/document/259574.pdf',page=None,date='2025-09-19',scope='unconsolidated company statement; not consolidated',
   review_status='pending_financial_page_visual_review',candidate_annual_report='https://dps.psx.com.pk/download/document/261187.pdf'),
}
VALUES = {
 6:('OGDC',2025,401177969,169903614,'39.50'),
 7:('OGDC',2024,463697861,208975771,'48.59'),
 8:('PPL',2025,242516363,92027450,'33.82'),
 9:('PPL',2024,288797413,114309077,'42.01'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(raw, expected, multiplier, workbook_end, source_end, scope):
    if workbook_end != source_end:return 'period_mismatch'
    if scope != 'company':return 'accounting_scope_mismatch'
    if Decimal(str(raw))*Decimal(str(multiplier)) != Decimal(str(expected)):return 'numeric_mismatch'
    return 'exact_match_after_scale_correction' if multiplier != 1 else 'exact_value_and_unit_match'

def run():
    wbpath=ROOT.parent/'PSX data v4/03_fundamentals_final.xlsx'
    before=sha(wbpath)
    sheet=openpyxl.load_workbook(wbpath,data_only=True).active
    headers={c.value:c.column for c in sheet[1]}
    for s in SOURCES.values():
        if s['file'] and sha(EVIDENCE/s['file']) != s['sha256']:raise ValueError('Source changed: visual review required')
    graph=Graph();graph.bind('repair',A);graph.bind('prov',PROV)
    facts=[];growth=[]
    for row,(symbol,year,sales,pat,eps) in VALUES.items():
        for field,expected in zip(('sales_thousand_pkr','profit_after_tax_thousand_pkr','eps'),(sales,pat,eps)):
            cell=sheet.cell(row,headers[field]);multiplier=1 if field=='eps' else 1000000
            end=sheet.cell(row,headers['period_end_date']).value
            status=check(cell.value,expected,multiplier,end,f'{year}-06-30','company')
            assert status.startswith('exact_')
            arithmetic_status=status
            if symbol=='PPL':status='pending_financial_page_visual_review'
            fact=dict(company=symbol,year=year,workbook=str(wbpath.relative_to(ROOT.parent)),worksheet=sheet.title,
               cell=cell.coordinate,field=field,raw_value=str(cell.value),normalized_value=str(expected),
               normalization_multiplier=multiplier,unit='PKR per share' if field=='eps' else 'thousand PKR',
               period_end=end,accounting_scope=SOURCES[symbol]['scope'],status=status,arithmetic_agreement_with_indexed_table=arithmetic_status,
               original_source_url=sheet.cell(row,headers['source_url']).value,
               replacement_source_url=SOURCES[symbol]['url'],inspected_pdf_page_1_based=SOURCES[symbol]['page'],
               original_preserved=True,source_repair_is_not_publication_date_repair=True)
            facts.append(fact)
            n=A[f'{symbol}_{year}_{cell.coordinate}'];source=URIRef(SOURCES[symbol]['url'])
            graph.add((n,RDF.type,A.AuthenticatedCellRepair if symbol=='OGDC' else A.PendingCellRepair));graph.add((n,PROV.hadPrimarySource,source))
            for k,v in fact.items():
                if v is not None:graph.add((n,A[k],Literal(v)))
        if year==2025:
            for field,current,previous in [('yoy_revenue_growth_pct',sales,VALUES[row+1][2]),('yoy_profit_growth_pct',pat,VALUES[row+1][3])]:
                recomputed=(Decimal(current)-Decimal(previous))/abs(Decimal(previous))*100
                raw=Decimal(str(sheet.cell(row,headers[field]).value))
                assert abs(raw-recomputed)<Decimal('0.000000001')
                growth.append(dict(company=symbol,field=field,recomputed=str(recomputed),archived=str(raw),
                   absolute_difference=str(abs(raw-recomputed)),status='unchanged_common_scale_cancels',
                   source_status='visually_verified' if symbol=='OGDC' else 'pending_financial_page_visual_review'))
    assert sha(wbpath)==before
    result=dict(version='annual-source-repair-v1',review_date='2026-10-16',workbook_sha256=before,
      sources=SOURCES,facts=facts,status_counts=dict(Counter(x['status'] for x in facts)),growth_checks=growth,
      limits=['Twelve purposively selected company annual facts, not representative source coverage.',
       'FY2024 verified as comparative columns in FY2025 statements, not separately against original FY2024 releases.',
       'Statement dates are not authenticated first-publication timestamps. No report window changed.',
       'Archived workbook and financial-v2 graphs untouched. Overlay must be explicitly consumed.',
       'Hash binds downloaded copy, not a publisher digital signature. Source redistribution rights not established.'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    graph.serialize(OUT/'repairs.ttl',format='turtle')
    print(json.dumps(result['status_counts']))

def self_test():
    assert check('401.177969',401177969,1000000,'2025-06-30','2025-06-30','company')=='exact_match_after_scale_correction'
    assert check('401.177969',401177969,1,'2025-06-30','2025-06-30','company')=='numeric_mismatch'
    assert check('39.5','39.50',1,'2025-06-30','2025-12-31','company')=='period_mismatch'
    assert check('39.5','39.50',1,'2025-06-30','2025-06-30','consolidated')=='accounting_scope_mismatch'
    assert check('39.5','39.51',1,'2025-06-30','2025-06-30','company')=='numeric_mismatch'
    print('5 source-repair assertions passed')
if __name__=='__main__':self_test() if '--self-test' in sys.argv else run()
