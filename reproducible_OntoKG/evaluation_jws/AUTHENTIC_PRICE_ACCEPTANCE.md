# Acceptance rules for authentic price replacements

Frozen for the current retrieval pass on 16 October 2026. Obtaining a number from an official host is necessary but not sufficient to make a valid comparison.

1. Keep an immutable original input. A replacement is a separately versioned observation, with the original value and source status retained.
2. Record the official publisher URL, retrieval date, downloaded-response hash, response completeness, instrument identifier, trade date, field locator and exact value. A search snippet or retrieval timestamp alone does not establish a closing observation.
3. Distinguish official exchange, issuer, index administrator and third-party mirrors. Do not promote secondary values to primary verification. Public access does not establish redistribution permission.
4. Verify whether each value is a daily close, last intraday trade, previous close, adjusted close or index level. Record currency, timezone and applicable trading session. Do not interpret a current quote as an historical close.
5. Match return basis. PSX publishes KSE100 total-return and KSE100PR price-return variants; ordinary company close returns cannot silently be treated as equivalent to a total-return benchmark. Use the price-return variant for a price-only comparison, while documenting corporate-action treatment. An authentic but incompatible series remains unsuitable.
6. Preserve all required company dates. A full daily-series replacement must cover every declared endpoint/intermediate date; never silently intersect away missing days, interpolate, forward-fill, or treat missing as zero. An endpoint-only reconstruction must be labeled endpoint-only.
7. Distinguish the last pre-disclosure close, disclosure-date close, and first post-disclosure close. A disclosure document's date is not necessarily its exchange publication time. Do not claim initial reaction unless the baseline and disclosure timing support it.
8. A volume baseline needs genuinely pre-event observations under a declared horizon. A later post-event average cannot be renamed pre-event. Price availability does not imply volume-baseline availability.
9. Recompute returns independently and compare old/replacement values and classifications. A changed classification is a result to report, not a reason to reject the source. Do not expand a two-company repair into a claim that all cohorts are authenticated.
10. Keep unavailable, incomplete, incompatible-definition and authenticated-as-published statuses separate. Source-copy hashes are integrity checks, not publisher digital signatures or proof that a transcribed fact is correct.

Primary methodology: [PSX index overview](https://www.psx.com.pk/psx/product-and-services/indices) and [PSX KSE100/KSE100PR brochure, June 2025](https://www.psx.com.pk/psx/themes/psx/uploads/KSE-100-and-KSE100-PR-Brochure-Jun-2025-Updated.pdf). The official introduction notice is [PSX/N-695](https://www.psx.com.pk/psx/files/?file=255824-1.pdf), effective 30 June 2025. These documents establish variant definitions, not historical levels.
