"""Fetch Discogs release counts by genre x year (per_page=1, read pagination total).

Paced at ~1.2s per request to stay under the unauthenticated 60/min limit.
Saves incrementally to counts.json so a restart never loses work.
"""
import json
import os
import time

import requests

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "discogs_counts.json")
BASE = "https://api.discogs.com/database/search"
HEADERS = {"User-Agent": "MusingWithMike/1.0 (research; contact: michaelzhou96@gmail.com)"}

GENRES = ["electronic", "rock", "hip hop", "pop"]
YEARS = list(range(2005, 2027))


def get_count(genre, year, tries=0):
    params = {"genre": genre, "type": "release", "year": year, "per_page": 1}
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=30)
    if r.status_code == 429 and tries < 5:
        wait = int(r.headers.get("Retry-After", 60))
        print(f"429, waiting {wait}s", flush=True)
        time.sleep(wait + 2)
        return get_count(genre, year, tries + 1)
    r.raise_for_status()
    return r.json()["pagination"]["items"]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = {}
    if os.path.exists(OUT):
        data = json.load(open(OUT))
    for genre in GENRES:
        data.setdefault(genre, {})
        for year in YEARS:
            key = str(year)
            if key in data[genre]:
                continue
            try:
                n = get_count(genre, year)
            except Exception as e:
                print(f"FAIL {genre} {year}: {e}", flush=True)
                json.dump(data, open(OUT, "w"), indent=2)
                raise
            data[genre][key] = n
            print(f"{genre} {year}: {n:,}", flush=True)
            json.dump(data, open(OUT, "w"), indent=2)
            time.sleep(1.2)
    print("DONE")


if __name__ == "__main__":
    main()
