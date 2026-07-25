# Data dictionary

This dictionary documents the data artifacts in the OntoKG-EQ reproducibility bundle.
The fields and row counts below map to the CSV columns and RDF assertions used to build `data/demo.ttl`.

## Files shipped in `data/`

| file name | description | key columns or RDF role | row count | provenance handling |
|---|---|---|---:|---|
| `data/demo.ttl` | Demonstrator RDF graph used for the CQ and SHACL runs (CQ1–CQ5 examples, time-scoped observations, evidence-linked provenance). | RDF instances/assertions aligned to the OntoKG-EQ core ontology classes and properties. | 343 triples | Each statement set links to provenance records via `:hasProvenanceRecord`. |
| `data/provenance_register.csv` | Provenance register for the bundle (source, activity, agent, timestamps). | provenance record ID, source, activity, agent, timestamp | see file | Primary provenance table; reconciles with the RDF provenance records in `demo.ttl`. |

## Logical data layer behind `demo.ttl`

The following are the conceptual data tables that the demonstrator graph represents. They are
materialized into `data/demo.ttl` from the source spreadsheets (PSX `7 PSX data v4`, and the
mirrored Bursa Malaysia `updated MSX`), and are not shipped as separate CSVs in this bundle.

| logical table | description | key columns or RDF role | expected row count | provenance handling |
|---|---|---|---:|---|
| reporting_periods | Reporting period metadata | `reporting_period_id`, period start/end, fiscal labeling | 8 | Map each row to source/time provenance record |
| company_market_observations | Company-level market observations | company identifier, instrument, observation date, metric/value | 159 | Record source endpoint/file and extraction timestamp |
| comparator_observations | Comparator (sector/benchmark) market observations | comparator identifier, date, metric/value, comparator link | 318 | Preserve source lineage and transformation step IDs |
| fx_observations | Exchange-rate observations | currency pair, date/time, rate, source marker | 50 | Track FX provider/source and retrieval time |
| announcements_disclosures | Announcement/disclosure events | issuer/entity, event date, disclosure type/reference | 4 | Keep citation/reference URI and ingestion provenance |
| provenance_records | Provenance ledger for ingested/transformed records | provenance record ID, source, activity, agent, timestamp | 24 | Primary provenance table; must reconcile with all data artifacts |
