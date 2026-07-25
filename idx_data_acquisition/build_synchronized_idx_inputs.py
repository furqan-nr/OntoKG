#!/usr/bin/env python3
"""Build strictly date-aligned IDX raw inputs for OntoKG-EQ.

The output is intentionally blocked unless every retained date appears in all six
input series. It never interpolates, forward-fills, back-fills, or invents an
observation. Generated final files are removed before each run, so a failed run
cannot leave stale historical files that look valid.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

EQUITIES = ("BBCA", "BMRI", "ISAT", "TOWR")
SERIES = (*EQUITIES, "USDIDR", "JCI")
ANCHORS = {
    "BBCA": "2026-01-27",
    "BMRI": "2026-02-06",
    "ISAT": "2026-02-09",
    "TOWR": "2026-03-18",
}
DEFAULT_START = "2026-01-15"
DEFAULT_END = "2026-05-29"


def parse_number(value):
    """Parse common CSV numeric formats without changing economic values."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("IDR", "").replace("Rp", "")
    if not text or text.lower() in {"nan", "null", "-", "n/a"}:
        return None
    multiplier = 1
    if text[-1:].upper() in {"K", "M", "B", "T"}:
        multiplier = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[text[-1].upper()]
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError as exc:
        raise ValueError(f"Cannot parse numeric value {value!r}") from exc


def canonicalize(frame: pd.DataFrame, name: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    lookup = {str(column).strip().lower(): column for column in frame.columns}
    if "date" not in lookup or "close" not in lookup:
        raise ValueError(f"{name}: expected at least Date and Close columns; got {list(frame.columns)}")

    out = pd.DataFrame()
    out["Date"] = pd.to_datetime(frame[lookup["date"]], errors="coerce").dt.normalize()
    out["Close"] = frame[lookup["close"]].map(parse_number)
    if name in EQUITIES:
        if "volume" not in lookup:
            raise ValueError(f"{name}: expected a Volume column")
        out["Volume"] = frame[lookup["volume"]].map(parse_number)

    out = out.dropna(subset=["Date", "Close"]).drop_duplicates(subset=["Date"], keep="last")
    out = out[out["Close"] > 0]
    if name in EQUITIES:
        out = out.dropna(subset=["Volume"])
        out = out[out["Volume"] >= 0]
    out = out[(out["Date"] >= start) & (out["Date"] <= end)].sort_values("Date")
    if out.empty:
        raise ValueError(f"{name}: no usable rows inside {start.date()} to {end.date()}")
    return out


def load_series(raw: Path, name: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    path = raw / f"{name}_history_source.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required raw input: {path}")
    return canonicalize(pd.read_csv(path, encoding="utf-8-sig"), name, start, end)


def case_coverage(common: pd.DatetimeIndex, symbol: str, required_pre: int, required_post: int) -> dict:
    anchor = pd.Timestamp(ANCHORS[symbol])
    later = common[common >= anchor]
    if len(later) == 0:
        return {
            "company_symbol": symbol,
            "announcement_date": anchor.date().isoformat(),
            "anchor_trade_date": "",
            "pre_trading_days": 0,
            "post_trading_days": 0,
            "required_pre": required_pre,
            "required_post": required_post,
            "status": "FAIL_NO_COMMON_DATE_ON_OR_AFTER_ANCHOR",
        }
    anchor_trade = later[0]
    pre = int((common < anchor_trade).sum())
    post = int((common > anchor_trade).sum())
    status = "COMPLETE" if pre >= required_pre and post >= required_post else "FAIL_INSUFFICIENT_COMMON_WINDOW"
    return {
        "company_symbol": symbol,
        "announcement_date": anchor.date().isoformat(),
        "anchor_trade_date": anchor_trade.date().isoformat(),
        "pre_trading_days": pre,
        "post_trading_days": post,
        "required_pre": required_pre,
        "required_post": required_post,
        "status": status,
    }


def clear_generated_outputs(output: Path) -> None:
    """Remove only generated files; retain README or manually added documentation."""
    output.mkdir(parents=True, exist_ok=True)
    generated = [
        *(f"{name}_history.csv" for name in SERIES),
        "coverage_report.csv",
        "series_overlap_report.csv",
        "build_status.txt",
    ]
    for filename in generated:
        target = output / filename
        if target.exists():
            target.unlink()


def write_status(output: Path, text: str) -> None:
    (output / "build_status.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def write_output(output: Path, aligned: dict[str, pd.DataFrame], common: pd.DatetimeIndex) -> None:
    for name, frame in aligned.items():
        final = frame[frame["Date"].isin(common)].sort_values("Date").copy()
        final["Date"] = final["Date"].dt.date.astype(str)
        columns = ["Date", "Close", "Volume"] if name in EQUITIES else ["Date", "Close"]
        final.to_csv(output / f"{name}_history.csv", index=False, columns=columns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True, help="Folder containing six *_history_source.csv files")
    parser.add_argument("--output", type=Path, required=True, help="Destination for validated synchronized inputs")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--required-pre", type=int, default=5)
    parser.add_argument("--required-post", type=int, default=35)
    args = parser.parse_args()

    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    if end < start:
        raise ValueError("--end must be on or after --start")
    if args.required_pre < 0 or args.required_post < 0:
        raise ValueError("Required pre/post session counts must be non-negative")

    clear_generated_outputs(args.output)
    try:
        aligned = {name: load_series(args.raw, name, start, end) for name in SERIES}
    except Exception as exc:
        write_status(args.output, f"BLOCKED: raw-input validation failed. No final CSVs were written.\nReason: {exc}")
        raise

    common = pd.DatetimeIndex(sorted(set.intersection(*(set(frame["Date"]) for frame in aligned.values()))))
    if common.empty:
        write_status(args.output, "BLOCKED: no common date exists across all six 