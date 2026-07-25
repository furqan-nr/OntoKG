#!/usr/bin/env bash
set -euo pipefail
python3 download_yahoo_idx_series.py --out raw_downloads --start 2026-01-15 --end 2026-05-30
python3 build_synchronized_idx_inputs.py --raw raw_downloads --output final_raw_inputs
