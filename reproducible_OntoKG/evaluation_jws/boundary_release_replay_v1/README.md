# Actual stored release replay

Run `docs/jws_boundary_release_replay.py` with the documented Python dependencies
and this checkout's Git history. The fixed original commit is recorded in the
script/report. All six original/repaired market inputs must match the byte hashes
in the preceding independent release-audit ledgers; a mismatching source is rejected.

The end-to-end boundary `audit()` entry point reproduces the two previously
documented PSX event-support defects: original support/delivered sufficiency is
19/21; repaired support/delivered sufficiency is 21/21. Both transitions are R4
unknown to positive. The other nineteen actual stored findings remain positive.
These are paired artifact versions, not 42 independent findings or a population
prevalence estimate. No new corruption or participant result was constructed.

Two interface adaptations are explicit and in-memory: link each finding to its
already existing generated bundle, and expose the previous implicit market-index
lookup as company-to-index links. No numerical value, support link or actual bundle
member is changed by the adapter. The source graphs remain untouched.

All ambient pools return positive, but original R4 findings lack a sufficient
explicit event identity for independent event-anchored ambient replay; this is
not an event-specific truth guarantee. Source authentication, financial accuracy,
metadata readiness and human audit performance remain separate questions. The
matched synthetic baseline is a different experiment, not a competitor run on
these release records.
