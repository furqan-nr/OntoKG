@echo off
setlocal
python download_yahoo_idx_series.py --out raw_downloads --start 2026-01-15 --end 2026-05-30
if errorlevel 1 goto :end
python build_synchronized_idx_inputs.py --raw raw_downloads --output final_raw_inputs
:end
endlocal
