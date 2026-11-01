"""Independent CSV/XLSX source reconciliation; no RDF or checker imports.

Publisher percentages are reconciled to 1e-12 in ratio units, fixed before
reconciliation: this covers binary Excel floating storage, not count differences.
Displayed one-decimal percent values use Decimal ROUND_HALF_UP. Exact integer
cross-products alone determine the 92% screen.
"""
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
import openpyxl

BASE = Path(__file__).resolve().parents[1] / 'external_applications' / 'nhs_rtt_v1'
WEEK_COLUMNS = [f'Gt {i:02d} To {i+1:02d} Weeks SUM 1' for i in range(18)]
TOLERANCE = Decimal('0.000000000001')


def integer(value):
    if isinstance(value, bool) or value is None or str(value).strip() == '':
        raise ValueError(f'unavailable count: {value!r}')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or result != result.to_integral_value():
        raise ValueError(f'invalid count: {value!r}')
    return int(result)


def classify(within18, total):
    if total == 0:
        return 'not_applicable'
    return 'at_least_92_percent' if 100 * within18 >= 92 * total else 'below_92_percent'


def fingerprint(path):
    return {'filename': path.name, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    archive = next((BASE / 'source').glob('*.zip'))
    workbook = next((BASE / 'source').glob('*.xlsx'))
    groups = defaultdict(list)
    excluded = 0
    all_rows = 0
    with zipfile.ZipFile(archive) as z:
        members = z.namelist()
        assert len(members) == 1 and members[0].endswith('.csv'), members
        with z.open(members[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig'))
            header = reader.fieldnames
            for field in WEEK_COLUMNS + ['Total All']:
                assert field in header, field
            keys = set()
            for line, row in enumerate(reader, 2):
                all_rows += 1
                if row['RTT Part Type'] != 'Part_2' or row['Treatment Function Name'] != 'Total':
                    continue
                assert row['Treatment Function Code'] == 'C_999'
                assert row['Period'] == 'RTT-August-2026'
                if row['Commissioner Org Code'] == 'NONC':
                    excluded += 1
                    continue
                key = (row['Period'], row['Provider Org Code'], row['Commissioner Org Code'])
                assert key not in keys, ('duplicate commissioner/provider key', key)
                keys.add(key)
                groups[row['Provider Org Code']].append((line, row))
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    published = {}
    for sheet in ['Provider', 'IS Provider']:
        ws = wb[sheet]
        assert ws['C5'].value == 'August 2026'
        h = list(next(ws.iter_rows(min_row=14, max_row=14, values_only=True)))
        assert h[111:114] == ['Total number of incomplete pathways', 'Total within 18 weeks', '% within 18 weeks']
        for rownum, cells in enumerate(ws.iter_rows(min_row=15), 15):
            row = tuple(cell.value for cell in cells)
            if row[5] != 'Total':
                continue
            code = row[2]
            if not code or code == 'ENGLAND':
                continue
            assert row[4] == 'C_999'
            assert code not in published, ('duplicate workbook provider', code)
            published[code] = {'sheet': sheet, 'row': rownum, 'total': row[111],
                               'within18': row[112], 'ratio': row[113],
                               'weekly': list(row[6:24]),
                               'percentage_format': cells[113].number_format}
    wb.close()
    records = []
    mismatches = []
    for code, rows in sorted(groups.items()):
        errors = []
        try:
            for _, raw_row in rows:
                if sum(integer(raw_row[c]) for c in WEEK_COLUMNS) > integer(raw_row['Total All']):
                    raise ValueError('source-row within18 exceeds Total All')
            weekly = [sum(integer(r[c]) for _, r in rows) for c in WEEK_COLUMNS]
            total = sum(integer(r['Total All']) for _, r in rows)
            within = sum(weekly)
            if within > total:
                raise ValueError('within18 exceeds Total All')
        except ValueError as exc:
            errors.append(str(exc))
            weekly, within, total = None, None, None
        pub = published.get(code)
        comparisons = {}
        if pub and not errors:
            for label, actual, expected in [('total', total, pub['total']), ('within18', within, pub['within18'])]:
                comparisons[label] = actual == expected
            comparisons['all_18_weekly_cells'] = weekly == pub['weekly']
            if total:
                exact_ratio = Decimal(within) / Decimal(total)
                try:
                    delta = abs(exact_ratio - Decimal(str(pub['ratio'])))
                    comparisons['stored_percentage'] = delta <= TOLERANCE
                    comparisons['stored_percentage_absolute_delta'] = str(delta)
                except Exception:
                    comparisons['stored_percentage'] = False
                display = str((exact_ratio * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + '%'
            else:
                display = None
                comparisons['stored_percentage'] = pub['ratio'] in (None, 0, '-', 'N/A')
            for label in ['total', 'within18', 'all_18_weekly_cells', 'stored_percentage']:
                if not comparisons[label]:
                    mismatches.append({'provider': code, 'field': label})
        else:
            display = None
        records.append({'provider_code': code, 'provider_name': rows[0][1]['Provider Org Name'],
                        'period': '2026-08', 'within18': within, 'total': total,
                        'weekly_counts': weekly, 'classification': 'unavailable' if errors else classify(within, total),
                        'ratio_fraction': None if not total else f'{within}/{total}',
                        'display_percentage': display, 'input_errors': errors,
                        'csv_lineage': {'member': members[0], 'line_numbers': [n for n, _ in rows],
                                        'commissioner_codes': [r['Commissioner Org Code'] for _, r in rows],
                                        'within18_columns': WEEK_COLUMNS, 'total_column': 'Total All',
                                        'weekly_column_numbers_1based': [header.index(c) + 1 for c in WEEK_COLUMNS],
                                        'total_column_number_1based': header.index('Total All') + 1},
                        'workbook': pub,
                        'workbook_cells': None if not pub else {'total': f"DH{pub['row']}", 'within18': f"DI{pub['row']}",
                                                              'percentage': f"DJ{pub['row']}", 'weekly': f"G{pub['row']}:X{pub['row']}"},
                        'publisher_comparison': comparisons})
    urls = [line.split(': ', 1)[1] for line in (BASE / 'PROTOCOL.md').read_text(encoding='utf-8').splitlines()
            if line.startswith('- Original')]
    result = {'protocol_sha256': fingerprint(BASE / 'PROTOCOL.md')['sha256'],
              'sources': [dict(fingerprint(p), url=u) for p, u in zip([archive, workbook], urls)],
              'archive_members': members, 'encoding': 'utf-8-sig', 'csv_header': header,
              'workbook_only_records': [dict(provider_code=code, workbook=published[code],
                                            status='no_selected_csv_record; publisher_zero_denominator' if published[code]['total'] == 0 else 'no_selected_csv_record',
                                            csv_counts=None)
                                        for code in sorted(set(published) - set(groups))],
              'percentage_tolerance_ratio_units': str(TOLERANCE),
              'scope': 'Part_2; Treatment Function Name Total/C_999; commissioner NONC excluded; all providers',
              'summary': {'all_csv_records': all_rows, 'selected_csv_records': sum(map(len, groups.values())),
                          'excluded_NONC_records': excluded, 'providers': len(records),
                          'workbook_providers': len(published),
                          'csv_only_providers': sorted(set(groups) - set(published)),
                          'workbook_only_providers': sorted(set(published) - set(groups)),
                          'classifications': dict(Counter(r['classification'] for r in records)),
                          'reconciliation_mismatches': mismatches},
              'limitations': ['Publisher workbook and CSV derive from the same reporting collection; not independent observations.',
                              'No population-completeness inference from absent providers; no external roster used.',
                              'No missing-provider or estimate flags are inferred from absence.',
                              'A newly generated application screen, not clinical advice or a hospital-quality ranking.'],
              'records': records}
    (BASE / 'source_oracle.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))
    audit = ('# Independent source audit\n\nRecorded 18 October 2026. No RDF/checker imports are used.\n\n'
             'The frozen protocol maps `Total` to the actual Treatment Function Name, code `C_999`. '
             'The all-specialty workbook rows reside in both `Provider` and `IS Provider`, not a Total-named sheet. '
             'The same-provider/month/commissioner key is unique across selected CSV rows; no provider aggregate '
             'commissioner row is added to underlying commissioner totals. NONC rows are excluded.\n\n'
             'Reconciliation tolerance was fixed in source code before comparison at 1e-12 ratio units for stored '
             'Excel floating percentages. Count and weekly-cell comparison requires exact equality. Display is '
             'one decimal percent; threshold classification always uses exact integer cross-products, never rounded display.\n\n'
             '```json\n' + json.dumps(result['summary'], indent=2) + '\n```\n\n'
             'All raw CSV row IDs, commissioner codes, weekly columns, workbook sheet/row/cell references, '
             'file sizes, SHA-256 hashes, archive members and original URLs are retained in `source_oracle.json`. '
             'Original binaries were not modified. Missing/invalid counts remain unavailable; zero denominators '
             'remain not applicable, rather than failures or success.\n\n'
             'The workbook-only provider D1V5N (ACES BOLTON), `IS Provider` row 6758, has '
             'DH6758=0, DI6758=0 and DJ6758=0; no Part_2/Total row exists for it in the CSV. '
             'It remains a separate undefined publisher-only record, not a zero-filled CSV observation '
             'or an inferred missing submission.\n\n'
             'The workbook is a publisher-derived cross-format check of the same reporting collection, not '
             'an independently collected ground truth. No patient-level information, practitioner validation, '
             'deployment benefit, natural explanation defects or causal benefit is established.\n')
    (BASE / 'SOURCE_AUDIT.md').write_text(audit, encoding='utf-8')


if __name__ == '__main__':
    main()
