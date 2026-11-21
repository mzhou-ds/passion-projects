"""Stratified uniform sample of Discogs releases, with exact inclusion weights.

Problem: Discogs search caps at 10,000 accessible results per query, and the
default ordering is popularity-graded (median `have` falls 74 -> 13 -> 7 from
page 1 to page 100), so naive deep paging is both capped and biased.

Solution: partition each (genre, year) cohort into small leaf cells via
recursive splitting (style -> format -> file-description -> country) until
every leaf total is <= 10,000, then sample one random page (100 records)
per leaf. A release's inclusion probability is computed exactly from the
leaf cells whose filters it matches (a record lists all its styles, formats
and descriptions, so membership is observable), giving Horvitz-Thompson
weights for population estimates.

Counts are fetched with per_page=1 (pagination total). All requests paced
~1.2s (unauthenticated limit 60/min) with 429 backoff. Everything is saved
incrementally: per-cohort sample JSON + a cells manifest for weights.
"""
import json
import math
import os
import random
import time

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "raw")
BASE = "https://api.discogs.com/database/search"
HEADERS = {"User-Agent": "MusingWithMike/1.0 (research; contact: michaelzhou96@gmail.com)"}
SEED = 20261121
PER_PAGE = 100
CAP = 10000

STYLES = ["House", "Techno", "Trance", "Drum & Bass", "Electro", "Ambient",
          "Downtempo", "Dubstep", "Progressive House", "Tech House", "Minimal",
          "Deep House", "Hardcore", "Breakbeat", "IDM", "Disco", "Tribal",
          "Psy-Trance", "Garage", "Jungle", "Eurodance", "Experimental",
          "Trip Hop", "Acid", "Acid House", "Big Beat", "Breakcore", "Breaks",
          "Chiptune", "Dub", "Electroclash", "Euro House", "Eurobeat",
          "Footwork", "Gabber", "Goa Trance", "Grime", "Happy Hardcore",
          "Hard House", "Hard Techno", "Hardstyle", "Hi-NRG", "Italo-Disco",
          "Juke", "Leftfield", "Makina", "Moombahton", "New Beat", "Noise",
          "Nu-Disco", "Progressive Breaks", "Progressive Trance", "Rave",
          "Speed Garage", "Speedcore", "Synth-pop", "Synthwave", "Tribal House",
          "UK Garage", "Vaporwave", "Witch House", "Future Jazz", "Bassline",
          "Ghettotech", "Jersey Club", "Baltimore Club", "Dungeon Synth",
          "Power Electronics", "Disco Polo"]
FORMATS = ["Vinyl", "File", "CD", "CDr", "Cassette"]
FILE_DESCS = ["MP3", "WAV", "FLAC", "AIFF"]
COUNTRIES = ["UK", "US", "Germany", "Netherlands", "France", "Italy", "Spain",
             "Belgium", "Canada", "Unknown"]

# (genre, year, use_style_strata)
# NOTE: rock/pop control cohorts were dropped 2026-11-21: their
# (format x country) cells exceed Discogs' 10,000-result cap (rock Vinyl x
# US 2020 alone is >10k) and cannot be split further at the country stage.
COHORTS = [
    ("electronic", 2005, True), ("electronic", 2015, True),
    ("electronic", 2025, True),
]


def get_total(params, tries=0):
    p = dict(params, type="release", per_page=1)
    r = requests.get(BASE, params=p, headers=HEADERS, timeout=30)
    if r.status_code == 429 and tries < 5:
        wait = int(r.headers.get("Retry-After", 60))
        print(f"429, waiting {wait}s", flush=True)
        time.sleep(wait + 2)
        return get_total(params, tries + 1)
    r.raise_for_status()
    return r.json()["pagination"]["items"]


def fetch_page(params, page, tries=0):
    p = dict(params, type="release", per_page=PER_PAGE, page=page)
    r = requests.get(BASE, params=p, headers=HEADERS, timeout=30)
    if r.status_code == 429 and tries < 5:
        wait = int(r.headers.get("Retry-After", 60))
        print(f"429, waiting {wait}s", flush=True)
        time.sleep(wait + 2)
        return fetch_page(params, page, tries + 1)
    r.raise_for_status()
    return r.json()["results"]


def resolve_cells(genre, year, use_styles):
    """Return list of leaf cells: each is (filters dict, total)."""
    leaves = []

    def split(params, stage):
        total = get_total(params)
        time.sleep(1.1)
        if total == 0:
            return
        if total <= CAP or stage >= 4:
            leaves.append((dict(params), total))
            if total > CAP:
                print(f"WARNING leaf over cap: {params} total={total:,}",
                      flush=True)
            return
        if stage == 0:
            dims = [("style", s) for s in STYLES]
        elif stage == 1:
            dims = [("format", f) for f in FORMATS]
        elif stage == 2:
            if params.get("format") == "File":
                dims = [("format", f) for f in FILE_DESCS]
            else:
                dims = [("country", c) for c in COUNTRIES]
        else:  # stage == 3
            if "country" in params:
                leaves.append((dict(params), total))
                return
            dims = [("country", c) for c in COUNTRIES]
        for k, v in dims:
            split(dict(params, **{k: v}), stage + 1)

    split({"genre": genre, "year": year}, 0 if use_styles else 1)
    return leaves


def main():
    rng = random.Random(SEED)
    manifest_path = os.path.join(DATA_DIR, "sample_cells.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    for genre, year, use_styles in COHORTS:
        key = f"{genre}_{year}"
        out = os.path.join(DATA_DIR, f"sample_{key}.json")
        if os.path.exists(out):
            print(f"skip {key} (exists)", flush=True)
            continue
        print(f"== resolving cells {key} ==", flush=True)
        leaves = resolve_cells(genre, year, use_styles)
        print(f"{key}: {len(leaves)} leaf cells, "
              f"frame total {sum(t for _, t in leaves):,}", flush=True)
        records = []
        cells_meta = []
        for params, total in leaves:
            npages = math.ceil(total / PER_PAGE)
            page = rng.randint(1, npages)
            try:
                res = fetch_page(params, page)
            except Exception as e:
                print(f"FAIL {key} {params} p{page}: {e}", flush=True)
                raise
            records.extend(res)
            cells_meta.append({"filters": params, "total": total,
                               "page": page, "n": len(res)})
            print(f"{key} {params} total={total:,} page={page} n={len(res)}",
                  flush=True)
            time.sleep(1.1)
        json.dump({"genre": genre, "year": year, "n": len(records),
                   "cells": cells_meta, "results": records}, open(out, "w"))
        manifest[key] = cells_meta
        json.dump(manifest, open(manifest_path, "w"), indent=1)
        print(f"saved {key}: {len(records)} records", flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
