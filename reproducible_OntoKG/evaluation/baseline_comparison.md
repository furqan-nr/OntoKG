# Baseline comparison (D2)

Relational/SQL baseline over the **same** PSX derived metrics, vs the KG/SPARQL pipeline.

## Result equivalence (PSX)

- CQ1 — SQL: [] ; SPARQL: [] ; **match: True**
- CQ3 — SQL: ['company_1', 'company_3'] ; SPARQL: ['company_1', 'company_3'] ; **match: True**

Both compute identical result entities — confirming the KG layer does not change the analytics, only what surrounds them.

## What the relational baseline cannot provide (without bespoke extra engineering)

| Dimension | Relational / SQL baseline | OntoKG-EQ (KG) |
|---|---|---|
| Answers CQ1/CQ3 | yes | yes (identical rows) |
| Structural validation of inputs | none built-in (ad-hoc CHECK constraints at best) | SHACL shapes, `Conforms=True` |
| Result -> evidence -> source -> provenance | not returned; needs hand-written joins across bespoke tables | automatic `EvidenceBundle` + traceable path |
| Derived classifications (findings) as first-class, queryable objects | no (transient query rows) | yes (`AnalyticalFinding` + rule/CQ provenance) |
| Cross-market reuse | schema + per-column SQL rewrites per market (e.g. eps vs eps_myr, pkr_usd_rate vs myr_usd_rate) | ontology + shapes + queries unchanged; bounded config only |
| Self-describing semantics | column names only | typed ontology terms with CQ justification |

## Contrast with GraphRAG / LLM answering (structural, not run here)

A GraphRAG/KG-RAG baseline would answer the CQs by retrieving subgraphs and generating text. We deliberately do **not** run an LLM: the point of contrast is that GraphRAG faithfulness is *estimated* (and known to admit faithfulness hallucinations even with retrieval), whereas OntoKG-EQ produces results by SPARQL over a SHACL-validated graph with every result bound to an evidence bundle whose observations, sources, and provenance are present in the validated graph by construction. Faithfulness is therefore **structurally guaranteed rather than measured**. A future empirical study (instrument an LLM over the same graph) can quantify GraphRAG explanation-faithfulness against this provenance-grounded reference.
