# OntoKG-EQ Expert Study (§7.6) — completed study + reproduction

This directory contains the **completed** human-utility study reported in §7.6 of the manuscript
(within-subject design, n = 17 participants with a finance background), together with everything needed
to regenerate its statistics. The study has already been run; nothing here requires new participants.

## Files
| File | What it is |
|---|---|
| `Form responses (17).xlsx` | Raw anonymous Google Form export — the 17 collected responses |
| `response_form.xlsx` | The responses arranged on sheet `Data` (input to the analysis script) |
| `analyze_expert_study.py` | Recomputes the participant-level statistics and writes `results.md` |
| `results.md` | The regenerated statistics, as reported in §7.6 |
| `facilitator_protocol.docx` / `.md` | The protocol used: design, procedure, bias controls, ethics |
| `participant_packet.docx` / `.md` | Consent + instructions + the 8 A/B items + rating grids given to participants |
| `stimuli.json` | The 8 A/B items as data |
| `google_form/` | The Google Form definition used to collect the responses |

## Reproduce the reported statistics
```
pip install openpyxl
python analyze_expert_study.py      # reads response_form.xlsx (sheet 'Data'), writes results.md
```
Then compare `results.md` with §7.6. Expected values (participant-level, n = 17): trust +2.87
(Wilcoxon p ≈ 5×10⁻⁴, n = 17); completeness +3.35 (p ≈ 6×10⁻⁴, n = 16 non-zero pairs — one participant
rated completeness identically for both versions, a zero difference the signed-rank test excludes); and
16/17 participants preferring the evidence-grounded version on all eight items (sign test p ≈ 1.5×10⁻⁵).

## Design (as run)
Each participant gave voluntary opt-in consent, rated Version A (result-only note), then rated Version B
(the same statement with its provenance-grounded evidence bundle) and chose a preference (~20–30 min per
participant). Ratings used ad-hoc 7-point trust and justification-completeness items. Analysis is at the
**participant level** (each participant contributes one mean per condition) to avoid pseudoreplicating the
136 nested item ratings. Caveats — single-session convenience panel, A-before-B information/order effect,
and a counterbalanced three-condition replication as future work — are stated in §7.6 and in `results.md`.

## What it measures
Whether provenance-grounded explanations improve analyst trust and perceived completeness over
result-only notes, turning the structural transcription-consistency guarantee into a measured
human-utility result. It is optional for pipeline reproduction; the pipeline and its results stand
without it.
