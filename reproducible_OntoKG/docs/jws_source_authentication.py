"""Recheck bounded, manually visually authenticated primary-source facts.

This does not fetch pages automatically or authenticate unaudited cells. Source
transcriptions below were inspected on 16 October 2026; hashes bind local copies.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from collections import Counter
import hashlib, json
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation_jws/source_authentication'
EVIDENCE = OUT / 'evidence'
SOURCES = {
 'FFC': ('FFC_269389.pdf','https://dps.psx.com.pk/download/document/269389.pdf',4,'issuer-original standalone statement of profit or loss; Annexure A page 2'),
 'ENGROH': ('ENGROH_271307.pdf','https://dps.psx.com.pk/download/document/271307.pdf',16,'issuer-original financial-performance narrative; standalone not consolidated'),
 'OGDC': ('OGDC_270842-1.pdf','https://dps.psx.com.pk/download/attachment/270842-1.pdf',1,'issuer letter for half-year ended 31 December 2025'),
 'PPL': ('PPL_270122.pdf','https://dps.psx.com.pk/download/document/270122.pdf',1,'issuer letter for half-year ended 31 December 2025; no annual table in downloaded one-page PDF'),
}
REVIEWED_HASHES = {
 'ENGROH':'ee6edb12f959b3c4c85ba2d3463c114bfde1172a81cbe7700de9a98bf606768c',
 'FFC':'a8962695859abc2e27bb780b0919a533f8e7dc6ae0652818d0735ce94cb41e2e',
 'OGDC':'0c6acef204b667f6859f57b4772e020e690be8e46fbd737020dca64be5f951f9',
 'PPL':'240a0d331f21b67f5c6cc376828ab900653583acc623f104bae64911d89db972',
}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def run():
    wbpath=ROOT.parent/'PSX data v4/03_fundamentals_final.xlsx'
    sheet=openpyxl.load_workbook(wbpath,data_only=True).active
    headers={c.value:c.column for c in sheet[1]}
    facts=[]
    def add(row,field,source_value,scale=1,rounded=False):
        symbol=sheet.cell(row,headers['company_symbol']).value
        cell=sheet.cell(row,headers[field]); raw=Decimal(str(cell.value))
        normalized=raw*Decimal(str(scale)); expected=Decimal(str(source_value))
        if rounded:
            # Narrative million-PKR precision, not exact-thousand verification.
            agrees=(normalized/1000).quantize(Decimal('1'),rounding=ROUND_HALF_UP)==expected
            status='rounded_narrative_match_after_scale_correction' if agrees else 'numeric_mismatch'
            unit='million PKR'; compared=normalized/1000
        else:
            agrees=abs(normalized-expected)<=Decimal('0.000001')
            status=('exact_value_and_unit_match' if scale==1 else 'exact_match_after_scale_correction') if agrees else 'numeric_mismatch'
            unit='PKR per share' if field=='eps' else 'thousand PKR';compared=normalized
        facts.append(dict(company=symbol,year=sheet.cell(row,headers['fiscal_year']).value,
          workbook=str(wbpath.relative_to(ROOT.parent)),worksheet=sheet.title,cell=cell.coordinate,field=field,
          raw_value=str(raw),declared_unit='PKR per share' if field=='eps' else 'thousand PKR',
          status=status,raw_unit_correct=scale==1,normalization_multiplier=scale,
          compared_value=str(compared),source_value=str(expected),source_unit=unit,
          source=symbol,source_period='year ended 31 December 2025 with FY2024 comparison',
          original_preserved=True))
    for row,vals in [(4,(432410443,73564267,'51.69')),(5,(373536920,64731439,'45.49'))]:
        for field,value in zip(('sales_thousand_pkr','profit_after_tax_thousand_pkr','eps'),vals):
            add(row,field,value,1 if field=='eps' else 1000000)
    for row,eps,pat in [(2,'0.21',253),(3,'20.48',9854)]:
        add(row,'eps',eps)
        add(row,'profit_after_tax_thousand_pkr',pat,1000000,rounded=True)
    for row in (6,8):
        symbol=sheet.cell(row,headers['company_symbol']).value
        for field in ('sales_thousand_pkr','profit_after_tax_thousand_pkr','eps'):
            cell=sheet.cell(row,headers[field])
            facts.append(dict(company=symbol,year=2025,workbook=str(wbpath.relative_to(ROOT.parent)),
              worksheet=sheet.title,cell=cell.coordinate,field=field,raw_value=str(cell.value),
              status='registered_source_period_mismatch',source=symbol,
              workbook_period_end=str(sheet.cell(row,headers['period_end_date']).value),
              source_period='half-year ended 31 December 2025',
              explanation='Registered disclosure cannot authenticate the June-2025 annual value. No numeric replacement inferred.',
              original_preserved=True))
    sources=[]
    for company,(filename,url,page,scope) in SOURCES.items():
        p=EVIDENCE/filename
        if not p.exists(): raise FileNotFoundError('Retrieve registered official disclosure before replay: '+str(p))
        if sha(p)!=REVIEWED_HASHES[company]:
            raise ValueError('Source copy changed; visual review required: '+company)
        sources.append(dict(company=company,url=url,retrieved='2026-10-16',file=str(p.relative_to(ROOT)),sha256=sha(p),
           inspected_pdf_page_1_based=page,scope=scope,evidence_method='manual rendered-page inspection or primary PDF text with period heading',
           issuer_original=True,authentication_not_digital_signature=True))
    result=dict(version='bounded-source-authentication-v1',retrieved='2026-10-16',
      workbook_sha256=sha(wbpath),sources=sources,facts=facts,
      status_counts=dict(Counter(x['status'] for x in facts)),
      limits=['Purposive four-issuer PSX audit, not representative cross-market source validation.',
       'ENGROH PAT narrative only confirms rounding to millions, not exact thousand-PKR values.',
       'No first-publication time, historical daily price/volume, FX or sector benchmark authenticated.',
       'IDX/MSX facts remain unauthenticated. Download hashes bind inspected copies, not publisher signatures.',
       'Exact value matches do not establish comparability across restructuring, payout or consolidation scopes.'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    assert result['status_counts']=={'exact_match_after_scale_correction':4,'exact_value_and_unit_match':4,'rounded_narrative_match_after_scale_correction':2,'registered_source_period_mismatch':6}
    print(json.dumps(result['status_counts']))
if __name__=='__main__':run()
