#!/usr/bin/env python3
"""Fair relational reuse control over the same released graph-stored metrics.

Run: python docs/jws_relational_reuse.py. This is not independent source-data
reconstruction or a comparison of modeling costs. Writes evaluation_jws only.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

import rdflib
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
C = Namespace("https://w3id.org/ontokg-eq#")
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE entity(id TEXT PRIMARY KEY);
CREATE TABLE entity_type(entity TEXT REFERENCES entity(id), type TEXT NOT NULL,
 PRIMARY KEY(entity,type));
CREATE TABLE sector(company TEXT REFERENCES entity(id), sector TEXT REFERENCES entity(id),
 PRIMARY KEY(company,sector));
CREATE TABLE context(id TEXT PRIMARY KEY);
CREATE TABLE context_property(context TEXT REFERENCES context(id), predicate TEXT NOT NULL,
 value TEXT NOT NULL, PRIMARY KEY(context,predicate,value));
CREATE TABLE observation(id TEXT PRIMARY KEY, subject TEXT NOT NULL REFERENCES entity(id),
 metric TEXT NOT NULL, value REAL NOT NULL CHECK(typeof(value) IN ('real','integer')),
 window TEXT REFERENCES context(id), period TEXT REFERENCES context(id));
CREATE TABLE source(id TEXT PRIMARY KEY);
CREATE TABLE source_property(source TEXT REFERENCES source(id), predicate TEXT NOT NULL,
 value TEXT NOT NULL, PRIMARY KEY(source,predicate,value));
CREATE TABLE evidence(id TEXT PRIMARY KEY);
CREATE TABLE evidence_source(evidence TEXT REFERENCES evidence(id), source TEXT REFERENCES source(id),
 PRIMARY KEY(evidence,source));
CREATE TABLE finding(id TEXT PRIMARY KEY, entity TEXT NOT NULL REFERENCES entity(id),
 cq TEXT NOT NULL, rule TEXT NOT NULL);
CREATE TABLE finding_observation(finding TEXT REFERENCES finding(id),
 observation TEXT REFERENCES observation(id), PRIMARY KEY(finding,observation));
CREATE TABLE bundle(id TEXT PRIMARY KEY, entity TEXT REFERENCES entity(id));
CREATE TABLE bundle_observation(bundle TEXT REFERENCES bundle(id),
 observation TEXT REFERENCES observation(id), PRIMARY KEY(bundle,observation));
CREATE TABLE bundle_evidence(bundle TEXT REFERENCES bundle(id), evidence TEXT REFERENCES evidence(id),
 PRIMARY KEY(bundle,evidence));
"""
SQL = {
    "CQ1": """SELECT DISTINCT cr.subject, fg.value, cr.value, br.value
FROM observation cr JOIN entity_type co ON co.entity=cr.subject AND co.type='Company'
JOIN observation fg ON fg.subject=cr.subject AND fg.metric='YoY profit growth %'
JOIN observation br ON br.window=cr.window AND br.metric='benchmark window return %'
JOIN entity_type bm ON bm.entity=br.subject AND bm.type='MarketIndex'
WHERE cr.metric='post-report window return %' AND fg.value>0 AND cr.value<br.value""",
    "CQ3": """SELECT DISTINCT cr.subject, cr.value, sr.value, br.value
FROM observation cr JOIN entity_type co ON co.entity=cr.subject AND co.type='Company'
JOIN sector cs ON cs.company=cr.subject
JOIN observation sr ON sr.subject=cs.sector AND sr.window=cr.window AND sr.metric='sector window return %'
JOIN observation br ON br.window=cr.window AND br.metric='benchmark window return %'
JOIN entity_type bm ON bm.entity=br.subject AND bm.type='MarketIndex'
WHERE cr.metric='post-report window return %' AND cr.value>sr.value AND cr.value>br.value""",
    "dependencies": """SELECT DISTINCT f.id,f.cq,f.entity,o.id,o.metric,o.value,
b.id,be.evidence,es.source
FROM finding f JOIN finding_observation fo ON fo.finding=f.id
JOIN observation o ON o.id=fo.observation
JOIN bundle b ON b.id=f.id||'_bundle' AND b.entity=f.entity
JOIN bundle_observation bo ON bo.bundle=b.id AND bo.observation=o.id
JOIN bundle_evidence be ON be.bundle=b.id
JOIN evidence_source es ON es.evidence=be.evidence""",
}
SPARQL_DEPENDENCIES = """PREFIX : <https://w3id.org/ontokg-eq#>
SELECT DISTINCT ?f ?cq ?entity ?o ?metric ?value ?b ?ev ?source WHERE {
 ?f a :AnalyticalFinding; :forCompetencyQuestion ?cq; :concernsEntity ?entity;
    :supportedByObservation ?o.
 ?o :hasMetricName ?metric; :hasMetricValue ?value.
 BIND(IRI(CONCAT(STR(?f), '_bundle')) AS ?b)
 ?b :explainsResultEntity ?entity; :includesObservation ?o; :containsEvidenceItem ?ev.
 ?ev :hasEvidenceSource ?source.
}"""


