"""Reproduce strengthened revision artifacts without changing archived graphs."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import hashlib
import json
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--external', action='store_true', help='Also run NPCS; requires the separately obtained upstream JAR and Java runtime.')
parser.add_argument('--sources', action='store_true', help='Recheck manually reviewed issuer transcriptions and evidence hashes; requires cited local source copies.')
parser.add_argument('--prices', action='store_true', help='Recheck local reviewed price captures and acquisition ledgers; does not download restricted market feeds.')
parser.add_argument('--audit-only', action='store_true', help='Check existing evidence without rebuilding frozen financial/evaluation artifacts or preparing study packets.')
args = parser.parse_args()
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
deps = ROOT.parent / '.jws_deps'
if deps.exists():
    env['PYTHONPATH'] = str(deps) + os.pathsep + env.get('PYTHONPATH', '')
stages = [
    ['docs/jws_financial_v2.py'],
    ['docs/jws_expanded_evaluation.py'],
    ['docs/jws_metadata_v2.py'],
    ['docs/jws_temporal_resolution.py'],
    ['docs/jws_report_aligned_cohort.py'],
    ['docs/jws_objective_study.py', 'prepare', '--graph', 'evaluation_jws/financial_v2/demo_idx_scaled_financial_v2.ttl'],
    ['docs/test_jws_objective_study.py'],
]
if args.audit_only:
    stages = [['docs/test_jws_contracts.py'], ['docs/test_jws_objective_study.py'],
              ['docs/jws_source_sampling.py']]
stages.append(['docs/test_jws_expanded_categories.py'])
stages.append(['docs/test_jws_boundary_contracts.py'])
stages.append(['docs/test_jws_boundary_analytical.py'])
for test in ('source_oracle', 'contract', 'matched_baseline', 'application'):
    stages.append(['docs/test_jws_nhs_'+test+'.py'])
stages.append(['docs/test_jws_nhs_change_replay.py'])
if args.external:
    stages.append(['docs/jws_external_provenance.py'])
if args.sources:
    stages.append(['docs/jws_source_authentication.py'])
    stages.append(['docs/jws_annual_source_repair.py', '--self-test'])
    stages.append(['docs/jws_annual_source_repair.py'])
    stages.append(['docs/jws_ppl_source_completion.py', '--self-test'])
    stages.append(['docs/jws_ppl_source_completion.py'])
    stages.append(['docs/jws_systematic_source_audit.py', '--test'])
    stages.append(['docs/jws_systematic_source_audit.py'])
if args.prices:
    stages.append(['docs/jws_psx_authentic_prices.py'])
    stages.append(['docs/jws_psx_regulator_recovery.py'])
    stages.append(['docs/test_jws_psx_regulator_recovery.py'])
    stages.append(['docs/jws_malaysia_authentic_prices.py', '--test'])
    stages.append(['docs/jws_malaysia_authentic_prices.py'])
    stages.append(['docs/jws_price_definition_audit.py', '--test'])
    stages.append(['docs/jws_price_definition_audit.py'])
    stages.append(['docs/jws_source_backed_cohort.py', '--test'])
    stages.append(['docs/jws_source_backed_cohort.py'])
stages.append(['docs/jws_revision_check.py'])
run_report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'stages': [],
              'audit_only': args.audit_only,
              'human_study_executed': False, 'external_requested': args.external,
              'source_captures_requested': args.sources, 'price_captures_requested': args.prices}
report_path = ROOT / 'evaluation_jws/strengthening_run.json'
for stage in stages:
    print('Running', stage[0], flush=True)
    started = time.monotonic()
    completed = subprocess.run([sys.executable, *stage], cwd=ROOT, env=env,
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
    script = ROOT / stage[0]
    run_report['stages'].append({'command': stage, 'exit_code': completed.returncode,
        'duration_seconds': round(time.monotonic() - started, 3),
        'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
        'stdout': completed.stdout[-12000:], 'stderr': completed.stderr[-12000:]})
    run_report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    run_report['all_completed_stages_pass'] = all(s['exit_code'] == 0 for s in run_report['stages'])
    report_path.write_text(json.dumps(run_report, indent=2), encoding='utf-8')
    if completed.stdout:
        print(completed.stdout, end='')
    if completed.stderr:
        print(completed.stderr, end='', file=sys.stderr)
    if completed.returncode:
        raise SystemExit(completed.returncode)
print('Strengthening checks complete. No human study has been executed.')
