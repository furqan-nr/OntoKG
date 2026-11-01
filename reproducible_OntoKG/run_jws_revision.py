#!/usr/bin/env python3
"""Run the local JWS revision checks without rebuilding archived market graphs.

Outputs are local evaluation artifacts. No upload, submission or model call occurs.
The optional workspace dependency directory is a convenience for this checkout;
ordinary installed packages work on other machines.
"""
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
STAGES = [
    "docs/analytical_correctness.py",
    "docs/jws_source_lineage.py",
    "docs/test_jws_contracts.py",
    "docs/jws_contract_run.py",
    "docs/jws_contract_faults.py",
    "docs/jws_contract_evolution.py",
    "docs/jws_relational_reuse.py",
    "docs/jws_revision_check.py",
]


def main():
    environment = os.environ.copy()
    local_deps = ROOT.parent / ".jws_deps"
    if local_deps.is_dir():
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(local_deps)] + ([environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else [])
        )
    results = []
    out = ROOT / "evaluation_jws"
    out.mkdir(exist_ok=True)
    for stage in STAGES:
        path = ROOT / stage
        process = subprocess.run(
            [sys.executable, str(path)], cwd=ROOT,
            env=environment, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        results.append({
            "script": stage,
            "script_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        })
        print(f"{'PASS' if process.returncode == 0 else 'FAIL'} {stage}", flush=True)
        if process.returncode:
            break
    payload = {
        "python": platform.python_version(), "platform": platform.platform(),
        "all_stages_passed": len(results) == len(STAGES) and all(r["exit_code"] == 0 for r in results),
        "stages": results,
        "scope": "Local revision verification; no original-source authentication, model rescoring, or general SPARQL proof.",
    }
    (out / "revision_run.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if not payload["all_stages_passed"]:
        print(results[-1]["stdout"] + results[-1]["stderr"], file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
