# Executed external NPCS provenance comparison

The external system is the unmodified `ReifySparqlByte.jar` distributed by Asma et al., *Native Provenance Computation for Federated and Non-Federated SPARQL Queries*, TGDK 4(1), 2026, DOI [10.4230/TGDK.4.1.4](https://doi.org/10.4230/TGDK.4.1.4). Its [repository](https://github.com/ZubariaForthAcc/NPCS_Fed-NPCS) was checked out at the exact publication-archived commit `b95bff3b56587b2a9ef6655503aada19c844630d`. This is actual external execution, not an independently implemented semiring baseline.

## Scope and results

The author's CLI was invoked as `java -jar ReifySparqlByte.jar Standard query <query>`. Its signed byte-array response was decoded without modifying the generated SPARQL. A deterministic encoding maps each actual input triple to three RDF standard-reification facts and a SHA256-addressed statement identifier. Oxigraph 0.5.11 executes both ordinary and rewritten queries, using the same local engine; this is not a GraphDB/Stardog performance comparison.

| Market | Observation tuples: direct / NPCS | CQ3 BGP candidates: direct / NPCS | CQ3 post-filter positives |
|---|---:|---:|---:|
| PSX | 404 / 404 | 4 / 4 | 2 |
| MSX | 249 / 249 | 4 / 4 | 0 |
| IDX | 391 / 391 | 4 / 4 | 2 |

For all 1,044 analytical-observation tuples, the genuine NPCS output polynomial identifies exactly the four input facts supporting that tuple, with no unknown tokens. The full CQ3 BGP produces native polynomials of 15 input-triple tokens per candidate: 12/12 candidates have complete resolvable tokens. The numeric comparison is applied explicitly after external BGP execution. All four positive and eight nonpositive candidates agree with the original CQ3 result and the evidence-contract classification using recovered observation identifiers. The contract uses original graph type/classification metadata when interpreting those identifiers; this is a complementary validation stage, not a claim that NPCS verifies domain contracts natively.

## Material compatibility limitation

The full original CQ3 numeric `FILTER` path was also executed. At this exact published JAR version, its Standard rewrite emits extra reification of the generated object patterns, omits the provenance projection, and returns zero rows on each market; ordinary CQ3 returns 2/0/2. Both original and unmodified generated queries are retained as `*.cq3_full.*.rq`. The BGP-only path produces native provenance and answer parity. Therefore the external comparison supports **BGP provenance generation plus explicit analytical post-processing**, not complete NPCS CQ3 execution or full application replacement. This observed implementation limitation should not be represented as a theoretical defect of semiring provenance or evidence that OntoKG is generally superior.

## What this establishes

External provenance can already recover precise input-fact support. OntoKG's contract evaluation interprets whether that support satisfies an analytical requirement; it complements the external system. Standard provenance does not claim to certify financial definitions, units, period validity, or original source truth. No fault-detection percentage from an internal ablation should be attributed to NPCS.

`results.json` records the JAR hash, actual commit, Java version, input/query hashes, single-run rewriting and execution timings, polynomials, candidate-level verdicts, and coverage limitations. Timings include store loading and Java startup and support reproducibility only, not a speed ranking. Input graphs are unchanged. Archived source links are recorded where present; the comparison does not independently establish source accuracy.

## Reproduction

Run `docs/jws_external_provenance.py` with Python 3.13, rdflib 7.6.0 and pyoxigraph 0.5.11. Set `PYTHONPATH` to the workspace `.jws_deps` directory. The checked-out external repository is at workspace `jws_external/NPCS_Fed-NPCS`; portable Temurin JDK 17 is under `.jws_external_deps/java17`. The script invokes the upstream executable JAR directly and asserts tuple-count/answer parity, token resolution, exact observation support, and candidate-level numeric/contract parity. Repeating it overwrites only this separate evaluation output directory.
