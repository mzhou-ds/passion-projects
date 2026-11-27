"""01_parse_bv.py — Parse the Ricos 2014 biological variation table (Westgard mirror)
into a tidy CSV, and verify the CVi/CVg values used in markers.csv.

Input : data/ricos_2014_bv_database_westgard.html (saved 2026-11-27)
Output: output/ricos_bv.csv (all analytes) + verification lines on stdout.
"""
import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "data" / "ricos_2014_bv_database_westgard.html"
OUT = ROOT / "output" / "ricos_bv.csv"

tables = pd.read_html(str(HTML), flavor="lxml")
print(f"{len(tables)} tables found")
rows = []
for t in tables:
    if t.shape[1] != 8:
        continue
    # Layout: col0 = matrix prefix (S-, P-, B-...), col1 = analyte, col2 = papers,
    # col3 = CVI, col4 = CVg, col5 = I(%), col6 = B(%), col7 = TE(%); rows 0-1 are headers.
    for _, r in t.iloc[2:].iterrows():
        prefix = str(r.iloc[0]).strip()
        name = str(r.iloc[1]).strip()
        if name.lower() in ("analyte", "nan", "") or prefix == "nan":
            continue
        try:
            cvi = float(str(r.iloc[3]).replace(",", "."))
            cvg_raw = str(r.iloc[4]).strip()
            cvg = float(cvg_raw.replace(",", ".")) if cvg_raw not in ("---", "nan", "") else None
            papers = str(r.iloc[2]).strip()
        except (ValueError, TypeError):
            continue
        rows.append({"analyte": f"{prefix} {name}", "n_papers": papers,
                     "cvi_pct": cvi, "cvg_pct": cvg})

df = pd.DataFrame(rows).drop_duplicates(subset=["analyte"])
df.to_csv(OUT, index=False)
print(f"wrote {len(df)} analytes to {OUT}")

# Verification: the markers we use from Ricos must match markers.csv,
# except where markers.csv deliberately uses a newer EFLM value (expected_overrides).
markers = pd.read_csv(ROOT / "data" / "markers.csv", comment="#")
expected_overrides = {"hsCRP": "EFLM 2021 meta 58.9 (Ricos 49.7)"}
lookup = {
    "S- C reactive protein - high sensitivity": "hsCRP",
    "S- Insulin": "Fasting insulin",
    "S- Triglyceride": "Triglycerides",
    "S- Thyroid stimulating hormone (TSH)": "TSH",
    "S- Lipoprotein (a)": "Lipoprotein(a)",
    "S- Ferritin": "Ferritin (men)",
    "S- Sex hormone binding globulin (SHBG)": "SHBG",
    "S- Testosterone": "Total testosterone (men)",
    "P- Homocysteine": "Homocysteine",
    "S- LDL Cholesterol": "LDL cholesterol",
    "S- Apolipoprotein B": "Apolipoprotein B",
    "S- Glucose": "Fasting glucose",
    "B- Hemoglobin A1 C": "HbA1c",
}
ok = True
smap = dict(zip(df["analyte"], zip(df["cvi_pct"], df["cvg_pct"])))
for key, mine in lookup.items():
    if key not in smap:
        print(f"MISSING in Ricos table: {key}")
        ok = False
        continue
    cvi, cvg = smap[key]
    row = markers[markers["marker"] == mine].iloc[0]
    if mine in expected_overrides:
        print(f"{mine:32s} Ricos CVi={cvi:6.2f} CVg={cvg}  markers.csv CVi={row['cvi_pct']}  (expected override: {expected_overrides[mine]})")
        continue
    flag = "" if abs(cvi - row["cvi_pct"]) < 0.01 else "  <-- MISMATCH"
    if flag:
        ok = False
    print(f"{mine:32s} Ricos CVi={cvi:6.2f} CVg={cvg}  markers.csv CVi={row['cvi_pct']}{flag}")
print("VERIFICATION:", "PASS" if ok else "FAIL — check mismatches above")
