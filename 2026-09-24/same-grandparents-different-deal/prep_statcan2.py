#!/usr/bin/env python3
"""Stream-filter StatCan zips -> compact CSVs (part 2: mother tongue, low income,
employment income by year, occupation)."""
import csv
import io
import zipfile
from pathlib import Path

PROJ = Path("/home/hatch/workspace/passion-projects/2026-09-24/same-grandparents-different-deal")
RAW = PROJ / "data" / "raw"
OUT = PROJ / "data"


def stream_rows(zip_path, member):
    z = zipfile.ZipFile(zip_path)
    with z.open(member) as f:
        t = io.TextIOWrapper(f, encoding="utf-8-sig")
        reader = csv.DictReader(t)
        for row in reader:
            yield row


def num(s):
    s = (s or "").strip()
    if s in ("", "..", "...", "x", "F"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def vismin_cols_wide(fieldnames, prefix="Visible minority (15):"):
    out = {}
    for c in fieldnames:
        if c.startswith(prefix) and not c.endswith("Symbol"):
            out[c.split(":", 1)[1]] = c
    return out


# ---------------- mother tongue (long format) ----------------
def filter_mothertongue():
    zp = RAW / "statcan_98100325_vismin_mothertongue_genstatus.zip"
    if not zp.exists():
        print("mothertongue zip missing"); return
    mts = ["Total - Mother tongue", "Mandarin", "Yue (Cantonese)", "Chinese, n.o.s.",
           "Chinese languages", "English", "French"]
    vms = ["Chinese", "Total - Visible minority", "Not a visible minority"]
    gens = ["Total - Generation status", "First generation", "Second generation",
            "Third generation or more"]
    ages = ["Total - Age", "25 to 54 years"]
    total_c = "Single and multiple mother tongue responses (3):Total - Single and multiple mother tongue responses[1]"
    single_c = "Single and multiple mother tongue responses (3):Single mother tongue responses[2]"
    kept = []
    for r in stream_rows(zp, "98100325.csv"):
        if (r["GEO"] == "Canada" and r["Visible minority (15)"] in vms
                and r["Generation status (4)"] in gens and r["Age (15C)"] in ages
                and r["Gender (3)"] == "Total - Gender" and r["Statistics (3)"] == "Count"
                and r["Mother tongue (234)"] in mts):
            kept.append(r)
    with open(OUT / "statcan_mothertongue_filtered.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vismin", "generation", "age", "mother_tongue", "total", "single"])
        for r in kept:
            w.writerow([r["Visible minority (15)"], r["Generation status (4)"], r["Age (15C)"],
                        r["Mother tongue (234)"], num(r[total_c]), num(r[single_c])])
    print(f"mothertongue: {len(kept)} rows")


# ---------------- low income (wide = generation) ----------------
def filter_lowincome():
    zp = RAW / "statcan_98100332_vismin_lowincome_genstatus.zip"
    if not zp.exists():
        print("lowincome zip missing"); return
    vms = ["Chinese", "Total - Visible minority", "Not a visible minority"]
    stats = ["Total - Individual low-income status based on low-income measure, after tax (LIM-AT)",
             "In low income (LIM-AT)", "Not in low income (LIM-AT)",
             "Prevalence of low income (LIM-AT) (%)"]
    gen_cols = [c for c in
                ["Generation status (4):Total - Generation status[1]",
                 "Generation status (4):First generation[2]",
                 "Generation status (4):Second generation[3]",
                 "Generation status (4):Third generation or more[4]"]]
    kept = []
    for r in stream_rows(zp, "98100332.csv"):
        if (r["GEO"] == "Canada" and r["Visible minority (15)"] in vms
                and r["Age (15C)"] == "Total - Age" and r["Gender (3)"] == "Total - Gender"
                and r["Statistics (3)"] == "Count"
                and r["Individual low-income status (8)"] in stats):
            kept.append(r)
    with open(OUT / "statcan_lowincome_filtered.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vismin", "status", "gen_total", "gen_first", "gen_second", "gen_thirdplus"])
        for r in kept:
            w.writerow([r["Visible minority (15)"], r["Individual low-income status (8)"][:60]]
                       + [num(r[c]) for c in gen_cols])
    print(f"lowincome: {len(kept)} rows")


