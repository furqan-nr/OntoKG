"""Application configuration, not a new arithmetic engine.

Fixed positive-integer scaling compiles into balanced addition supported by the
unchanged boundary-1 interpreter. No division, approximate percent or string eval.
Raw 18-band aggregation is separately disclosed in the source adapter/oracle.
"""
N = 'https://w3id.org/ontokg-eq/application/nhs-rtt#'


def scaled_role(role, factor):
    if not isinstance(role, str) or not role or type(factor) is not int or not 0 <= factor <= 256:
        raise ValueError('scaling requires a named role and integer factor 0..256')
    if factor == 0:
        return {'constant': '0'}
    if factor == 1:
        return {'role': role}
    half = factor // 2
    return {'add': [scaled_role(role, half), scaled_role(role, factor-half)]}


def build_contract():
    roles = {name: {'metric': name, 'expected_unit': 'pathways',
                    'unit_predicate': N+'unit', 'focus_path': [],
                    'subject_type': N+'Provider', 'window_predicate': N+'inMonth',
                    'window_type': N+'ReportingMonth'}
             for name in ['within18', 'total']}
    return {'version': 'boundary-1', 'entity_type': N+'Provider',
            'bundle_type': N+'EvidenceView', 'observation_type': N+'CountObservation',
            'metric_predicate': N+'metric', 'value_predicate': N+'count',
            'subject_predicate': N+'reportedBy', 'finding_entity_predicate': N+'aboutProvider',
            'support_predicate': N+'usesCount', 'bundle_predicate': N+'deliveredAs',
            'bundle_entity_predicate': N+'forProvider', 'membership_predicate': N+'containsCount',
            'shared_window': True, 'roles': roles,
            'branches': [[{'op': 'gt', 'left': {'role': 'total'}, 'right': {'constant': '0'}},
                          {'op': 'ge', 'left': scaled_role('within18', 100),
                           'right': scaled_role('total', 92)}]]}
