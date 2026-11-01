"""Independently parameterized batch SPARQL and actual SHACL controls.

Imports neither contract configuration nor interpreter nor its pool selection.
Batch queries on the unchanged cohort are explicitly not SHACL validations.
"""
from decimal import localcontext
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.plugins.sparql import prepareQuery

N = Namespace('https://w3id.org/ontokg-eq/application/nhs-rtt#')
SH = Namespace('http://www.w3.org/ns/shacl#')
PREFIX = 'PREFIX n: <'+str(N)+'> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> '
PAIR = '''
?provider a n:Provider . ?month a n:ReportingMonth .
?a a n:CountObservation; n:metric "within18"; n:count ?n; n:reportedBy ?provider; n:inMonth ?month .
?b a n:CountObservation; n:metric "total"; n:count ?t; n:reportedBy ?provider; n:inMonth ?month .
FILTER(datatype(?n)=xsd:integer && datatype(?t)=xsd:integer)
FILTER NOT EXISTS {?a n:metric ?x FILTER(?x != "within18")}
FILTER NOT EXISTS {?b n:metric ?x FILTER(?x != "total")}
FILTER NOT EXISTS {?a n:count ?x FILTER(!sameTerm(?x,?n))}
FILTER NOT EXISTS {?b n:count ?x FILTER(!sameTerm(?x,?t))}
FILTER NOT EXISTS {?a n:reportedBy ?x FILTER(!sameTerm(?x,?provider))}
FILTER NOT EXISTS {?b n:reportedBy ?x FILTER(!sameTerm(?x,?provider))}
FILTER NOT EXISTS {?a n:inMonth ?x FILTER(!sameTerm(?x,?month))}
FILTER NOT EXISTS {?b n:inMonth ?x FILTER(!sameTerm(?x,?month))}
'''
UNITS = '''?a n:unit "pathways" . ?b n:unit "pathways" .
FILTER NOT EXISTS {?a n:unit ?x FILTER(?x != "pathways")}
FILTER NOT EXISTS {?b n:unit ?x FILTER(?x != "pathways")}'''


def condition(threshold, operator):
    if type(threshold) is not int or not 0 <= threshold <= 100 or operator not in ('ge','gt'):
        raise ValueError('unsupported policy')
    return 'FILTER(?t > 0 && 100 * ?n '+('>=' if operator=='ge' else '>')+' '+str(threshold)+' * ?t) '


def queries(threshold, operator):
    passed = condition(threshold, operator)
    return {name: PREFIX+'SELECT DISTINCT ?provider WHERE {'+PAIR+extra+'}'
            for name,extra in [('available',''),('positive',passed),
                               ('qualified_available',UNITS),('qualified_positive',passed+UNITS)]}


def batch(g, providers, threshold, operator):
    texts = queries(threshold,operator)
    lengths=[len(str(v).lstrip('+-')) for v in g.objects(None,N['count'])]
    with localcontext() as ctx:
        ctx.prec=max([28]+[length+6 for length in lengths])
        prepared={key:prepareQuery(query) for key,query in texts.items()}
        sets={key:set() for key in texts}
        # Bind the already declared target before joins. Same query text and
        # semantics; no decision is computed from Python count arithmetic.
        for provider in providers.values():
            for key,query in prepared.items():
                if list(g.query(query,initBindings={'provider':provider})):
                    sets[key].add(provider)
    output={}
    for code,provider in providers.items():
        positive=provider in sets['positive']; available=provider in sets['available']
        output[code]={'status':'positive' if positive else 'false' if available else 'unknown',
                      'metadata_ready':provider in sets['qualified_positive' if positive else 'qualified_available'] if available else False}
    return output,texts


def selected_pools(g, finding):
    providers=set(g.objects(finding,N.aboutProvider))
    if len(providers)!=1: raise ValueError('one provider required')
    provider=next(iter(providers)); support=set(g.objects(finding,N.usesCount))
    bundles=set(g.objects(finding,N.deliveredAs)); bundle=next(iter(bundles)) if len(bundles)==1 else None
    valid=(bundle is not None and (bundle,RDF.type,N.EvidenceView) in g and set(g.objects(bundle,N.forProvider))=={provider})
    delivered=set(g.objects(bundle,N.containsCount)) & support if valid else set()
    membership={'ambient':set(g.subjects(RDF.type,N.CountObservation)),'support':support,'delivered':delivered}
    pools={}
    for name,members in membership.items():
        selected=Graph()
        for typ in (N.Provider,N.ReportingMonth):
            for triple in g.triples((None,RDF.type,typ)): selected.add(triple)
        for observation in members:
            for triple in g.triples((observation,None,None)): selected.add(triple)
        pools[name]=selected
    return provider,pools


def shacl_control(g, finding, threshold, operator):
    from pyshacl import validate
    provider,pools=selected_pools(g,finding); outcomes={}; validations=0
    constraint=PREFIX+'SELECT $this WHERE { FILTER NOT EXISTS {'+PAIR.replace('?provider','$this')+condition(threshold,operator)+'} }'
    for name,pool in pools.items():
        shape=Graph()
        for triple in [(N.Shape,RDF.type,SH.NodeShape),(N.Shape,SH.targetNode,provider),
                       (N.Shape,SH.sparql,N.Constraint),(N.Constraint,SH.select,Literal(constraint))]: shape.add(triple)
        passes,_,_=validate(pool,shacl_graph=shape,advanced=True); validations+=1
        result,_=batch(pool,{'control':provider},threshold,operator)
        assert passes == (result['control']['status']=='positive')
        outcomes[name]=result['control']
    return outcomes,validations
