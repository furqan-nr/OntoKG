# OntoKG-EQ Expert Study — Facilitator Protocol

## Purpose
Convert the paper's *structural* faithfulness guarantee into a *measured* human-utility result: do the
provenance-grounded explanations (Version B) improve analyst **trust** and **perceived completeness**
over result-only notes (Version A)? This is the §7.6 pre-registered study.

## Design
Within-subject, within-item A/B. Each participant rates the **same** statement twice — first as a
result-only note (A), then with its evidence bundle (B) — across 8 real OntoKG-EQ items (PSX, MSX, IDX,
and the 64-stock IDX set). Primary outcomes: Trust (1–7), Completeness of justification (1–7). Secondary:
forced A/B preference; optional verification time.

## What you need
- **Participants:** target **12–20** people with some finance background (finance/MBA/CS graduate
  students, junior analysts, or faculty colleagues). 12 is enough for significance if the effect is as
  large as expected; more is better.
- **Materials (in this folder):** `participant_packet.docx` (print or share one per participant),
  `response_form.xlsx` (data entry), `analyze_expert_study.py` (analysis).
- **Time:** ~20–30 min per participant; the whole study can be done in a week.

## Procedure (per participant)
1. Assign a Participant ID (P01, P02, …). Record role and years of experience.
2. Give them the packet. Ask them to read each item's **Version A first** and rate Trust + Completeness,
   and note what they'd need to verify it. **Keep Version B covered** until Part 1 is done (fold the page,
   or use a digital form that reveals B only after A is submitted).
3. Reveal **Version B**; they re-rate Trust + Completeness and mark which version they'd rather receive.
4. (Optional) Time how long they spend verifying each version and record seconds.
5. Transfer their ratings into `response_form.xlsx` (one row per item; 15 participants × 8 items are
   pre-filled — add rows for more).

## Bias controls
- Reveal B only after A is rated (prevents anchoring).
- Randomise item order across participants (shuffle the 8 items).
- Tell participants there are no right/wrong answers and the tool — not they — is under evaluation.
- Keep the two conditions visually parallel (same claim sentence; B only *adds* evidence).

## Analysis
Run `python analyze_expert_study.py` in this folder. It computes descriptive stats, a Wilcoxon
signed-rank test (B vs A) for Trust and Completeness, an exact sign test, the rank-biserial effect size,
and a binomial test on preference, and writes `results.md` including a ready-to-paste §7.6 paragraph. Send
me `results.md` (or the filled `response_form.xlsx`) and I will finalise §7.6 in the manuscript.

## Ethics / consent
The packet's first page is a short anonymous-consent block (18+, voluntary, aggregate reporting, no
personal identifiers). For a formal submission, obtain your institution's ethics/IRB clearance or an
exemption before running; keep signed/── ticked consent pages on file. No sensitive personal data is
collected.
