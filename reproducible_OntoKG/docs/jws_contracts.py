"""Typed, support-only finding replay. No production rule imports or queries."""
import itertools
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from rdflib import Namespace, RDF, URIRef

C = Namespace('https://w3id.org/ontokg-eq#')
PROV = Namespace('http://www.w3.org/ns/prov#')
AUD = Namespace('https://w3id.org/ontokg-eq/lineage-audit#')
ROOT = Path(__file__).resolve().parents[1]

def load_contracts():
    return json.loads((ROOT / 'contracts/cq_contracts.json').read_text(encoding='utf-8'))

def _candidates(g, observations, entity, spec):
    result = []
    for o in sorted(observations, key=str):
        if (o, RDF.type, C.Observation) not in g:
            continue
        if set(map(str, g.objects(o, C.hasMetricName))) != {spec['metric']}:
            continue
        subjects = set(g.objects(o, C.isObservationOf))
        kind = spec['entity']
        targets = {entity} if kind == 'company' else set(g.objects(entity, C.isClassifiedByIndustrySector)) if kind == 'sector' else set(g.subjects(RDF.type, C.MarketIndex))
        if len(subjects) != 1 or not subjects <= targets:
            continue
        if kind == 'company' and (entity, RDF.type, C.Company) not in g:
            continue
        if kind == 'sector' and not all((s, RDF.type, C.IndustrySectorClassifier) in g for s in subjects):
            continue
        values = list(g.objects(o, C.hasMetricValue))
        windows = set(g.objects(o, C[spec['window']])) if 'window' in spec else {None}
        if len(values) != 1 or len(windows) != 1:
            continue
        if 'window' in spec:
            window_type = C.EventWindow if spec['window'] == 'observedInEventWindow' else C.AnalysisWindow
            if (next(iter(windows)), RDF.type, window_type) not in g:
                continue
        try:
            value = Decimal(str(values[0]))
        except (ValueError, TypeError, InvalidOperation):
            continue
        if value.is_finite():
            result.append((o, value, next(iter(windows))))
    return result

def _replay(g, observations, entity, rid, contract):
    candidates = {role: _candidates(g, observations, entity, spec) for role, spec in contract['roles'].items()}
    roles = list(candidates)
    combinations = list(itertools.product(*(candidates[r] for r in roles)))
    valid = []
    for combo in combinations:
        windows = {item[2] for item in combo if item[2] is not None}
        if len(windows) <= 1:
            valid.append(dict(zip(roles, combo)))
    witnesses = []
    if rid == 'R4':
        # OR witnesses stand independently; a nonpassing/missing other branch is optional.
        for role, threshold in [('event_return', contract.get('return_threshold', 2)), ('volume', contract.get('volume_threshold', 1.5))]:
            for item in candidates[role]:
                if (abs(item[1]) if role == 'event_return' else item[1]) >= Decimal(str(threshold)):
                    witnesses.append({role: str(item[0])})
    else:
        for values in valid:
            v = {r: x[1] for r, x in values.items()}
            passed = (v['growth'] > 0 and v['company'] < v['benchmark']) if rid == 'R1' else abs(v['correlation']) >= Decimal(str(contract.get('threshold', .3))) if rid == 'R2' else v['company'] > v['sector'] + Decimal(str(contract.get('margin', 0))) and v['company'] > v['benchmark'] + Decimal(str(contract.get('margin', 0)))
            if passed:
                witnesses.append({r: str(x[0]) for r, x in values.items()})
    return candidates, bool(valid), witnesses

