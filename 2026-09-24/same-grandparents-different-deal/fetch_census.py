#!/usr/bin/env python3
"""Fetch US-side data via the Census Reporter API (no key needed).

Release pinned to acs2023_5yr. Tables mirror the verified Census API map:
  median HH inc: B19013D / B19013 | education: C15002D / B15002
  tenure: B25003D / B25003 | employment: C23002D / B23025
  median earnings: B20017D / B20017 | nativity: B05003D / B05003
  poverty: B17001D / B17001 | occupation: C24010D / C24010
  Chinese pop: B02015
"""
import json
import time
import urllib.request
from pathlib import Path

RAW = Path("/home/hatch/workspace/passion-projects/2026-09-24/same-grandparents-different-deal/data/raw")
RAW.mkdir(parents=True, exist_ok=True)

BASE = "https://api.censusreporter.org/1.0/data/show/acs2024_5yr"
REL = "acs2023_5yr"
UA = {"User-Agent": "musing-with-mike/1.0 research"}

TABLES = ["B19013D", "B19013", "C15002D", "B15002", "B25003D", "B25003",
          "C23002D", "B23025", "B20017D", "B20017", "B05003D", "B05003",
          "B17001D", "B17001", "C24010D", "C24010", "B02015"]

GEOS = {
    "us": "01000US",
    "msa41860": "31000US41860",  # San Francisco-Oakland-Berkeley
    "msa41940": "31000US41940",  # San Jose-Sunnyvale-Santa Clara
    "msa42660": "31000US42660",  # Seattle-Tacoma-Bellevue
    "msa31080": "31000US31080",  # Los Angeles-Long Beach-Anaheim
    "msa35620": "31000US35620",  # New York-Newark-Jersey City
    "msa47900": "31000US47900",  # Washington-Arlington-Alexandria
}


def get(url, dest):
    if dest.exists() and dest.stat().st_size > 100:
        return
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                dest.write_bytes(r.read())
            return
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}: {last}")


# national: all tables
for t in TABLES:
    dest = RAW / f"reporter_{t}_us.json"
    get(f"{BASE}?table_ids={t}&geo_ids={GEOS['us']}", dest)
    print("ok", t, dest.stat().st_size)
    time.sleep(0.5)

# metros: Chinese pop + income + tenure (+ Asian variants)
for gname, gid in list(GEOS.items())[1:]:
    for t in ["B02015", "B19013D", "B19013", "B25003D", "B25003"]:
        dest = RAW / f"reporter_{t}_{gname}.json"
        get(f"{BASE}?table_ids={t}&geo_ids={gid}", dest)
        time.sleep(0.4)
    print("ok", gname)

print("done")
