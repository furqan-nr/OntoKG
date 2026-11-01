#!/usr/bin/env python3
"""Inventory whether historical LLM outputs can be rescored; never run models.

Only writes evaluation_jws/llm_rescore.{json,md}. The existing notebooks save
per-case score flags, not answer text. Aggregate tables cannot recover recall.
"""
import csv
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reproducible_OntoKG/evaluation_jws"


def run():
    tracked_roots = [REPO / "kaggle_faithfulness", REPO / "reproducible_OntoKG"]
    inventory = []
    answer_candidates = []
    for root in tracked_roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "evaluation_jws" in path.parts:
                continue
            if path.suffix.lower() == ".csv":
                with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                    reader = csv.reader(fh)
                    header = next(reader, [])
                if any(any(term in h.lower() for term in ("answer", "response", "generated_text")) for h in header):
                    # Aggregated cases/answers count is not raw answer text.
                    if any(h.lower().strip() in {"answer", "answer_text", "response", "generated_text", "llm_answer"} for h in header):
                        answer_candidates.append(str(path.relative_to(REPO)))
                if "faithfulness" in path.name or "panel" in path.name:
                    inventory.append({"path": str(path.relative_to(REPO)), "headers": header, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            if path.suffix.lower() == ".ipynb":
                nb = json.loads(path.read_text(encoding="utf-8"))
                source = "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []))
                outputs = [output for c in nb.get("cells", []) for output in c.get("outputs", [])]
                inventory.append({"path": str(path.relative_to(REPO)), "notebook_output_blocks": len(outputs), "source_mentions_panel_percase": "panel_percase.csv" in source, "source_serializes_answer_field": any(token in source for token in ('"answer":a', '"answer": a', "'answer': a", '"answer_text"')), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    panel_csv = REPO / "reproducible_OntoKG/evaluation_faithfulness/panel_results.csv"
    percase = REPO / "reproducible_OntoKG/evaluation_faithfulness/panel_percase.csv"
    result = {
        "status": "BLOCKED_NO_ARCHIVED_ANSWER_TEXT" if not answer_candidates else "REQUIRES_MANUAL_CASE_ALIGNMENT",
        "new_model_statistics_computed": False,
        "model_inference_run": False,
        "answer_candidates": answer_candidates,
        "historical_panel_results_csv_present": panel_csv.exists(),
        "historical_panel_percase_csv_present": percase.exists(),
        "inventory": inventory,
        "definitions": {
            "historical_numeric_faithfulness": "Numeric precision: matched stated decimals / stated decimals; empty stated set receives 1.0. Not recall.",
            "current_numeric_recall": "Distinct expected rounded numeric values mentioned within tolerance / distinct expected numeric values; omitting all numbers receives 0 when facts exist.",
            "current_source_date_provenance": "Any exact date OR source token substring occurs; date alone counts. This is stricter than generic source keywords but does not require actual source identity.",
            "stronger_source_identity": "Exact case-specific source identifier or source URL must occur; date alone does not count. Requires archived answers and case-specific source mappings.",
            "numeric_parser_limit": "Current decimal-only regex -?\\d+\\.\\d+ ignores integer and scientific-notation expressions and does not align numbers to metric roles; set-based recall collapses equal-valued metrics.",
            "unsupported_assertions_limit": "Keyword matches are heuristic flags, not validated semantic entailment judgments.",
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "llm_rescore.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Historical LLM panel rescoring audit", "", f"Status: **{result['status']}**. No new eight-model scores were produced and no models were run.", "", "The repository contains the historical eight-model aggregate Markdown table and pairwise McNemar table. No archived raw model-answer corpus was found. The expected panel_results.csv and panel_percase.csv files are absent from the evaluation_faithfulness directory. The panel notebook's per-case CSV writer saves score flags and labels, not generated answers, so even that file alone would not allow stronger rescoring.", "", "## Definition changes", "", "| Measure | Historical interpretation | Current/required interpretation |", "|---|---|---|", "| Numeric faithfulness | Precision of stated decimal numbers; silence can receive 1.0 | Report recall separately; aggregate precision cannot recover omissions |", "| Numeric recall | Absent from archived historical panel table | Current notebook/scorer computes distinct-value recall, but no historical answer texts exist to apply it |", "| Provenance | Archived aggregate citation rates | Current scorer accepts exact date OR source token; true source-identity coverage must require source ID/URL and cannot be inferred from old rates |", "| Unsupported assertions | Keyword counts | Heuristic only; cannot establish semantic entailment |", "", "The checked-in current notebook includes recall and specific date/source tokens, whereas the historical panel Markdown omits recall. The scorer version actually used for the archived table cannot be established from aggregate results alone. Do not describe the historical eight-model rates as recomputed under the current definitions.", "", "Current numerical scoring also ignores integers/scientific notation and associates values by numeric membership rather than metric identity. Two metrics with equal values collapse into one expected numeric value. Therefore its recall is numeric-value recall, not complete semantic fact recall.", "", "## What is required to unblock", "", "Recover the original per-model per-case generated answers together with the exact prompt/context, case identifier, original graph snapshot, source identity, and model revision. Apply a versioned scorer to those records and preserve per-case outputs. Do not regenerate answers merely to claim historical rescoring. If records cannot be recovered, keep the table explicitly historical and exploratory, or remove it from the main paper.", "", "Files checked (SHA-256 and notebook/CSV details are in llm_rescore.json):", ""]
    lines += [f"- `{r['path']}`" for r in inventory]
    (OUT / "llm_rescore.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "answer_candidates": answer_candidates, "files_inventoried": len(inventory)}, indent=2))


if __name__ == "__main__":
    run()
