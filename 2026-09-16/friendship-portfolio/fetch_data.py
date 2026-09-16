#!/usr/bin/env python3
"""Download the raw public datasets used by the Friendship Portfolio project.

Sources (all open access):
  1. Our World in Data / Wellbeing Research Centre — "Self-reported life
     satisfaction" (Cantril ladder), country-year panel 2011-2025, sourced
     from the Gallup World Poll via the World Happiness Report.
     Grapher CSV endpoint (public, documented download API).
  2. All other datasets (AEI friendship survey, Meta-Gallup loneliness,
     WHR 2025 young-adult figures, Holt-Lunstad / Pantell mortality
     effect sizes) are transcribed from the published reports/papers and
     live in data/*.csv with per-row source citations — see SOURCES.md.
"""
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

CANTRIL_URL = (
    "https://ourworldindata.org/grapher/happiness-cantril-ladder.csv"
    "?csvType=full&useColumnShortNames=true"
)
CANTRIL_OUT = DATA / "cantril_ladder_owid.csv"

print("Downloading OWID Cantril ladder panel ...")
req = urllib.request.Request(CANTRIL_URL, headers={"User-Agent": "friendship-portfolio/1.0"})
with urllib.request.urlopen(req, timeout=60) as r, open(CANTRIL_OUT, "wb") as f:
    f.write(r.read())
print("saved ->", CANTRIL_OUT, f"({CANTRIL_OUT.stat().st_size/1024:.0f} KB)")