# ---------------- employment income by census year (wide = year) ----------------
def filter_empyears():
    zp = RAW / "statcan_98100642_vismin_employment_income_by_year.zip"
    if not zp.exists():
        print("empyears zip missing"); return
    vms = ["Chinese", "Total - Visible minority", "Not a visible minority"]
    immgens = ["Total – Immigrant and generation status", "Non-immigrants", "Immigrants",
               "First generation", "Second generation", "Third generation or more"]
    edus = ["Total - Highest certificate, diploma or degree", "Bachelor’s degree or higher"]
    year_cols = ["Census year (4):2021[1]", "Census year (4):2016[2]",
                 "Census year (4):2011[3]", "Census year (4):2006[4]"]
    kept = []
    for r in stream_rows(zp, "98100642.csv"):
        if (r["GEO"] == "Canada" and r["Visible minority (15)"] in vms
                and r["Immigrant and generation status (9)"] in immgens
                and r["Highest certificate, diploma or degree (6A)"] in edus
                and r["Gender (3a)"] == "Total - Gender"
                and r["Age and first official language spoken (17)"] == "Total - Age"
                and r["Employment income (2)"] in ["Average employment income ($)",
                                                   "Median employment income ($)"]):
            kept.append(r)
    with open(OUT / "statcan_empincome_years_filtered.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vismin", "immgen", "education", "income_stat", "y2021", "y2016", "y2011", "y2006"])
        for r in kept:
            w.writerow([r["Visible minority (15)"], r["Immigrant and generation status (9)"],
                        r["Highest certificate, diploma or degree (6A)"],
                        r["Employment income (2)"]] + [num(r[c]) for c in year_cols])
    print(f"empyears: {len(kept)} rows")


# ---------------- occupation: management + tech broad cats ----------------
def filter_occupation():
    zp = RAW / "statcan_98100330_vismin_occupation_education_genstatus.zip"
    if not zp.exists():
        print("occupation zip missing"); return
    rows = stream_rows(zp, "98100330.csv")
    first = next(rows)
    vcols = vismin_cols_wide(first.keys())
    assert "Chinese[4]" in vcols and "Total - Visible minority[1]" in vcols \
        and "Not a visible minority[15]" in vcols, sorted(vcols)
    occ_col = [c for c in first.keys() if "ccupation" in c][0]
    mgmt2 = ("10", "20", "30", "50", "60", "70", "80", "90")

    def kind_of(occ):
        if occ.startswith("0 Legislative and senior management"):
            return "mgmt"
        if len(occ) > 3 and occ[:2] in mgmt2 and occ[2] == " ":
            return "mgmt"
        if occ.startswith("2 Natural and applied sciences and related occupations"):
            return "tech_broad"
        if occ.startswith("21 Professional occupations in natural and applied sciences"):
            return "tech_prof"
        if len(occ) > 2 and occ[0].isdigit() and occ[1] == " ":
            return "broad"  # single-digit broad category -> denominator
        return None

    kept = []
    for r in rows:
        k = kind_of(r[occ_col])
        if k is None:
            continue
        if (r["GEO"] == "Canada" and r["Generation status (4)"] in
                ["Total - Generation status", "First generation", "Second generation"]
                and r["Highest certificate, diploma or degree (15)"] in
                ["Total - Highest certificate, diploma or degree", "Bachelor’s degree or higher"]
                and r["Age (8C)"] in ["Total - Age", "25 to 34 years", "35 to 44 years", "45 to 54 years"]
                and r["Gender (3)"] == "Total - Gender" and r["Statistics (3)"] == "Count"):
            kept.append((r[occ_col][:75], k, r))
    with open(OUT / "statcan_occupation_filtered.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["generation", "education", "age", "occupation", "kind",
                    "chinese", "total_pop", "not_vismin"])
        for occ, k, r in kept:
            w.writerow([r["Generation status (4)"],
                        r["Highest certificate, diploma or degree (15)"], r["Age (8C)"],
                        occ, k, num(r[vcols["Chinese[4]"]]),
                        num(r[vcols["Total - Visible minority[1]"]]),
                        num(r[vcols["Not a visible minority[15]"]])])
    print(f"occupation: {len(kept)} rows")


if __name__ == "__main__":
    filter_mothertongue()
    filter_lowincome()
    filter_empyears()
    filter_occupation()
