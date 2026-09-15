#!/usr/bin/env python3
"""Fetch all raw data for the 49th Parallel project.

Sources:
  - World Bank API v2 (api.worldbank.org) — no key required
  - NHL records API (records.nhl.com) — NHL draft picks by year, with countryCode
  - Google Books Ngram Viewer JSON endpoint — word frequencies in
    American English (corpus 27) and British English (corpus 28), 2019 edition

Saves raw responses to data/raw/ so reruns never lose work.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def get(url, dest, tries=4, sleep=1.0):
    if dest.exists():
        return dest
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "musing-with-mike/1.0 research"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            dest.write_bytes(data)
            return dest
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(sleep * (i + 1))
    raise RuntimeError(f"failed {url}: {last}")


# ---------------- World Bank indicators ----------------
WB_INDICATORS = {
    "life_expectancy": "SP.DYN.LE00.IN",
    "health_exp_gdp": "SH.XPD.CHEX.GD.ZS",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "gini": "SI.POV.GINI",
    "migrant_stock": "SM.POP.TOTL",
    "population": "SP.POP.TOTL",
    "homicide_rate": "VC.IHR.PSRC.P5",
    "co2_per_capita": "EN.ATM.CO2E.PC",
}
for name, code in WB_INDICATORS.items():
    url = (
        f"https://api.worldbank.org/v2/country/CAN;USA/indicator/{code}"
        f"?format=json&per_page=200&date=1990:2024"
    )
    get(url, RAW / f"wb_{name}.json")
    print("wb", name, "ok")
    time.sleep(0.4)

# ---------------- NHL draft nationality, 2000-2025 ----------------
for year in range(2000, 2026):
    exp = urllib.parse.quote(f"draftYear={year}")
    url = f"https://records.nhl.com/site/api/draft?cayenneExp={exp}"
    get(url, RAW / f"nhl_draft_{year}.json")
    print("nhl", year, "ok")
    time.sleep(0.5)

# ---------------- Google Ngrams ----------------
# corpus 27 = American English 2019, corpus 28 = British English 2019
PAIRS = [
    ("toque,beanie", [27, 28]),
    ("washroom,restroom", [27, 28]),
    ("eh", [27, 28]),
    ("cheque", [27, 28]),
]
for words, corpora in PAIRS:
    for corpus in corpora:
        q = urllib.parse.quote(words)
        url = (
            "https://books.google.com/ngrams/json?content=" + q
            + f"&year_start=1960&year_end=2019&corpus={corpus}&smoothing=3"
        )
        slug = words.replace(",", "_").replace(" ", "")
        get(url, RAW / f"ngram_{slug}_corpus{corpus}.json")
        print("ngram", slug, corpus, "ok")
        time.sleep(0.5)

print("ALL FETCHES DONE")
