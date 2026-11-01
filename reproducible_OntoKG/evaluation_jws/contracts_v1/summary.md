# Executable finding contracts v1

Contract 1.0.0; Python 3.13.5.

| Market | Findings | Finding support sufficient | Bundle sufficient | All roles available | Source-linked bundle witness |
|---|---:|---:|---:|---:|---:|
| psx | 9 | 9 | 9 | 9 | 9 |
| msx | 2 | 2 | 2 | 2 | 2 |
| idx | 10 | 10 | 10 | 10 | 10 |

Complete-bundle rate (at least one sufficient witness in the correctly targeted actual bundle): 21/21. Source sufficiency requires every recorded dependency cell of a sufficient bundle witness to have exactly one primary source with matching source identifier; it does not prove that all actual computational dependencies were recorded. A plausible but wrong consistently relinked source cannot be detected without an independent truth oracle. Observation and window RDF types are checked. R4 finding-to-event identity remains unverified where the finding declares no event-window anchor. Replay arithmetic reads RDF lexical numbers directly as Decimal; strict decimal margin boundaries are regression tested.

R4 uses a single passing OR branch as a sufficient witness. All-role availability is a separate contextual completeness measure. Only actual prov:wasDerivedFrom links count as source linkage; unlinked default-zero values remain untrusted. Graph units absent from observations remain explicitly unverified; expected units in the contract are assumptions, not measurements verified by the graph. Source linkage is not independent source truth. R2 tests the archived classification, not the complete CQ2 query. Event return labels retain the archived arithmetic caveat. Full-graph truth is an independent Python predicate replay over graph observations, not upstream numerical recomputation and not general SPARQL validation.

The contracted TTL files are separate status/witness overlays. Original graphs and historical reports are unchanged. SHA256 hashes identify inputs and implementations in results.json.

Reproduce with Python 3.13, rdflib available on PYTHONPATH: docs/jws_contract_run.py.
