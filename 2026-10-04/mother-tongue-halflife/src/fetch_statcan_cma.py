#!/usr/bin/env python3
"""Stream-filter StatCan 2021 Census table 98-10-0325-01 (visible minority x
generation status x mother tongue) from the full-table zip -> compact CSV for
Canada + selected CMAs. Zip courtesy of the 2026-09-24 build's raw archive;
for a fresh download: https://www150.statcan.gc.ca/n1/tbl/csv/98100325-eng.zip
"""
import csv, io, zipfile
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
ZIP = Path.home() / "workspace/passion-projects/2026-09-24/same-grandparents-different-deal/data/raw/statcan_98100325_vismin_mothertongue_genstatus.zip"
OUT = PROJ / "data" / "statcan_cma_mothertongue.csv"

TARGET_GEO = ("Canada", "Toronto", "Vancouver", "Montr", "Calgary", "Edmonton", "Ottawa", "Winnipeg")
MTS = {"Total - Mother tongue", "Mandarin", "Yue (Cantonese)", "Chinese, n.o.s.", "Chinese languages", "English"}
VMS = {"Chinese", "Total - Visible minority"}
GENS = {"Total - Generation status", "First generation", "Second generation", "Third generation or more"}
AGES = lambda a: a == "Total - Age" or a.startswith(("0 to 14", "15 to 24", "25 to 54", "55 years"))

TOTAL_C = "Single and multiple mother tongue responses (3):Total - Single and multiple mother tongue responses[1]"
SINGLE_C = "Single and multiple mother tongue responses (3):Single mother tongue responses[2]"

rows, geos = [], set()
z = zipfile.ZipFile(ZIP)
with z.open("98100325.csv") as f:
    r = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
    for row in r:
        geo = row["GEO"]
        if not (geo == "Canada" or (row["DGUID"].startswith("2021S0503") and any(t in geo for t in TARGET_GEO))):
            continue
        if (row["Visible minority (15)"] in VMS and row["Generation status (4)"] in GENS
                and AGES(row["Age (15C)"]) and row["Gender (3)"] == "Total - Gender"
                and row["Statistics (3)"] == "Count" and row["Mother tongue (234)"] in MTS):
            geos.add(geo)
            rows.append({"geo": geo, "vismin": row["Visible minority (15)"], "generation": row["Generation status (4)"],
                         "age": row["Age (15C)"], "mother_tongue": row["Mother tongue (234)"],
                         "total": row[TOTAL_C], "single": row[SINGLE_C]})
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"wrote {len(rows)} rows; geos={sorted(geos)}")
