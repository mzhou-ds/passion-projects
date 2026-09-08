#!/usr/bin/env python3
"""
Collect EDM subgenre release counts from the Discogs API.

Pivot from MusicBrainz (which tarpitted our IP after sustained polling).
Discogs database search supports style + year filters; pagination.items
gives the total matching releases.

11 styles x 26 years (2000-2025) = 286 queries, 1 per 3s (~15 min).
Persists after every query; circuit-breaks after 5 consecutive failures.
Writes data/discogs_style_counts.json
"""
import json
import time
import urllib.parse
from pathlib import Path

import requests

BASE = "https://api.discogs.com/database/search"
UA = "passion-projects-edm/1.0 (https://github.com/mzhou-ds/passion-projects; research project)"

STYLES = [
    "House", "Techno", "Trance", "Drum n Bass", "Dubstep", "Electro House",
    "Progressive House", "Deep House", "Tech House", "Hardstyle", "Future Bass",
]
YEARS = list(range(2000, 2026))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "discogs_style_counts.json"


def count_for(style: str, year: int) -> int:
    params = {
        "style": style,
        "genre": "Electronic",
        "year": year,
        "type": "release",
        "per_page": 1,
    }
    r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return int(r.json()["pagination"]["items"])


def save(results: dict) -> None:
    payload = {
        "metadata": {
            "source": "Discogs API database search",
            "query": "style=<style> genre=Electronic year=<year> type=release",
            "collected_at": time.strftime("%Y-%m-%d"),
            "note": "items = total Discogs releases matching style+year; -1 = query failed",
        },
        "counts": results,
    }
    OUT.write_text(json.dumps(payload, indent=1))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    total = len(STYLES) * len(YEARS)
    if OUT.exists():
        results = json.loads(OUT.read_text())["counts"]
        done0 = sum(len(v) for v in results.values())
        print(f"resuming: {done0}/{total} pairs already done", flush=True)
    else:
        results = {}
    consecutive_failures = 0
    for style in STYLES:
        results.setdefault(style, {})
        for year in YEARS:
            if str(year) in results[style]:
                continue
            try:
                results[style][str(year)] = count_for(style, year)
                consecutive_failures = 0
            except Exception as e:
                print(f"FAILED {style} {year}: {e}", flush=True)
                results[style][str(year)] = -1
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    print("5 consecutive failures - backing off", flush=True)
                    save(results)
                    return
            save(results)
            time.sleep(3)
        done = sum(len(v) for v in results.values())
        print(f"[{done}/{total}] finished {style}", flush=True)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
