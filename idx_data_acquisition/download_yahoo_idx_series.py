#!/usr/bin/env python3
"""Download six daily IDX/FX/index source series from Yahoo Finance's chart endpoint.

This is a convenience acquisition route. It retries temporary HTTP/network failures
and writes raw CSVs only after all six series are retrieved successfully. A manual
source may be used instead, provided the exact required filenames and columns are
preserved. The downstream builder is the acceptance gate.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SYMBOLS = {
    "BBCA": ("BBCA.JK", True),
    "BMRI": ("BMRI.JK", True),
    "ISAT": ("ISAT.JK", True),
    "TOWR": ("TOWR.JK", True),
    "USDIDR": ("IDR=X", False),
    "JCI": ("^JKSE", False),
}


def epoch(date_text: str) -> int:
    return int(datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc).timestamp())


def fetch(symbol: str, start: str, end: str, attempts: int, retry_seconds: float):
    params = urlencode({
        "period1": epoch(start),
        "period2": epoch(end),  # Yahoo endpoint uses exclusive end date.
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "false",
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; OntoKG-EQ reproducibility acquisition)"})
            with urlopen(request, timeout=45) as response:
                payload = json.load(response)
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(f"Yahoo returned an API error: {chart['error']}")
            result = chart.get("result")
            if not result:
                raise RuntimeError("Yahoo returned no chart result")
            quote = result[0]["indicators"]["quote"][0]
            timestamps = result[0]["timestamp"]
            rows = []
            jakarta = ZoneInfo("Asia/Jakarta")
            closes = quote.get("close", [None] * len(timestamps))
            volumes = quote.get("volume", [None] * len(timestamps))
            for index, timestamp in enumerate(timestamps):
                close = closes[index]
                volume = volumes[index]
                if close is None:
                    continue
                date = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(jakarta).date().isoformat()
                rows.append((date, close, volume))
            if not rows:
                raise RuntimeError("Yahoo returned no usable daily rows")
            return rows, url
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(retry_seconds * attempt)
    raise RuntimeError(f"download failed after {attempts} attempt(s): {last_error}")