def one(g, subject, predicate, required=False):
    values = list(g.objects(subject, predicate))
    if len(values) > 1 or (required and len(values) != 1):
        raise ValueError(f"Expected {'one' if required else 'zero or one'} value: {subject} {predicate}")
    return str(values[0]) if values else None


def insert_many(db, table, rows, width):
    db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(width))})", sorted(set(rows)))


def load(g):
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    observations = sorted(set(g.subjects(C.hasMetricValue, None)), key=str)
    findings = sorted(set(g.subjects(RDF.type, C.AnalyticalFinding)), key=str)
    bundles = sorted(set(g.subjects(RDF.type, C.EvidenceBundle)), key=str)
    entities = {one(g, o, C.isObservationOf, True) for o in observations}
    entities |= {str(s) for s in g.subjects(RDF.type, C.Company)}
    entities |= {str(s) for s in g.subjects(RDF.type, C.MarketIndex)}
    entities |= {str(x) for pair in g.subject_objects(C.isClassifiedByIndustrySector) for x in pair}
    entities |= {one(g, f, C.concernsEntity, True) for f in findings}
    entities |= {one(g, b, C.explainsResultEntity, True) for b in bundles}
    insert_many(db, "entity", [(e,) for e in entities], 1)
    insert_many(db, "entity_type", [(str(s), str(t).split('#')[-1]) for s,t in g.subject_objects(RDF.type) if str(s) in entities], 2)
    insert_many(db, "sector", [(str(s),str(o)) for s,o in g.subject_objects(C.isClassifiedByIndustrySector)], 2)
    contexts = {str(o) for p in (C.observedOverWindow,C.observedInEventWindow,C.observedInPeriod)
                for o in g.objects(None,p)}
    insert_many(db,"context",[(x,) for x in contexts],1)
    insert_many(db,"context_property",[(str(s),str(p),str(o)) for s,p,o in g if str(s) in contexts],3)
    observation_rows = []
    for o in observations:
        window = one(g,o,C.observedOverWindow) or one(g,o,C.observedInEventWindow)
        observation_rows.append((str(o),one(g,o,C.isObservationOf,True),one(g,o,C.hasMetricName,True),
                                 float(one(g,o,C.hasMetricValue,True)),window,one(g,o,C.observedInPeriod)))
    db.executemany("INSERT INTO observation VALUES (?,?,?,?,?,?)",observation_rows)
    sources = {str(o) for o in g.objects(None,C.hasEvidenceSource)}
    evidence = {str(s) for s in g.subjects(C.hasEvidenceSource,None)}
    evidence |= {str(o) for o in g.objects(None,C.containsEvidenceItem)}
    insert_many(db,"source",[(s,) for s in sources],1)
    insert_many(db,"source_property",[(str(s),str(p),str(o)) for s,p,o in g if str(s) in sources],3)
    insert_many(db,"evidence",[(e,) for e in evidence],1)
    insert_many(db,"evidence_source",[(str(s),str(o)) for s,o in g.subject_objects(C.hasEvidenceSource)],2)
    insert_many(db,"finding",[(str(f),one(g,f,C.concernsEntity,True),one(g,f,C.forCompetencyQuestion,True),one(g,f,C.derivedByRule,True)) for f in findings],4)
    insert_many(db,"finding_observation",[(str(f),str(o)) for f in findings for o in g.objects(f,C.supportedByObservation)],2)
    insert_many(db,"bundle",[(str(b),one(g,b,C.explainsResultEntity,True)) for b in bundles],2)
    insert_many(db,"bundle_observation",[(str(b),str(o)) for b in bundles for o in g.objects(b,C.includesObservation)],2)
    insert_many(db,"bundle_evidence",[(str(b),str(e)) for b in bundles for e in g.objects(b,C.containsEvidenceItem)],2)
    db.commit()
    return db


def normalize(rows, numeric_positions):
    return {tuple(float(v) if i in numeric_positions else str(v) for i,v in enumerate(row)) for row in rows}


