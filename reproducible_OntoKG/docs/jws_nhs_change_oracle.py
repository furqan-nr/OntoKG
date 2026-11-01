"""Exact policy oracle over adapter records; no RDF, contract or query imports."""


def classify(record, threshold, operator):
    if type(threshold) is not int or not 0 <= threshold <= 100 or operator not in ('ge', 'gt'):
        raise ValueError('unsupported policy')
    if not record['csv_present']:
        if record['within18'] is not None or record['total'] is not None:
            raise ValueError('unavailable source cannot carry deciding counts')
        return {'status': 'unknown', 'metadata_ready': False}
    n, t = record['within18'], record['total']
    if type(n) is not int or type(t) is not int or n < 0 or t < 0 or n > t:
        raise ValueError('invalid nonnegative pathway counts')
    passes = t > 0 and (100*n >= threshold*t if operator == 'ge' else 100*n > threshold*t)
    return {'status': 'positive' if passes else 'false', 'metadata_ready': True}


def cohort(records, threshold, operator):
    output = {}
    for record in records:
        code = record['provider_code']
        if code in output:
            raise ValueError('duplicate provider')
        output[code] = classify(record, threshold, operator)
    return output


def changes(before, after):
    if before.keys() != after.keys():
        raise ValueError('population changed')
    return sorted(code for code in before if before[code] != after[code])


def require_equal(actual, expected, label):
    if actual != expected:
        keys = actual.keys() | expected.keys()
        mismatch = sorted(k for k in keys if actual.get(k) != expected.get(k))
        raise AssertionError(label+': mismatched identities/results '+repr(mismatch))
