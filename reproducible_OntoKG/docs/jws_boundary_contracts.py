"""Bounded evidence-pool interpreter. Not general SHACL/SPARQL or source authentication.

False is a closed-candidate diagnostic: each OR branch has a complete assignment,
and none passes. Missing/invalid bindings stay unknown. Unit metadata never changes
numeric truth; readiness separately requires a deciding witness with declared units.
"""
import hashlib
import itertools
import json
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from rdflib import RDF, URIRef

OPS = {'gt': lambda a,b:a>b, 'ge':lambda a,b:a>=b, 'lt':lambda a,b:a<b, 'le':lambda a,b:a<=b}

def decimal(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('invalid decimal') from exc
    if not d.is_finite():
        raise ValueError('nonfinite decimal')
    if len(d.as_tuple().digits)>1000 or abs(d.as_tuple().exponent)>10000:
        raise ValueError('decimal representation exceeds bound')
    return d

def expression_roles(expr, depth=0):
    if depth>12: raise ValueError('expression nesting exceeds bound')
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError('expression must have exactly one operator')
    op, arg = next(iter(expr.items()))
    if op == 'role' and isinstance(arg, str):
        return {arg}
    if op == 'constant':
        decimal(arg)
        return set()
    if op == 'abs':
        return expression_roles(arg,depth+1)
    if op == 'add' and isinstance(arg, list) and len(arg) == 2:
        return expression_roles(arg[0],depth+1) | expression_roles(arg[1],depth+1)
    raise ValueError('unsupported expression')

def validate_contract(c):
    if not isinstance(c,dict) or c.get('version') != 'boundary-1':
        raise ValueError('unsupported contract version')
    required=['observation_type','metric_predicate','value_predicate','subject_predicate',
                  'finding_entity_predicate','support_predicate','bundle_predicate',
                  'bundle_entity_predicate','membership_predicate']
    if set(c)-set(required)-{'version','roles','branches','shared_window','entity_type','bundle_type'}:
        raise ValueError('unsupported contract field')
    if not isinstance(c.get('shared_window',True),bool):raise ValueError('shared_window must be boolean')
    for field in required+[k for k in ['entity_type','bundle_type'] if k in c]:
        if not isinstance(c.get(field),str) or not c[field].startswith(('http://','https://','urn:')):
            raise ValueError('missing/invalid IRI: '+field)
    if not isinstance(c.get('roles'),dict) or not 1 <= len(c['roles']) <= 12:
        raise ValueError('roles must be bounded nonempty mapping')
    if not isinstance(c.get('branches'),list) or not 1 <= len(c['branches']) <= 12:
        raise ValueError('branches must be bounded nonempty list')
    for role,spec in c['roles'].items():
        if not isinstance(spec,dict) or 'metric' not in spec:
            raise ValueError('invalid role '+role)
        if set(spec)-{'metric','expected_unit','unit_predicate','focus_path','window_predicate','window_type','subject_type'}:
            raise ValueError('unsupported role field')
        if not isinstance(spec['metric'],str) or not spec['metric']:raise ValueError('metric must be nonempty string')
        if 'expected_unit' in spec and (not isinstance(spec['expected_unit'],str) or not spec['expected_unit']):raise ValueError('invalid expected unit')
        for field in ['unit_predicate','window_predicate','window_type','subject_type']:
            if field in spec and (not isinstance(spec[field],str) or not spec[field].startswith(('http://','https://','urn:'))):raise ValueError('invalid role IRI')
        if 'window_type' in spec and 'window_predicate' not in spec:raise ValueError('window type requires predicate')
        if not isinstance(spec.get('focus_path',[]),list) or len(spec.get('focus_path',[])) > 4:
            raise ValueError('invalid bounded focus path')
        for p in spec.get('focus_path',[]):
            if not isinstance(p,str) or not p.startswith(('http://','https://','urn:')):
                raise ValueError('invalid focus path IRI')
    for branch in c['branches']:
        if not isinstance(branch,list) or not 1 <= len(branch) <= 12:
            raise ValueError('branch must be bounded conjunction')
        roles=set()
        for comparison in branch:
            if not isinstance(comparison,dict) or set(comparison) != {'op','left','right'} or not isinstance(comparison['op'],str) or comparison['op'] not in OPS:
                raise ValueError('unsupported comparison')
            roles |= expression_roles(comparison['left']) | expression_roles(comparison['right'])
        if not roles or not roles <= c['roles'].keys():
            raise ValueError('branch references missing roles')
    return c

def _value(expr, assignment):
    op,arg=next(iter(expr.items()))
    if op=='role': return assignment[arg]['value']
    if op=='constant': return decimal(arg)
    if op=='abs': return _value(arg,assignment).copy_abs()
    left,right=_value(arg[0],assignment),_value(arg[1],assignment)
    # Enough digits for exact finite-decimal addition, independent of ambient context.
    with localcontext() as ctx:
        ctx.prec=max(left.adjusted(),right.adjusted())-min(left.as_tuple().exponent,right.as_tuple().exponent)+3
        return left+right

def _targets(g,entity,spec):
    targets={entity}
    for p in spec.get('focus_path',[]):
        targets={o for s in targets for o in g.objects(s,URIRef(p))}
    if spec.get('subject_type'):
        targets={s for s in targets if (s,RDF.type,URIRef(spec['subject_type'])) in g}
    return targets

def evaluate_pool(g, observations, entity, contract, max_assignments=10000):
    c=validate_contract(contract)
    if type(max_assignments) is not int or not 1<=max_assignments<=1000000:raise ValueError('invalid assignment limit')
    candidates={}; exclusions=[]
    for role,spec in c['roles'].items():
        candidates[role]=[]
        for obs in sorted(observations,key=str):
            if (obs,RDF.type,URIRef(c['observation_type'])) not in g: continue
            metrics=set(map(str,g.objects(obs,URIRef(c['metric_predicate']))))
            if str(spec['metric']) not in metrics: continue
            reason=None
            subjects=set(g.objects(obs,URIRef(c['subject_predicate'])))
            values=list(g.objects(obs,URIRef(c['value_predicate'])))
            windows=set(g.objects(obs,URIRef(spec['window_predicate']))) if spec.get('window_predicate') else {None}
            if metrics != {str(spec['metric'])}: reason='ambiguous_metric'
            elif len(subjects)!=1 or not subjects <= _targets(g,entity,spec): reason='wrong_or_ambiguous_subject'
            elif len(values)!=1: reason='missing_or_ambiguous_value'
            elif len(windows)!=1: reason='missing_or_ambiguous_window'
            elif spec.get('window_type') and (next(iter(windows)),RDF.type,URIRef(spec['window_type'])) not in g: reason='invalid_window_type'
            if reason:
                exclusions.append({'role':role,'observation':str(obs),'reason':reason}); continue
            try: value=decimal(values[0])
            except ValueError:
                exclusions.append({'role':role,'observation':str(obs),'reason':'invalid_numeric_value'}); continue
            units=set(map(str,g.objects(obs,URIRef(spec['unit_predicate'])))) if spec.get('unit_predicate') else set()
            ready=bool(spec.get('expected_unit')) and units=={spec['expected_unit']}
            candidates[role].append({'id':str(obs),'value':value,'window':next(iter(windows)),'ready':ready})
    branches=[]; budget=0
    for conjunction in c['branches']:
        roles=sorted(set().union(*(expression_roles(x['left'])|expression_roles(x['right']) for x in conjunction)))
        count=1
        for role in roles: count*=len(candidates[role])
        budget+=count
        if budget>max_assignments: raise ValueError('candidate assignment budget exceeded')
        complete=[]; passing=[]
        for combination in itertools.product(*(candidates[r] for r in roles)):
            assignment=dict(zip(roles,combination))
            windows={v['window'] for v in combination if v['window'] is not None}
            if c.get('shared_window',True) and len(windows)>1: continue
            complete.append(assignment)
            if all(OPS[x['op']](_value(x['left'],assignment),_value(x['right'],assignment)) for x in conjunction):
                passing.append(assignment)
        status='positive' if passing else 'false' if complete else 'unknown'
        deciding=passing if passing else complete
        branches.append({'status':status,'complete_assignments':len(complete),
                         'witnesses':[{r:v['id'] for r,v in a.items()} for a in passing],
                         'metadata_ready':any(all(v['ready'] for v in a.values()) for a in deciding)})
    status='positive' if any(b['status']=='positive' for b in branches) else 'false' if all(b['status']=='false' for b in branches) else 'unknown'
    readiness=any(b['status']=='positive' and b['metadata_ready'] for b in branches) if status=='positive' else all(b['metadata_ready'] for b in branches) if status=='false' else False
    return {'status':status,'truth':True if status=='positive' else False if status=='false' else None,
            'metadata_ready':readiness,'branches':branches,'exclusions':exclusions,
            'candidate_counts':{r:len(v) for r,v in candidates.items()},'assignment_budget_used':budget}

def audit(g,finding,contract,max_assignments=10000):
    c=validate_contract(contract)
    entities=set(g.objects(finding,URIRef(c['finding_entity_predicate'])))
    if len(entities)!=1: raise ValueError('finding must identify exactly one entity')
    entity=next(iter(entities)); support=set(g.objects(finding,URIRef(c['support_predicate'])))
    if c.get('entity_type') and (entity,RDF.type,URIRef(c['entity_type'])) not in g:raise ValueError('finding entity has wrong type')
    bundles=set(g.objects(finding,URIRef(c['bundle_predicate'])))
    association=len(bundles)==1
    bundle=next(iter(bundles)) if association else None
    association=association and set(g.objects(bundle,URIRef(c['bundle_entity_predicate'])))=={entity}
    if association and c.get('bundle_type'):association=(bundle,RDF.type,URIRef(c['bundle_type'])) in g
    declared=set(g.objects(bundle,URIRef(c['membership_predicate']))) if bundle else set()
    delivered=declared & support if association else set()
    ambient=set(g.subjects(RDF.type,URIRef(c['observation_type'])))
    pools={'ambient':ambient,'support':support,'delivered':delivered}
    return {'finding':str(finding),'entity':str(entity),'bundle_association_valid':association,
            'excluded_bundle_members':sorted(map(str,declared-delivered)),
            'pools':{name:evaluate_pool(g,obs,entity,c,max_assignments) for name,obs in pools.items()},
            'pool_members':{name:sorted(map(str,obs)) for name,obs in pools.items()},
            'contract_sha256':hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest(),
            'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'graph_sha256':hashlib.sha256('\n'.join(sorted(' '.join(n.n3() for n in t) for t in g)).encode()).hexdigest(),
            'hash_scope':'local artifact identity, not signatures or RDF blank-node canonicalization',
            'policy':'finite closed candidate pools; false is not open-world negation; no ambient rescue'}
