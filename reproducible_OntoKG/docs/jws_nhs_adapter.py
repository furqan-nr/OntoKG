"""Independent source-to-application adapter; no RDF/checker/oracle imports.

Run with bundled Python for read-only CSV/XLSX extraction. Workbook values are
retained as publisher context, never substituted for absent CSV operands.
"""
import csv
from collections import defaultdict
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import zipfile
import openpyxl

BASE = Path(__file__).resolve().parents[1] / 'external_applications/nhs_rtt_v1'
FIELDS = tuple('Gt %02d To %02d Weeks SUM 1' % (n,n+1) for n in range(18))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count(raw):
    if raw is None or not str(raw).strip():
        raise ValueError('absent source count')
    value = Fraction(str(raw))
    if value < 0 or value.denominator != 1:
        raise ValueError('source count is not a nonnegative integer')
    return value.numerator


def run():
    manifest = json.loads((BASE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        path = BASE/source['file']
        assert path.stat().st_size == source['bytes'] and digest(path) == source['sha256'], 'source manifest mismatch'
    archive = BASE/manifest['sources'][0]['file']
    book = BASE/manifest['sources'][1]['file']
    frame = defaultdict(lambda: {'rows': [], 'commissioners': [], 'weekly': [0]*18, 'total': 0, 'errors': []})
    seen = set(); raw_rows = excluded = 0
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        assert len(infos) == 1 and infos[0].filename.endswith('.csv') and infos[0].file_size < 512*1024*1024
        member = infos[0].filename
        with z.open(member) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig'))
            header = reader.fieldnames
            assert len(set(header)) == len(header) and set(FIELDS + ('Total All',)) <= set(header)
            for record_number, row in enumerate(reader, 2):
                raw_rows += 1
                if row['RTT Part Type'] != 'Part_2' or row['Treatment Function Name'] != 'Total':
                    continue
                assert row['Treatment Function Code'] == 'C_999' and row['Period'] == 'RTT-August-2026'
                if row['Commissioner Org Code'] == 'NONC':
                    excluded += 1
                    continue
                code, commissioner = row['Provider Org Code'], row['Commissioner Org Code']
                key = (code, commissioner, row['Period'])
                assert key not in seen, 'duplicate provider/commissioner/month key'
                seen.add(key)
                target = frame[code]
                target['name'] = row['Provider Org Name']
                target['rows'].append(record_number); target['commissioners'].append(commissioner)
                try:
                    values = [count(row[field]) for field in FIELDS]
                    total = count(row['Total All'])
                    assert sum(values) <= total, 'within18 exceeds denominator in a source row'
                    target['weekly'] = [a+b for a,b in zip(target['weekly'],values)]
                    target['total'] += total
                except (ValueError, AssertionError, ZeroDivisionError) as exc:
                    target['errors'].append({'record': record_number, 'reason': str(exc)})
    # Read only the actual all-specialty roster and publisher context. This
    # independently discovers workbook-only entries without an external roster.
    publisher = {}
    wb = openpyxl.load_workbook(book, read_only=True, data_only=True)
    for sheet_name in ['Provider', 'IS Provider']:
        ws = wb[sheet_name]
        assert ws['C5'].value == 'August 2026'
        for row_number, row in enumerate(ws.iter_rows(min_row=15, values_only=True), 15):
            if len(row) < 114 or row[4] != 'C_999' or row[5] != 'Total' or not row[2] or row[2] == 'ENGLAND':
                continue
            code = str(row[2])
            assert code not in publisher, 'duplicate publisher provider code'
            publisher[code] = {'name': row[3], 'sheet': sheet_name, 'row': row_number,
                               'total': row[111], 'within18': row[112], 'ratio': row[113]}
    wb.close()
    records = []
    for code in sorted(set(frame) | set(publisher)):
        raw = frame.get(code); published = publisher.get(code)
        unavailable = raw is None or bool(raw['errors'])
        within = None if unavailable else sum(raw['weekly'])
        total = None if unavailable else raw['total']
        status = ('unavailable_source' if unavailable else 'not_applicable_zero_denominator' if total == 0
                  else 'at_least_92_percent' if 100*within >= 92*total else 'below_92_percent')
        records.append({'provider_code': code, 'provider_name': raw['name'] if raw else published['name'],
                        'period': '2026-08', 'within18': within, 'total': total,
                        'classification': status, 'csv_present': raw is not None,
                        'errors': [] if raw is None else raw['errors'],
                        'weekly_counts': None if unavailable else raw['weekly'],
                        'lineage': {'archive_sha256': manifest['sources'][0]['sha256'], 'member': member,
                                    'record_numbers_including_header': [] if raw is None else raw['rows'],
                                    'commissioner_codes': [] if raw is None else raw['commissioners'],
                                    'within18_columns': list(FIELDS), 'total_column': 'Total All',
                                    'column_numbers_1based': {field: header.index(field)+1 for field in FIELDS+('Total All',)}},
                        'publisher_context': published})
    result = {'adapter_sha256': digest(Path(__file__)), 'protocol_sha256': digest(BASE/'PROTOCOL.md'),
              'manifest_sha256': digest(BASE/'SOURCE_MANIFEST.json'),
              'source_sha256': {p['file']: digest(BASE/p['file']) for p in manifest['sources']},
              'record_number_convention': 'CSV logical record positions including the header as record 1, not byte offsets.',
              'population': 'Union of actual selected CSV provider codes and actual workbook all-specialty provider codes.',
              'summary': {'all_csv_rows': raw_rows, 'selected_csv_rows': len(seen), 'excluded_NONC_rows': excluded,
                          'csv_providers': len(frame), 'publisher_roster_providers': len(publisher),
                          'application_frames': len(records),
                          'source_cells_referenced': len(seen)*19}, 'records': records}
    # This file is an application input independently reconstructed from source,
    # not copied from the separate source_oracle.json or its classifications.
    (BASE/'adapter_records.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))
    return result


if __name__ == '__main__':run()
