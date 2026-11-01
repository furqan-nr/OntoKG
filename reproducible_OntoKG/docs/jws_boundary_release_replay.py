"""End-to-end audit of actual stored original/repaired release findings.

Original bytes come from a recorded Git commit and must match the prior audit
ledger. Only explicit interface adapters are added in memory. No original
finding/support/bundle values or memberships are repaired by this experiment.
"""
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from rdflib import Graph, RDF, URIRef
from jws_boundary_contracts import audit

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
C = 'https://w3id.org/ontokg-eq#'
OUT = ROOT / 'evaluation_jws/boundary_release_replay_v1'
ORIGINAL_COMMIT = '5035e0ba7aeee7b9bbecb6311eafb339591a8636'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args], check=True, capture_output=True).stdout


def run():
    commit = ORIGINAL_COMMIT
    git('cat-file', '-e', commit + '^{commit}')
    spec_path = ROOT / 'contracts/finance_boundary_v1.json'
    code_path = Path(__file__).with_name('jws_boundary_contracts.py')
    specs = json.loads(spec_path.read_text(encoding='utf-8'))
    spec_hash, code_hash = sha(spec_path.read_bytes()), sha(code_path.read_bytes())
    ledgers = {name: json.loads((ROOT / f'evaluation_jws/{name}/evidence_audit.json').read_text())
               for name in ['original_release', 'repaired_release']}
    expected_hashes = {name: {row['market']: row['sha256'] for row in ledger['graphs']}
                       for name, ledger in ledgers.items()}
    records = []
    adapters = []
    for market in ['psx', 'msx', 'idx']:
        relative = f'reproducible_OntoKG/data/demo_{market}_inferred.ttl'
        current_path = REPO / relative
        sources = [('original_release', git('show', commit + ':' + relative)),
                   ('repaired_release', current_path.read_bytes())]
        for release, data in sources:
            actual_hash = sha(data)
            if actual_hash != expected_hashes[release][market]:
                raise ValueError(f'{release}/{market} does not match the recorded release bytes; no substitution permitted')
            g = Graph().parse(data=data.decode('utf-8'), format='turtle')
            # Disclose adaptation of old implicit identities to the explicit API.
            # Existing values, supports and actual bundle members stay untouched.
            added = 0
            for company in set(g.subjects(RDF.type, URIRef(C + 'Company'))):
                for index in set(g.subjects(RDF.type, URIRef(C + 'MarketIndex'))):
                    triple = (company, URIRef(C + 'comparedWithIndex'), index)
                    if triple not in g:
                        g.add(triple); added += 1
            for finding in sorted(g.subjects(RDF.type, URIRef(C + 'AnalyticalFinding')), key=str):
                bundle = URIRef(str(finding) + '_bundle')
                if (bundle, RDF.type, URIRef(C + 'EvidenceBundle')) not in g:
                    raise ValueError('Expected actual generated bundle is absent; do not manufacture one')
                triple = (finding, URIRef(C + 'hasEvidenceBundle'), bundle)
                if triple not in g:
                    g.add(triple); added += 1
            adapters.append(dict(release=release, market=market, input_sha256=actual_hash,
                                 added_interface_edges=added))
            for finding in sorted(g.subjects(RDF.type, URIRef(C + 'AnalyticalFinding')), key=str):
                rules = set(map(str, g.objects(finding, URIRef(C + 'derivedByRule'))))
                if len(rules) != 1:
                    raise ValueError('Ambiguous original finding classification')
                rule = next(iter(rules))
                checked = audit(g, finding, specs[rule])
                records.append(dict(release=release, market=market, rule=rule,
                                    input_sha256=actual_hash, **checked))
    assert sha(spec_path.read_bytes()) == spec_hash and sha(code_path.read_bytes()) == code_hash
    summary = {release: dict(findings=sum(r['release'] == release for r in records),
                            ambient_positive=sum(r['release'] == release and r['pools']['ambient']['status'] == 'positive' for r in records),
                            support_positive=sum(r['release'] == release and r['pools']['support']['status'] == 'positive' for r in records),
                            delivered_positive=sum(r['release'] == release and r['pools']['delivered']['status'] == 'positive' for r in records))
               for release in ['original_release', 'repaired_release']}
    pairs = {}
    for row in records:
        pairs.setdefault(row['finding'], {})[row['release']] = row
    transitions = []
    for finding, pair in pairs.items():
        if set(pair) != {'original_release', 'repaired_release'}:
            raise ValueError('Release finding sets differ; cannot silently pair')
        before, after = pair['original_release'], pair['repaired_release']
        old = [before['pools'][p]['status'] for p in ['ambient', 'support', 'delivered']]
        new = [after['pools'][p]['status'] for p in ['ambient', 'support', 'delivered']]
        if old != new:
            transitions.append(dict(finding=finding, rule=before['rule'], before=old, after=new))
    report = dict(scope='Paired actual stored release audit, not constructed corruption or independent new participants/companies.',
                  git_commit_for_original=commit, python=platform.python_version(), checker_sha256=code_hash,
                  config_sha256=spec_hash, interface_adapters=adapters, summary=summary,
                  transitions=transitions, records=records,
                  limits=['Original bytes must match the frozen original-release audit ledger.',
                          'Added explicit finding-to-existing-bundle and company-to-index interface links only; no source evidence or support memberships are synthesized.',
                          'This uses the end-to-end audit entry point after disclosed interface adaptation, not a raw unadapted production replacement.',
                          'Ambient R4 is not independently event-anchored; original findings lack sufficient explicit event identity. No event-specific ambient-truth guarantee is claimed.',
                          'Structural source linkage and numerical replay do not authenticate financial inputs or establish external-domain validity.'])
    expected_changed = {issue['finding'] for issue in ledgers['original_release']['dependency_issues']['psx']
                        if issue['code'] == 'volume_trigger_not_in_explicit_support'}
    assert {row['finding'] for row in transitions} == expected_changed, 'Release transitions differ from the prior independent defect ledger'
    assert summary['original_release']['findings'] == summary['repaired_release']['findings'] == 21
    assert summary['original_release']['support_positive'] == summary['original_release']['delivered_positive'] == 19
    assert summary['repaired_release']['support_positive'] == summary['repaired_release']['delivered_positive'] == 21
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(summary=summary, transitions=transitions), indent=2))
    return report


if __name__ == '__main__':
    run()
