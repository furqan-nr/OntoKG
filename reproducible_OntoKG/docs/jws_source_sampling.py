"""Freeze prospective source-audit cases; selected does not mean verified."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'evaluation_jws/expanded_evaluation/results.json'
OUT = ROOT / 'evaluation_jws/source_sampling'
FROZEN_INPUT = OUT / 'expanded_evaluation_frozen.json'
SEED = 20261016


def main():
    source = FROZEN_INPUT if FROZEN_INPUT.exists() else INPUT
    data = json.loads(source.read_text(encoding='utf-8'))
    strata = defaultdict(list)
    for dataset in data['datasets']:
        name = dataset['dataset']
        # Curated IDX overlaps the scaled cohort. Keep scaled as a separate
        # robustness frame, never sum its sampling units with curated IDX.
        if 'financial_v2' not in name:
            continue
        for i, case in enumerate(dataset['cases']):
            if case['label'].startswith('not_applicable'):
                continue
            strata[(name, case['rule'], case['label'])].append((i, case))
    rng = random.Random(SEED)
    selected = []
    frames = []
    for key, cases in sorted(strata.items()):
        picked = rng.sample(cases, min(2, len(cases)))
        frames.append(dict(dataset=key[0], rule=key[1], label=key[2], population_cases=len(cases), selected_cases=len(picked)))
        for i, case in sorted(picked):
            selected.append(dict(dataset=key[0], rule=key[1], numerical_label=key[2], case_index=i,
                company=case['company'], observations=case['observations'], window=case.get('window'),
                review_status='NOT_YET_REVIEWED', required_checks=['original source identity and accounting period',
                    'value, unit and accounting scope', 'all deciding transformation inputs',
                    'publication date semantics where required', 'matching observed price intervals where required']))
    result = dict(version='prospective-source-review-v1', seed=SEED,
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        design='Up to two cases sampled uniformly without replacement within each corrected dataset/rule/numerical-status stratum.',
        limits='Frozen after earlier purposive PSX checks; not a preregistered or completed independent audit. Case dependencies and overlapping datasets preclude treating selected cases as independent facts. No representative accuracy estimate until a predeclared weighted analysis and source review are completed.',
        strata=frames, selected_cases=selected)
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / 'frozen_manifest.json'
    if destination.exists():
        existing = json.loads(destination.read_text(encoding='utf-8'))
        assert existing == result, 'Frozen manifest differs: create a new audit version; do not overwrite.'
    else:
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert len({(x['dataset'], x['case_index']) for x in selected}) == len(selected)
    print(f'Frozen {len(selected)} source-review cases across {len(frames)} strata. None is marked verified.')


if __name__ == '__main__':
    main()
