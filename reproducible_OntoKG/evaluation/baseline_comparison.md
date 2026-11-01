# Baseline comparison (D2): historical SQL result record

Status reviewed 2026-10-16. The result rows below are retained historical output, not a new execution
or a general comparison of relational and semantic technologies. They test two PSX queries only.

Relational/SQL baseline over the **same** PSX derived metrics, vs the KG/SPARQL pipeline.

## Result equivalence (PSX)

- CQ1 — SQL: [] ; SPARQL: [] ; **match: True**
- CQ3 — SQL: ['company_1', 'company_3'] ; SPARQL: ['company_1', 'company_3'] ; **match: True**

These historical executions returned identical entity sets for CQ1 and CQ3. This does not establish
equivalence of all computations or queries; in particular, empty CQ1 results provide limited coverage.

## Capabilities implemented in this demonstrator

| Dimension | Relational / SQL baseline | OntoKG-EQ (KG) |
|---|---|---|
| Answers CQ1/CQ3 | yes | yes (identical rows) |
| Structural validation of inputs | this baseline does not evaluate relational constraints | declared SHACL shapes |
| Result -> evidence -> source -> provenance | relational provenance can be represented with tables and joins; completeness was not compared here | evidence bundle and provenance paths implemented |
| Derived classifications (findings) as queryable objects | possible with tables or views; not benchmarked here | `AnalyticalFinding` nodes implemented |
| Cross-market reuse | common normalized schemas can support reusable SQL; adaptation effort was not measured | reuse after mapping to the common ontology; mapping remains required |
| Explicit semantics | schemas, dictionaries, and metadata can supply semantics | typed ontology terms with CQ justification |

Relational systems support integrity constraints, reusable views, provenance, and persistent result
objects. Their absence from a small baseline is an implementation choice, not an inherent limitation.
No experiment here establishes lower engineering effort, superior analytical accuracy, or stronger
provenance completeness for the KG approach. A matched RDF/provenance ablation is needed to isolate
the additional contribution of CQ governance and evidence checks.

## Subsequent LLM evidence (separate experiment)

The previous statement that no LLM was run is obsolete. See
`../evaluation_faithfulness/graphrag_faithfulness_live.md` and its CSV for the recorded Qwen2.5-7B and
SmolLM2-1.7B runs (recorded run date 2026-06-30). Those runs evaluate generation from supplied
evidence; they are not a matched end-to-end evaluation of retrieval, graph construction, and answering
against a complete GraphRAG system. Their historical measurements were not rerun during this cleanup.
Deterministic rendering constrains output to selected stored evidence, but does not by itself prove
source truth, analytical correctness, or inclusion of every deciding observation.
