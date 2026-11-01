# Frozen synthetic prototype protocol — 19 October 2026

This protocol is written before benchmark execution. No real source alternatives,
participant observations, deployment outcomes or manuscript claims are created.

Compare a restricted exact source-mode arithmetic-star solver with (1) independent
explicit role-assignment/world enumeration on small products and (2) exact Boolean
SAT over source choices, including compilation and solving. All observations are
locally qualified, one fixed entity/window/pool, r >= 1, independent groups with
nonempty mode lists. Reject unsupported constraints and arithmetic. All numbers
are exact finite rationals; numeric floats are not accepted.

Correctness: seed 20261019, 400 random small models (1–4 groups, 1–3 modes,
1–2 comparators, 0–2 values per role, integer numerators -4..4 / denominators
1,2,5). Check decisions and independently replay every counterworld. Include
equality, negative margins, missing roles, empty payloads, multiple values,
high precision, correlated versus independent marginals and changing witnesses.

Scaling: declared synthetic gap-cover families, k=4,8,16,32,64, r=1 and2,
certain and one interior gap removed (counterworld), three repetitions. Include
construction, compilation/decision and exact independent replay, report each
timing and median. Group mode counts determine possible-world products, not new
empirical samples. Explicit world oracle restricted to product<=4096.

Resource limits: 100000 interpreted values, 10000 modes, 32 comparators;
SAT at most 1000000 pair-conflict checks/clauses and 10000 Boolean variables.
No wall-time timeout is interpreted as a verdict. Benchmark runs are bounded to
these modest sizes; any failure is recorded explicitly, never converted to
certainty. Bit-complexity and compilation costs are not omitted.

Pre-final-run amendment (after initial smoke run, before the added exhaustive
test or final benchmark): add all 625 two-group/two-mode models over payloads
empty, C0, S0, C0S1, C1S0. Add a separately timed independent execution-certificate
checker and tamper controls. Enforce lexical length<=4096, decimal exponent
absolute value<=4096 and rational numerator/denominator bit length<=4096 before
unbounded expansion. Initial 400-model smoke and first 60 timing trials passed;
final artifacts below are regenerated from the amended code, not cherry-picked.
The 4096-bit bound also keeps exact summed endpoints below Python's default
integer-to-decimal display limit; unsupported sizes raise a resource error.
Final pre-report addition: also record a sound but incomplete independently
extremized aggregate-envelope bound. It may return certain or undetermined only;
the exact SAT baseline remains the capable principal comparator. This additional
abstraction is checked for soundness on the same frozen 1025 correctness models.