def evaluate_finding(graph, finding, contract=None, lineage_graph=None):
    rid = str(next(graph.objects(finding, C.derivedByRule), ''))
    spec = contract or load_contracts().get(rid)
    entities = set(graph.objects(finding, C.concernsEntity))
    if rid not in {'R1','R2','R3','R4'} or not spec or len(entities) != 1:
        return {'finding':str(finding), 'rule':rid, 'status':'invalid_finding', 'sufficient_witness':False, 'support_complete':False, 'full_graph_truth':None, 'witnesses':[]}
    entity = next(iter(entities))
    support = set(graph.objects(finding, C.supportedByObservation))
    candidates, complete, witnesses = _replay(graph, support, entity, rid, spec)
    bundle = URIRef(str(finding) + '_bundle')
    bundle_valid = (bundle, RDF.type, C.EvidenceBundle) in graph and set(graph.objects(bundle,C.explainsResultEntity)) == {entity}
    bundle_support = set(graph.objects(bundle,C.includesObservation)) & support if bundle_valid else set()
    _, bundle_complete, bundle_witnesses = _replay(graph,bundle_support,entity,rid,spec)
    all_obs = set(graph.subjects(C.hasMetricName, None))
    _, full_complete, full_witnesses = _replay(graph, all_obs, entity, rid, spec)
    # An event finding must replay within its declared support event window, not another event.
    if rid == 'R4':
        windows = {w for xs in candidates.values() for _, _, w in xs}
        if windows:
            allowed = {o for o in all_obs if set(graph.objects(o,C.observedInEventWindow)) & windows}
            _, full_complete, full_witnesses = _replay(graph, allowed, entity, rid, spec)
    lg = lineage_graph if lineage_graph is not None else graph
    source = {str(o): sorted(map(str, lg.objects(o, PROV.wasDerivedFrom))) for o in sorted(support,key=str)}
    source_paths = {}
    for o in support:
        cells = list(lg.objects(o,PROV.wasDerivedFrom))
        checked = []
        for cell in cells:
            sources = list(lg.objects(cell,PROV.hadPrimarySource))
            identifiers = set(lg.objects(cell,AUD.sourceIdentifier))
            valid = len(sources)==1 and len(identifiers)==1 and set(lg.objects(sources[0],C.hasSourceIdentifier))==identifiers
            checked.append({'cell':str(cell),'sources':list(map(str,sources)),'valid_identity_path':valid})
        source_paths[str(o)] = {'cells':checked,'complete':bool(checked) and all(c['valid_identity_path'] for c in checked)}
    units = {}
    for role, obs in candidates.items():
        for o, _, _ in obs:
            declared = sorted({str(v) for p,v in graph.predicate_objects(o) if str(p).rsplit('#',1)[-1].lower() in {'hasunit','unit','hasmeasurementunit'}})
            units[str(o)] = {'expected':spec['roles'][role]['unit'], 'declared':declared, 'status':'declared_not_normalized' if declared else 'unverified_absent'}
    source_sufficient = any(all(source_paths[o]['complete'] for o in witness.values()) for witness in bundle_witnesses)
    return {'finding':str(finding),'rule':rid,'entity':str(entity),'status':'sufficient' if witnesses else 'predicate_false' if complete else 'incomplete', 'support_complete':complete,'sufficient_witness':bool(witnesses),'finding_support_sufficient':bool(witnesses),'bundle':str(bundle),'bundle_valid':bundle_valid,'bundle_sufficient':bool(bundle_witnesses),'bundle_all_roles_available':bundle_complete,'bundle_status':'sufficient' if bundle_witnesses else 'predicate_false' if bundle_complete else 'incomplete_bundle','bundle_witnesses':bundle_witnesses,'full_graph_truth':True if full_witnesses else False if full_complete else None,'witnesses':witnesses,'role_candidates':{r:[str(x[0]) for x in xs] for r,xs in candidates.items()},'source_linkage':source,'source_paths':source_paths,'source_linkage_complete':bool(support) and all(p['complete'] for p in source_paths.values()),'source_sufficient_witness':source_sufficient,'source_truth_verified':False,'units':units,'temporal_policy':{'shared_deciding_window':'checked_where_required','event_finding_to_window_anchor':'unverified_no_declared_anchor' if rid=='R4' else 'not_applicable','growth_reporting_period_to_return_window_anchor':'unverified' if rid=='R1' else 'not_applicable'},'unit_verification':'unverified' if any(v['status']=='unverified_absent' for v in units.values()) else 'declarations_only'}
