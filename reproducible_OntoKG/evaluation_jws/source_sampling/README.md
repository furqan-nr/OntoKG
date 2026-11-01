# Prospective stratified source-review frame

`frozen_manifest.json` fixes 52 cases across 29 dataset/rule/numerical-status strata using seed 20261016. Cases include positive, negative and incomplete classifications. Up to two cases are selected without replacement per stratum. Archived datasets and event-not-applicable cases are excluded.

This is a future review queue, **not 52 verified findings**. It was frozen after the earlier purposive PSX review; it is not preregistration. Original/corrected versions are not independent samples, and curated IDX overlaps scaled IDX. Case-level evidence can share upstream observations and sources. Stratum sampling fractions vary, so a pooled raw pass rate would not estimate population accuracy.

`expanded_evaluation_frozen.json` preserves the exact source report matching the manifest's input SHA256. The generator uses that snapshot when present, rather than a later rerun's possibly changed report. New evidence reviews belong in a separate ledger; they do not rewrite the frozen sampling frame.

For each case, review every deciding raw input against an appropriate primary source: publication identity and period, values, units, accounting scope, and temporal semantics. Record source unavailable, source-period mismatch, numeric mismatch, rounded agreement and exact agreement separately. Incomplete cases require authenticating absence/coverage where possible; a missing local cell does not establish that a source lacks the fact. Do not count locally recalculated values as source-authenticated without checking their inputs.

Freeze a scoring and weighted analysis plan before using these cases to estimate coverage or error rates. Preserve this manifest; record reviews separately with immutable source identifiers, page/cell locators, retrieval dates and source hashes. The generator refuses to overwrite a changed manifest. Run `docs/jws_source_sampling.py` to check reproducibility.
