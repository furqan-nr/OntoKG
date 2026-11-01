"""Independent NHS RTT SHACL-SPARQL constraint and availability baseline.

No boundary-interpreter or configuration imports. Main evaluation executes the
hand-written SHACL SELECT constraint through pySHACL, plus explicit availability
and unit-readiness ASK diagnostics through RDFLib.
Positive-screen conformance is executed by pySHACL. Integer arithmetic is exact;
this baseline is scoped to this integer-count task.
"""
import hashlib
from decimal import localcontext
from rdflib import Graph, Namespace, RDF, Literal, URIRef

N = Namespace('https://w3id.org/ontokg-eq/application/nhs-rtt#')
SH = Namespace('http://www.w3.org/ns/shacl#')
PREFIX = 'PREFIX n: <'+str(N)+'>\nPREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n'

# Requiring exactly one metric/value/subject/window is intentional. Alternative
# observations remain alternative witnesses, not competing values on one node.
PAIR = '''
  ?a a n:CountObservation; n:metric "within18"; n:count ?numerator;
     n:reportedBy $this; n:inMonth ?month .
  ?b a n:CountObservation; n:metric "total"; n:count ?denominator;
     n:reportedBy $this; n:inMonth ?month .
  $this a n:Provider . ?month a n:ReportingMonth .
  FILTER(datatype(?numerator) = xsd:integer && datatype(?denominator) = xsd:integer)
  FILTER NOT EXISTS { ?a n:metric ?v . FILTER(?v != "within18") }
  FILTER NOT EXISTS { ?b n:metric ?v . FILTER(?v != "total") }
  FILTER NOT EXISTS { ?a n:count ?v . FILTER(!sameTerm(?v, ?numerator)) }
  FILTER NOT EXISTS { ?b n:count ?v . FILTER(!sameTerm(?v, ?denominator)) }
  FILTER NOT EXISTS { ?a n:reportedBy ?v . FILTER(!sameTerm(?v, $this)) }
  FILTER NOT EXISTS { ?b n:reportedBy ?v . FILTER(!sameTerm(?v, $this)) }
  FILTER NOT EXISTS { ?a n:inMonth ?v . FILTER(!sameTerm(?v, ?month)) }
  FILTER NOT EXISTS { ?b n:inMonth ?v . FILTER(!sameTerm(?v, ?month)) }
'''
PASS = 'FILTER(?denominator > 0 && 100 * ?numerator >= 92 * ?denominator)\n'
UNITS = '''
  ?a n:unit "pathways" . ?b n:unit "pathways" .
  FILTER NOT EXISTS { ?a n:unit ?v . FILTER(?v != "pathways") }
  FILTER NOT EXISTS { ?b n:unit ?v . FILTER(?v != "pathways") }
'''
POSITIVE_CONSTRAINT = PREFIX+'SELECT $this WHERE { FILTER NOT EXISTS { '+PAIR+PASS+' } }'
AVAILABILITY = PREFIX+'ASK { '+PAIR+' }'
QUALIFIED_POSITIVE = PREFIX+'ASK { '+PAIR+PASS+UNITS+' }'
QUALIFIED_AVAILABLE = PREFIX+'ASK { '+PAIR+UNITS+' }'
QUERY_TEXTS = {'positive_constraint':POSITIVE_CONSTRAINT, 'availability':AVAILABILITY,
               'qualified_positive':QUALIFIED_POSITIVE,'qualified_available':QUALIFIED_AVAILABLE}


def shape_graph(entity):
    """A positive-screen constraint; missing and false both violate this shape.

    Availability must still be evaluated separately to distinguish those cases.
    """
    shapes = Graph()
    shape, constraint = N.ScreenShape, N.ScreenConstraint
    shapes.add((shape,RDF.type,SH.NodeShape))
    shapes.add((shape,SH.targetNode,entity))
    shapes.add((shape,SH.sparql,constraint))
    shapes.add((constraint,SH.select,Literal(POSITIVE_CONSTRAINT)))
    shapes.add((constraint,SH.message,Literal('No complete passing RTT count witness')))
    return shapes


def _pool_graph(g, members):
    # Keep entity/month typing; copy observation properties ONLY for this pool.
    # This prevents an ambient observation from rescuing a support/view query.
    selected=Graph()
    for triple in g.triples((None,RDF.type,N.Provider)):
        selected.add(triple)
    for triple in g.triples((None,RDF.type,N.ReportingMonth)):
        selected.add(triple)
    for observation in members:
        for triple in g.triples((observation,None,None)):
            selected.add(triple)
    return selected


def audit_baseline(g, finding):
    # RDFLib 7.6 evaluates SPARQL multiplication through Decimal even for integer
    # terms. Bound precision from this record's actual integer lexical lengths;
    # this avoids its default 28-digit rounding without changing the query.
    integer_lengths=[len(str(v).lstrip('+-')) for v in g.objects(None,N['count'])
                     if getattr(v,'datatype',None)==URIRef('http://www.w3.org/2001/XMLSchema#integer')]
    with localcontext() as context:
        context.prec=max([28]+[length+6 for length in integer_lengths])
        return _audit_baseline(g,finding)


def _audit_baseline(g, finding):
    from pyshacl import validate
    entities=set(g.objects(finding,N.aboutProvider))
    if len(entities)!=1:
        raise ValueError('baseline finding requires exactly one provider')
    entity=next(iter(entities))
    if (entity,RDF.type,N.Provider) not in g:
        raise ValueError('baseline provider is not typed Provider')
    support=set(g.objects(finding,N.usesCount))
    bundles=set(g.objects(finding,N.deliveredAs))
    bundle=next(iter(bundles)) if len(bundles)==1 else None
    association=(bundle is not None and (bundle,RDF.type,N.EvidenceView) in g
                 and set(g.objects(bundle,N.forProvider))=={entity})
    delivered=(set(g.objects(bundle,N.containsCount)) & support) if association else set()
    members={'ambient':set(g.subjects(RDF.type,N.CountObservation)),
             'support':support,'delivered':delivered}
    outcomes={}; cache={}; validations=0
    for name, observations in members.items():
        key=frozenset(observations)
        if key in cache:
            outcomes[name]=dict(cache[key])
            continue
        pool=_pool_graph(g,observations)
        bindings={'this':entity}
        passes,_,_=validate(pool,shacl_graph=shape_graph(entity),advanced=True)
        validations+=1
        available=bool(pool.query(AVAILABILITY,initBindings=bindings).askAnswer)
        status='positive' if passes else 'false' if available else 'unknown'
        ready_query=QUALIFIED_POSITIVE if passes else QUALIFIED_AVAILABLE
        ready=(status!='unknown' and bool(pool.query(ready_query,initBindings=bindings).askAnswer))
        outcomes[name]={'status':status,'metadata_ready':ready}
        cache[key]=outcomes[name]
    return {'bundle_association_valid':bool(association),'pools':outcomes,
            'pool_members':{k:sorted(map(str,v)) for k,v in members.items()},
            'query_texts_or_hashes':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in QUERY_TEXTS.items()},
            'shacl_validations':validations,
            'execution':'pySHACL positive constraint validation plus explicit RDFLib availability/unit ASK diagnostics; identical membership pools cached within finding'}
