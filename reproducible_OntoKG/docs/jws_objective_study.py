#!/usr/bin/env python3
"""Prepare objective audit tasks and analyze real responses; no human data invented.

prepare --graph PATH [--lineage PATH] freezes tasks from a named graph.
analyze --responses PATH reads externally collected anonymous task responses.
No participant recruitment, registration or external message is performed.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import random
import statistics

from rdflib import Graph, Namespace, RDF
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "objective_study_v2"
C = Namespace("https://w3id.org/ontokg-eq#")
PROV = Namespace("http://www.w3.org/ns/prov#")
AUD = Namespace("https://w3id.org/ontokg-eq/lineage-audit#")
FIELDS = ["participant_id", "sequence", "task_id", "condition", "judgment", "company_source_cell", "elapsed_seconds", "consent", "completed"]


def unique(g, subject, predicate):
    values = list(g.objects(subject, predicate))
    return values[0] if len(values) == 1 else None


def candidates(g, subject, metric):
    for obs in g.subjects(C.isObservationOf, subject):
        if str(unique(g, obs, C.hasMetricName)) == metric:
            value = unique(g, obs, C.hasMetricValue)
            window = unique(g, obs, C.observedOverWindow)
            if value is not None and window is not None:
                yield obs, Decimal(str(value)), window


def prepare(graph_path, lineage_path):
    response_template = OUT / "responses_template.csv"
    if response_template.exists():
        with response_template.open(newline="", encoding="utf-8-sig") as handle:
            if list(csv.DictReader(handle)):
                raise ValueError("Existing response template contains records; preparation refuses to overwrite collected responses or their frozen manifest.")
    g = Graph().parse(graph_path)
    lineage = Graph().parse(lineage_path) if lineage_path else g
    workbook_columns = {}

    def local_value(subject, name):
        found = [v for p, v in lineage.predicate_objects(subject)
                 if str(p).rsplit("#", 1)[-1] == name]
        return found[0] if len(found) == 1 else None

    def source_address(cell):
        workbook = local_value(cell, "workbookPath")
        address = local_value(cell, "excelCell")
        if workbook is None:
            return None
        if address is None:
            field, row = local_value(cell, "fieldName"), local_value(cell, "excelRow")
            if field is None or row is None:
                return None
            path = (ROOT.parent / str(workbook)).resolve()
            if not path.is_relative_to(ROOT.parent.resolve()) or not path.is_file():
                return None
            if path not in workbook_columns:
                book = openpyxl.load_workbook(path, read_only=True, data_only=True)
                header = next(book.active.iter_rows(values_only=True))
                workbook_columns[path] = {str(v): i + 1 for i, v in enumerate(header)}
                book.close()
            column = workbook_columns[path].get(str(field))
            if column is None:
                return None
            address = f"{openpyxl.utils.get_column_letter(column)}{int(row)}"
        return f"{workbook}!{address}"
    rows = []
    for company in sorted(set(g.subjects(RDF.type, C.Company)), key=str):
        for co, cv, cw in candidates(g, company, "post-report window return %"):
            for sector in g.objects(company, C.isClassifiedByIndustrySector):
                for so, sv, sw in candidates(g, sector, "sector window return %"):
                    for benchmark in g.subjects(RDF.type, C.MarketIndex):
                        for bo, bv, bw in candidates(g, benchmark, "benchmark window return %"):
                            if cw != sw or cw != bw:
                                continue
                            cells = []
                            for cell in lineage.objects(co, PROV.wasDerivedFrom):
                                address = source_address(cell)
                                if address is not None:
                                    cells.append(address)
                            if not cells:
                                continue
                            rows.append({"company": str(company), "window": str(cw), "company_obs": str(co), "sector_obs": str(so), "benchmark_obs": str(bo), "company_value": str(cv), "sector_value": str(sv), "benchmark_value": str(bv), "positive": cv > sv and cv > bv, "company_source_cells": sorted(set(cells))})
    positive = [r for r in rows if r["positive"]]
    negative = [r for r in rows if not r["positive"]]
    if len(positive) < 4 or len(negative) < 4:
        raise ValueError("Need at least four distinct positive and negative company/window cases; no synthetic replacements are inserted.")
    selected = positive[:4] + negative[:4]
    used = {(r["company"], r["window"]) for r in selected}
    # A missing benchmark is genuinely inconclusive only when the visible
    # company-versus-sector branch does not already refute the AND claim.
    unused = [r for r in rows if (r["company"], r["window"]) not in used
              and Decimal(r["company_value"]) > Decimal(r["sector_value"])]
    if len(unused) < 4:
        raise ValueError("Need four additional distinct company/window cases for missing-evidence tasks.")
    selected += unused[:4]
    OUT.mkdir(exist_ok=True)
    tasks = []
    for index, case in enumerate(selected):
        kind = "valid" if index < 4 else "invalid" if index < 8 else "incomplete"
        tasks.append({"task_id": f"T{index+1:02d}", "expected_judgment": kind, "withhold_benchmark": kind == "incomplete", **case})
    # Interleave types so each six-task condition receives two cases of each type.
    order = [0, 1, 4, 5, 8, 9, 2, 3, 6, 7, 10, 11]
    tasks = [tasks[i] for i in order]
    sequences = {}
    for seq, reverse_order, flip in [("S1", False, False), ("S2", False, True), ("S3", True, False), ("S4", True, True)]:
        ordered = list(reversed(tasks)) if reverse_order else tasks
        sequences[seq] = [{"task_id": t["task_id"], "condition": "B" if bool(i % 2) != flip else "A"} for i, t in enumerate(ordered)]
    manifest = {"status": "PREPARED_NOT_RUN_NOT_REGISTERED", "graph_path": str(graph_path.resolve()), "graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(), "lineage_sha256": hashlib.sha256(lineage_path.read_bytes()).hexdigest() if lineage_path else None, "tasks": tasks, "sequences": sequences, "condition_A": "Ungrouped observations plus source appendix", "condition_B": "Role-organized evidence plus the identical source appendix", "scope": "Verification against supplied records, not original-source authenticity or market forecasting."}
    (OUT / "task_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (OUT / "responses_template.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=FIELDS).writeheader()
    key = ["# Facilitator answer key — do not distribute with task packets", "", "Prepared material only: no participant results exist.", ""]
    for task in tasks:
        key.append(f"- {task['task_id']}: {task['expected_judgment']}; company source cell accepts any of {task['company_source_cells']}.")
    (OUT / "answer_key.md").write_text("\n".join(key) + "\n", encoding="utf-8")
    for seq, assignments in sequences.items():
        lines = [f"# Objective audit packet {seq}", "", "Research materials; complete only in an approved participant session.", "", "The claim in each task is that the company exceeds BOTH comparators on the stated window. Decide whether the supplied explanation demonstrates a valid claim, demonstrates an invalid claim, or lacks a required operand. Identify one source workbook/cell for the company statistic. Source-cell addresses identify supplied records; they do not authenticate external publications.", "", "Responses: valid / invalid / incomplete; company source cell; elapsed seconds recorded by the facilitator. Do not guess absent operands.", ""]
        for assignment in assignments:
            task = next(t for t in tasks if t["task_id"] == assignment["task_id"])
            condition = assignment["condition"]
            lines += [f"## {task['task_id']} — display {condition}", "", f"Company: {task['company']}", f"Window: {task['window']}", "", "Claim: company statistic exceeds both sector and benchmark statistics on this window.", ""]
            displayed = [("company", task["company_obs"], task["company_value"]), ("sector", task["sector_obs"], task["sector_value"])]
            if not task["withhold_benchmark"]:
                displayed.append(("benchmark", task["benchmark_obs"], task["benchmark_value"]))
            if condition == "A":
                lines += ["| Observation | Value (%) | Window |", "| --- | ---: | --- |"]
                for _, obs, value in reversed(displayed):
                    lines.append(f"| {obs} | {value} | {task['window']} |")
                lines += ["", "The observation names identify their metric roles; no validator verdict is supplied."]
            else:
                lines += ["| Analytical role | Observation | Value (%) | Matching window |", "| --- | --- | ---: | --- |"]
                for role, obs, value in displayed:
                    lines.append(f"| {role} | {obs} | {value} | {task['window']} |")
                lines += ["", "Required roles: company, sector, benchmark. Decision rule: company > sector AND company > benchmark. No validator verdict is supplied."]
            lines += ["", "Source appendix (identical across displays for this task):", ""]
            for cell in task["company_source_cells"]:
                lines.append(f"- {task['company_obs']} derives from supplied record `{cell}`.")
            lines += ["", "Judgment: ______  Company source cell: ______  Elapsed seconds: ______", ""]
        (OUT / f"packet_{seq}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Prepared {len(tasks)} distinct cases and {len(sequences)} counterbalanced packets; no human results generated.")


def analyze(response_path):
    manifest = json.loads((OUT / "task_manifest.json").read_text(encoding="utf-8"))
    keys = {t["task_id"]: t for t in manifest["tasks"]}
    with response_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError("Response CSV must contain every required field exactly once.")
        records = list(reader)
    if not records:
        raise ValueError("No participant responses supplied; objective performance cannot be estimated.")
    groups = defaultdict(list)
    seen = set()
    for row in records:
        validate_response_fields(row)
        participant = row["participant_id"].strip()
        task = row["task_id"]
        if not participant or task not in keys or row["sequence"] not in manifest["sequences"]:
            raise ValueError("Unknown participant/task/sequence; rows are not silently discarded.")
        expected = {r["task_id"]: r["condition"] for r in manifest["sequences"][row["sequence"]]}
        if row["condition"] != expected[task] or (participant, task) in seen:
            raise ValueError("Condition assignment mismatch or repeated task.")
        if row["consent"].lower() != "yes" or row["completed"].lower() != "yes":
            raise ValueError("Only consented completed responses may enter this complete-case analysis.")
        seconds = float(row["elapsed_seconds"])
        seen.add((participant, task))
        groups[participant].append({"condition": row["condition"], "sequence": row["sequence"], "correct": row["judgment"].strip().lower() == keys[task]["expected_judgment"], "source_correct": row["company_source_cell"].strip() in keys[task]["company_source_cells"], "seconds": seconds})
    participants = []
    for participant, rows in groups.items():
        if len(rows) != 12 or len({r["sequence"] for r in rows}) != 1:
            raise ValueError("Each included participant needs one consistent 12-task sequence; record attrition separately.")
        by_condition = {c: [r for r in rows if r["condition"] == c] for c in ["A", "B"]}
        if any(len(v) != 6 for v in by_condition.values()):
            raise ValueError("Expected six tasks per condition.")
        metrics = {c: {"accuracy": statistics.mean(r["correct"] for r in v), "source_accuracy": statistics.mean(r["source_correct"] for r in v), "median_seconds": statistics.median(r["seconds"] for r in v)} for c, v in by_condition.items()}
        participants.append({"participant_id": participant, **metrics, "accuracy_difference_B_minus_A": metrics["B"]["accuracy"] - metrics["A"]["accuracy"]})
    differences = [r["accuracy_difference_B_minus_A"] for r in participants]
    randomizer = random.Random(20261016)
    samples = sorted(statistics.mean(randomizer.choices(differences, k=len(differences))) for _ in range(10000))
    result = {"status": "ANALYZED_USER_SUPPLIED_RESPONSES", "participant_count": len(participants), "analysis_unit": "participant", "primary": "paired mean participant accuracy difference B minus A", "accuracy_difference": statistics.mean(differences), "participant_bootstrap_95_percent_interval": [samples[249], samples[9749]], "bootstrap_replicates": 10000, "bootstrap_seed": 20261016, "participants": participants, "graph_sha256": manifest["graph_sha256"], "responses_sha256": hashlib.sha256(response_path.read_bytes()).hexdigest(), "limits": "Complete-case analysis only; no causal claim without executing the counterbalanced design and checking allocation/attrition. This program cannot verify that supplied records came from real sessions."}
    # Results contain participant-level values: keep private until consented aggregation.
    destination = response_path.with_suffix(".analysis.json")
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Analyzed {len(participants)} supplied participant records; results kept beside the response file: {destination}")


def validate_response_fields(row):
    """Reject malformed records, rather than silently treating them as errors/time."""
    if any(not isinstance(row.get(field), str) for field in FIELDS) or None in row:
        raise ValueError("Missing fields or unexpected extra CSV cells.")
    if row["judgment"].strip().lower() not in {"valid", "invalid", "incomplete"}:
        raise ValueError("Judgment must be valid, invalid, or incomplete.")
    try:
        seconds = float(row["elapsed_seconds"])
    except ValueError as exc:
        raise ValueError("Elapsed time must be observed, finite and positive.") from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Elapsed time must be observed, finite and positive.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--graph", type=Path, required=True)
    prep.add_argument("--lineage", type=Path)
    analysis = commands.add_parser("analyze")
    analysis.add_argument("--responses", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.graph, args.lineage)
    else:
        analyze(args.responses)


if __name__ == "__main__":
    main()
