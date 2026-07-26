# OntoKG-EQ Expert Study Kit (§7.6)

Everything needed to run the human-utility study and turn its results into the paper's §7.6.

## Files
| File | What it is | Who uses it |
|---|---|---|
| `facilitator_protocol.docx` | Step-by-step guide: design, recruitment, procedure, bias controls, ethics | **You** |
| `participant_packet.docx` | Consent + instructions + 8 real A/B items + rating grids | **Give to each participant** |
| `response_form.xlsx` | Data-entry sheet (15×8 rows pre-filled) | **You** (transcribe ratings) |
| `analyze_expert_study.py` | Computes stats + writes `results.md` with a ready-to-paste §7.6 paragraph | **You** (run at the end) |
| `stimuli.json` | The 8 A/B items as data (source for the packet) | reference |

## What YOU do (in order)
1. Read `facilitator_protocol.docx`.
2. Recruit **12–20** people with some finance background. (This is the only part that needs real people.)
3. For each: hand them `participant_packet.docx`; they rate Version A, then you reveal Version B and they
   re-rate + pick a preference. ~20–30 min each.
4. Enter their ratings into `response_form.xlsx`.
5. Run `pip install openpyxl && python analyze_expert_study.py` → get `results.md`.
6. Send me `results.md` (or the filled xlsx) and I'll write §7.6 into the manuscript.

## What you GIVE participants
Only `participant_packet.docx` (printed or shared). It is self-contained: consent, instructions, the 8
statements in both versions, and the rating boxes. Nothing else is needed.

## Why it matters
This study measures whether the provenance-grounded explanations improve analyst trust and perceived
completeness over result-only notes, turning the structural faithfulness guarantee into a measured
human-utility result. It is optional for reproduction; the pipeline and its results stand without it.
