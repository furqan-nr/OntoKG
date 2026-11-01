# Execution-plan adjustment

The initial full-cohort attempt used four unbound SELECT DISTINCT queries over the merged graph per policy. The attempt was interrupted on 19 October 2026 before its first policy completed, following several minutes without a completed policy output. No classification disagreement had been observed or discarded; exact elapsed time was not recorded, so this is not timing evidence.

The revised execution plan prepares the same query texts and supplies each declared provider as an initial binding before evaluation. All 533 provider identities, all six frozen policies, the integer oracle and fourteen constructed controls are retained. This is a query-execution adjustment, not a change to expected answers or the experimental population. The resulting cohort run is provider-bound SPARQL, not cohort-level SHACL validation. Actual SHACL execution is separately counted on controls.

No speed, maintenance or algorithm-superiority claim follows from the interrupted attempt. The query texts and hashes are saved by policy in this directory.
