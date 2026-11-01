# Historical LLM panel rescoring audit

Status: **BLOCKED_NO_ARCHIVED_ANSWER_TEXT**. No new eight-model scores were produced and no models were run.

The repository contains the historical eight-model aggregate Markdown table and pairwise McNemar table. No archived raw model-answer corpus was found. The expected panel_results.csv and panel_percase.csv files are absent from the evaluation_faithfulness directory. The panel notebook's per-case CSV writer saves score flags and labels, not generated answers, so even that file alone would not allow stronger rescoring.

## Definition changes

| Measure | Historical interpretation | Current/required interpretation |
|---|---|---|
| Numeric faithfulness | Precision of stated decimal numbers; silence can receive 1.0 | Report recall separately; aggregate precision cannot recover omissions |
| Numeric recall | Absent from archived historical panel table | Current notebook/scorer computes distinct-value recall, but no historical answer texts exist to apply it |
| Provenance | Archived aggregate citation rates | Current scorer accepts exact date OR source token; true source-identity coverage must require source ID/URL and cannot be inferred from old rates |
| Unsupported assertions | Keyword counts | Heuristic only; cannot establish semantic entailment |

The checked-in current notebook includes recall and specific date/source tokens, whereas the historical panel Markdown omits recall. The scorer version actually used for the archived table cannot be established from aggregate results alone. Do not describe the historical eight-model rates as recomputed under the current definitions.

Current numerical scoring also ignores integers/scientific notation and associates values by numeric membership rather than metric identity. Two metrics with equal values collapse into one expected numeric value. Therefore its recall is numeric-value recall, not complete semantic fact recall.

## What is required to unblock

Recover the original per-model per-case generated answers together with the exact prompt/context, case identifier, original graph snapshot, source identity, and model revision. Apply a versioned scorer to those records and preserve per-case outputs. Do not regenerate answers merely to claim historical rescoring. If records cannot be recovered, keep the table explicitly historical and exploratory, or remove it from the main paper.

Files checked (SHA-256 and notebook/CSV details are in llm_rescore.json):

- `kaggle_faithfulness\ontokg_faithfulness.ipynb`
- `kaggle_faithfulness\ontokg_faithfulness_panel.ipynb`
- `reproducible_OntoKG\evaluation\graphrag_faithfulness.csv`
- `reproducible_OntoKG\evaluation_faithfulness\graphrag_faithfulness.csv`
- `reproducible_OntoKG\evaluation_faithfulness\graphrag_faithfulness_live.csv`
- `reproducible_OntoKG\evaluation_faithfulness\panel_mcnemar.csv`
