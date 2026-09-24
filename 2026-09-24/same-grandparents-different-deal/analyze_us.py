#!/usr/bin/env python3
"""Core analysis: US Asian-American outcomes (Census Reporter, ACS 2024 5-yr)
vs Chinese-Canadian outcomes (StatCan 2021 Census, filtered CSVs)."""
import json
from pathlib import Path

import pandas as pd

PROJ = Path("/home/hatch/workspace/passion-projects/2026-09-24/same-grandparents-different-deal")
RAW = PROJ / "data" / "raw"
OUT = PROJ / "data"
CHART = PROJ / "charts"

res = {}


def load(t, geo="01000US"):
    d = json.load(open(RAW / f"reporter_{t}_{'us' if geo=='01000US' else geo}.json"))
    tbl = d["tables"][t]
    labels = {c: v["name"] for c, v in tbl["columns"].items()}
    est = {k.replace("_", ""): v for k, v in d["data"][geo][t]["estimate"].items()}
    return labels, est


def s(v):
    return 0 if v is None else v


# ---------- median household income ----------
_, e = load("B19013D"); _, e0 = load("B19013")
res["us_median_hh_asian"] = e["B19013D001"]
res["us_median_hh_total"] = e0["B19013001"]

# ---------- education: bachelor's+ share, 25+ ----------
_, e = load("C15002D")
res["us_baplus_asian"] = (s(e["C15002D006"]) + s(e["C15002D011"])) / e["C15002D001"]
_, e0 = load("B15002")
ba = sum(s(e0[k]) for k in ["B15002015","B15002016","B15002017","B15002018",
                            "B15002032","B15002033","B15002034","B15002035"])
res["us_baplus_total"] = ba / e0["B15002001"]

# ---------- homeownership ----------
_, e = load("B25003D"); _, e0 = load("B25003")
res["us_homeown_asian"] = e["B25003D002"] / e["B25003D001"]
res["us_homeown_total"] = e0["B25003002"] / e0["B25003001"]

# ---------- employment: unemployment rate 16+ ----------
def unemp_rate(t):
    lab, e = load(t)
    un = emp = 0
    for k, l in lab.items():
        last = l.split(":")[0].strip().lower() if ":" not in l else l.rsplit(":", 1)[-1].strip().lower()
        # labels are like 'Male: 16 to 64 years: In labor force: Civilian: Employed'
        tail = l.rstrip(":").split(":")[-1].strip().lower()
        v = s(e[k])
        if tail == "unemployed":
            un += v
        elif tail == "employed":
            emp += v
    return un / (un + emp) if (un + emp) else None

res["us_unemp_asian"] = unemp_rate("C23002D")
res["us_unemp_total"] = unemp_rate("B23025")

# ---------- median earnings ----------
_, e = load("B20017D"); _, e0 = load("B20017")
res["us_medearn_asian"] = e["B20017D001"]
res["us_medearn_total"] = e0["B20017001"]

# ---------- nativity: foreign-born share ----------
def foreignborn(t):
    lab, e = load(t)
    fb = tot = 0
    for k, l in lab.items():
        tail = l.rstrip(":").split(":")[-1].strip().lower()
        v = s(e[k])
        if tail == "total":
            tot = v
        elif tail in ("naturalized u.s. citizen", "not a u.s. citizen"):
            fb += v
    return fb / tot if tot else None

res["us_foreignborn_asian"] = foreignborn("B05003D")
res["us_foreignborn_total"] = foreignborn("B05003")

# ---------- poverty ----------
lab, e = load("B17001D")
below = ptot = 0
for k, l in lab.items():
    ll = l.lower()
    v = s(e[k])
    if "below poverty" in ll:
        below += v
    if ll == "total:":
        ptot = v
res["us_poverty_asian"] = below / ptot if ptot else None
lab0, e0 = load("B17001")
below0 = ptot0 = 0
for k, l in lab0.items():
    ll = l.lower()
    v = s(e0[k])
    if "below poverty" in ll:
        below0 += v
    if ll == "total:":
        ptot0 = v
res["us_poverty_total"] = below0 / ptot0 if ptot0 else None

# ---------- occupation: management/business/science/arts share (white-collar proxy) ----------
def whitecollar(t):
    lab, e = load(t)
    wc = octot = 0
    for k, l in lab.items():
        tail = l.rstrip(":").split(":")[-1].strip().lower()
        v = s(e[k])
        if tail == "total":
            octot = v
        elif tail == "management, business, science, and arts occupations":
            wc += v
    return wc / octot if octot else None

res["us_whitecollar_asian"] = whitecollar("C24010D")
res["us_whitecollar_total"] = whitecollar("C24010")

# ---------- Chinese-alone population ----------
_, e = load("B02015")
res["us_chinese_pop"] = e["B02015002"] + e["B02015008"]  # Chinese except Taiwanese + Taiwanese
res["us_asian_pop"] = e["B02015001"]

json.dump(res, open(OUT / "us_indicators.json", "w"), indent=2)
for k, v in res.items():
    if isinstance(v, float) and v < 5:
        print(f"{k}: {v:.3f}")
    elif isinstance(v, float):
        print(f"{k}: {v:,.0f}")
    else:
        print(f"{k}: {v}")
