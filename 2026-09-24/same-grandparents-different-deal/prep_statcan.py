#!/usr/bin/env python3
"""Stream-filter the giant StatCan census zips -> compact CSVs.

Reads CSV members directly from the zip (no 7GB extraction) and keeps only
the dimension slices needed for the analysis.
"""
import csv
import io
import zipfile
from pathlib import Path

PROJ = Path("/home/hatch/workspace/passion-projects/2026-09-24/same-grandparents-different-deal")
RAW = PROJ / "data" / "raw"
OUT = PROJ / "data"
OUT.mkdir(parents=True, exist_ok=True)

GEOS = ["Canada", "Ontario", "British Columbia", "Toronto (CMA), Ont.", "Vancouver (CMA), B.C."]


def stream_rows(zip_path, member):
    z = zipfile.ZipFile(zip_path)
    with z.open(member) as f:
        t = io.TextIOWrapper(f, encoding="utf-8-sig")
        reader = csv.DictReader(t)
        for row in reader:
            yield row


def vismin_cols(fieldnames):
    """Return {group_name: value_col} for visible-minority wide columns."""
    out = {}
    for c in fieldnames:
        if c.startswith("Visible minority (15):") and not c.endswith("Symbol"):
            grp = c.split(":", 1)[1]
            out[grp] = c
    return out


def num(s):
    s = (s or "").strip()
    if s in ("", "..", "...", "x", "F", "E"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------- 98100331: visible minority x income ----------------
def filter_income():
    zp = RAW / "statcan_98100331_vismin_income_genstatus.zip"
    if not zp.exists():
        print("income zip missing, skip")
        return
    gens = ["Total - Generation status", "First generation", "Second generation",
            "Third generation or more"]
    edus = ["Total - Highest certificate, diploma or degree", "Bachelor’s degree or higher"]
    ages = ["Total - Age", "25 to 54 years"]
    genders = ["Total - Gender", "Men+", "Women+"]
    incstats = ["Total - Income statistics", "Median total income ($)", "Average total income ($)",
                "Median after-tax income ($)", "Median employment income ($)",
                "Average employment income ($)", "Median wages, salaries and commissions ($)"]
    rows = stream_rows(zp, "98100331.csv")
    first = next(rows)

    def keep(r):
        return (r["GEO"] in GEOS and r["Generation status (4)"] in gens
                and r["Highest certificate, diploma or degree (16)"] in edus
                and r["Age (15B)"] in ages and r["Gender (3)"] in genders
                and r["Income statistics (17)"] in incstats)

    vcols = vismin_cols(first.keys())
    kept = [r for r in rows if keep(r)]
    kept.insert(0, first)
    # write compact
    dimcols = ["GEO", "Generation status (4)", "Highest certificate, diploma or degree (16)",
               "Age (15B)", "Gender (3)", "Income statistics (17)"]
    with open(OUT / "statcan_income_filtered.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(dimcols + sorted(vcols))
        for r in kept:
            w.writerow([r[c] for c in dimcols] + [num(r[vcols[g]]) for g in sorted(vcols)])
    print(f"income: {len(kept)} rows -> statcan_income_filtered.csv")


if __name__ == "__main__":
    filter_income()