def rejection_tests(db):
    subject = db.execute("SELECT id FROM entity LIMIT 1").fetchone()[0]
    tests = {
        "numeric_type_check": ("INSERT INTO observation VALUES (?,?,?,?,?,?)",("test_bad_numeric",subject,"test","not-a-number",None,None)),
        "foreign_key_check": ("INSERT INTO observation VALUES (?,?,?,?,?,?)",("test_bad_subject","urn:missing-entity","test",1.0,None,None)),
    }
    results = {}
    for name,(query,args) in tests.items():
        db.execute("SAVEPOINT rejection_test")
        try:
            db.execute(query,args)
        except sqlite3.IntegrityError:
            results[name] = True
        else:
            results[name] = False
        finally:
            db.execute("ROLLBACK TO rejection_test")
            db.execute("RELEASE rejection_test")
    return results


def run():
    out = ROOT / "evaluation_jws"
    out.mkdir(exist_ok=True)
    report = {"schema_sha256":hashlib.sha256(SCHEMA.encode()).hexdigest(),
              "sql_sha256":{name:hashlib.sha256(q.encode()).hexdigest() for name,q in SQL.items()},
              "versions":{"sqlite":sqlite3.sqlite_version,"rdflib":rdflib.__version__},"markets":[]}
    all_pass = True
    for market in ("psx","msx","idx"):
        path = ROOT / "data" / f"demo_{market}_inferred.ttl"
        graph = Graph().parse(path,format="turtle")
        db = load(graph)
        item = {"market":market,"graph_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "counts":{t:db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                          ("entity","context","context_property","observation","source","source_property","evidence","finding","finding_observation","bundle","bundle_observation","bundle_evidence")},
                "checks":{}}
        for name in ("CQ1","CQ3","dependencies"):
            numeric = {5} if name == "dependencies" else {1,2,3}
            sparql = SPARQL_DEPENDENCIES if name == "dependencies" else (ROOT/"queries"/f"{name}_CASE_01.rq").read_text(encoding="utf-8")
            sql_rows = normalize(db.execute(SQL[name]),numeric)
            rdf_rows = normalize(graph.query(sparql),numeric)
            equal = sql_rows == rdf_rows
            item["checks"][name] = {"sql_rows":len(sql_rows),"sparql_rows":len(rdf_rows),"equal":equal}
            all_pass &= equal
        item["constraint_rejections"] = rejection_tests(db)
        all_pass &= all(item["constraint_rejections"].values())
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise AssertionError("Loaded relational data violates foreign keys")
        report["markets"].append(item)
        db.close()
    report["all_pass"] = bool(all_pass)
    (out/"relational_reuse.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    lines = ["# Relational reuse control", "", "Run: 2026-10-16. Same SQLite schema, CQ1/CQ3 SQL, and dependency join reused unchanged across PSX, MSX, and IDX.", "",
             "| Market | CQ1 SQL/SPARQL | CQ3 SQL/SPARQL | Dependency rows SQL/SPARQL | Numeric/FK rejection |", "|---|---:|---:|---:|---|"]
    for item in report["markets"]:
        checks = item["checks"]
        columns = [f"{checks[q]['sql_rows']}/{checks[q]['sparql_rows']} ({'equal' if checks[q]['equal'] else 'FAIL'})" for q in ("CQ1","CQ3","dependencies")]
        lines.append(f"| {item['market'].upper()} | {' | '.join(columns)} | {'pass' if all(item['constraint_rejections'].values()) else 'FAIL'} |")
    lines += ["", f"Schema SHA-256: `{report['schema_sha256']}`.", "SQL hashes and input graph hashes are recorded in `relational_reuse.json`.", "",
              "The relational schema includes numeric checks, foreign keys, source/context records, persistent findings, deciding observations, bundles, and evidence-source joins. Both CQ result sets include the returned numeric values, not only company identifiers. Dependency equality compares finding, CQ, entity, supported observation, metric/value, bundle, contextual evidence item, and source.", "",
              "The evidence join associates contextual bundle evidence with findings. It does not assert an independently verified source for each numeric observation; a bundle join can form multiple combinations of observations and contextual sources. Equality establishes representation/query equivalence on the supplied graphs, not complete provenance or absence of missing source records.", "",
              "This fair control uses the same stored graph metrics for both representations. It demonstrates that normalized relational schemas can also support unchanged cross-market queries, constraints, and evidence joins. It does not independently recompute source metrics, measure mapping/engineering effort, test different raw schemas, establish market-data authenticity, or show an RDF advantage. Empty-result queries are weak evidence and are reported explicitly. Constraint tests show rejection of a nonnumeric value and unknown subject; they are not a comprehensive integrity evaluation.", "",
              f"SQLite {sqlite3.sqlite_version}; rdflib {rdflib.__version__}. Overall: {'PASS' if all_pass else 'FAIL'}."]
    (out/"relational_reuse.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    raise SystemExit(not all_pass)


if __name__ == "__main__":
    run()
