"""
05_atus.py - the diary trend, from ATUS respondent microdata.

BLS precomputes companion minutes on the respondent file (TRTALONE,
TRTFRIEND, TRTSPOUSE, TRTUNMPART, TRTCHILD, TRTFAMILY): minutes per day
with each companion, over the activities where "who was with you" is
collected (sleeping and personal care are excluded by design; companion
categories overlap, alone does not). This script builds
data/atus_respondent_extract.csv from the raw .dat files in data/raw/
(when present; BLS URLs in data/PROVENANCE.md), then weighted trend
tables, an "atus_diary" block in data/findings.json, and one chart.

Run after 02_analysis.py. Raw files are not committed (about 20 MB);
the committed extract reproduces every number here on its own.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RAW = os.path.join(DATA, "raw")
CH = os.path.join(HERE, "..", "charts")
YEARS = [2003, 2019, 2024]
COLS = ["TUYEAR", "TUDIARYDAY", "TRSPPRES", "TUFINLWGT", "TRTALONE",
        "TRTFRIEND", "TRTSPOUSE", "TRTUNMPART", "TRTCHILD", "TRTFAMILY"]

extract_path = os.path.join(DATA, "atus_respondent_extract.csv")
frames = []
raw_found = False
for y in YEARS:
    p = os.path.join(RAW, f"atusresp_{y}.dat")
    if os.path.exists(p):
        raw_found = True
        d = pd.read_csv(p, usecols=lambda c: c in COLS, low_memory=False)
        d["src_year"] = y
        frames.append(d[["src_year"] + COLS])
if raw_found:
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(extract_path, index=False)
    print(f"built extract from raw: {len(df):,} respondents")
else:
    df = pd.read_csv(extract_path)
    print(f"using committed extract: {len(df):,} respondents")

df["partner_min"] = df[["TRTSPOUSE", "TRTUNMPART"]].sum(axis=1)
df["partnered"] = np.where(df["TRSPPRES"].isin([1, 2]), "Partnered",
                           "No partner in household")
df["weekend"] = np.where(df["TUDIARYDAY"].isin([1, 7]), "Weekend", "Weekday")


def wm(g, c):
    g = g.dropna(subset=[c])
    return float(np.average(g[c], weights=g["TUFINLWGT"]))


def wshare(g, mask):
    return float(100 * np.average(mask[g.index], weights=g["TUFINLWGT"]))


rows = []
for y, g in df.groupby("src_year"):
    r = {"year": int(y), "n": int(len(g))}
    for c, lbl in [("TRTALONE", "alone_min"), ("TRTFRIEND", "friend_min"),
                   ("partner_min", "partner_min"), ("TRTCHILD", "child_min"),
                   ("TRTFAMILY", "family_min")]:
        r[lbl] = round(wm(g, c), 1)
    r["zero_friend_day_pct"] = round(wshare(g, g["TRTFRIEND"] == 0), 1)
    for seg_name, seg_col in [("partnered", "partnered"),
                              ("day", "weekend")]:
        for seg_val, gg in g.groupby(seg_col):
            r[f"friend_min_{seg_name}_{seg_val}"] = round(wm(gg, "TRTFRIEND"), 1)
            r[f"alone_min_{seg_name}_{seg_val}"] = round(wm(gg, "TRTALONE"), 1)
    rows.append(r)
trend = pd.DataFrame(rows)
trend.to_csv(os.path.join(DATA, "atus_trend.csv"), index=False)

t = trend.set_index("year")
A = {
    "friend_min": {str(y): float(t.loc[y, "friend_min"]) for y in YEARS},
    "alone_min": {str(y): float(t.loc[y, "alone_min"]) for y in YEARS},
    "partner_min": {str(y): float(t.loc[y, "partner_min"]) for y in YEARS},
    "child_min": {str(y): float(t.loc[y, "child_min"]) for y in YEARS},
    "zero_friend_day_pct": {str(y): float(t.loc[y, "zero_friend_day_pct"])
                            for y in YEARS},
    "friend_change_2003_2019_pct": round(100 * (t.loc[2019, "friend_min"] /
                                                t.loc[2003, "friend_min"] - 1), 1),
    "friend_change_2019_2024_pct": round(100 * (t.loc[2024, "friend_min"] /
                                                t.loc[2019, "friend_min"] - 1), 1),
    "friend_change_2003_2024_pct": round(100 * (t.loc[2024, "friend_min"] /
                                                t.loc[2003, "friend_min"] - 1), 1),
    "alone_change_2003_2024_min": round(t.loc[2024, "alone_min"] -
                                        t.loc[2003, "alone_min"], 1),
    "friend_min_singles": {str(y): float(t.loc[y, "friend_min_partnered_No partner in household"]) for y in YEARS},
    "friend_min_partnered": {str(y): float(t.loc[y, "friend_min_partnered_Partnered"]) for y in YEARS},
    "friend_min_weekend": {str(y): float(t.loc[y, "friend_min_day_Weekend"]) for y in YEARS},
    "friend_min_weekday": {str(y): float(t.loc[y, "friend_min_day_Weekday"]) for y in YEARS},
    "n_by_year": {str(y): int(t.loc[y, "n"]) for y in YEARS},
}
F = json.load(open(os.path.join(DATA, "findings.json")))
F["atus_diary"] = A
with open(os.path.join(DATA, "findings.json"), "w") as f:
    json.dump(F, f, indent=1)

# ------------------------------------------------------------ chart
plt.rcParams.update({"figure.dpi": 150, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25,
                     "grid.linestyle": "--"})
fig, axes = plt.subplots(1, 2, figsize=(9, 4.3))
ax = axes[0]
x = np.arange(3)
ax.bar(x - 0.2, trend.friend_min, width=0.4, color="#c0392b",
       label="With friends")
ax.bar(x + 0.2, trend.alone_min / 5, width=0.4, color="#1a1a2e",
       label="Alone (minutes / 5)")
for xi, v in zip(x - 0.2, trend.friend_min):
    ax.text(xi, v + 2, f"{v:.0f}", ha="center", fontsize=10,
            fontweight="bold")
for xi, v in zip(x + 0.2, trend.alone_min):
    ax.text(xi, v / 5 + 2, f"{v:.0f}", ha="center", fontsize=10)
ax.set_xticks(x, ["2003", "2019", "2024"])
ax.set_ylabel("Minutes per day (ATUS diaries)")
ax.set_title("Friend minutes: 60 -> 34 -> 26")
ax.legend(frameon=False, fontsize=8)
ax = axes[1]
ax.plot(trend.year, trend.zero_friend_day_pct, color="#c0392b", lw=2.4,
        marker="o")
for _, r in trend.iterrows():
    ax.annotate(f"{r.zero_friend_day_pct:.0f}%", (r.year, r.zero_friend_day_pct),
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=10, fontweight="bold")
ax.set_ylim(70, 93)
ax.set_ylabel("% of diary days with zero\nminutes with friends")
ax.set_title("The zero-friend day is now the normal day")
fig.tight_layout(); fig.savefig(f"{CH}/atus_trend.png"); plt.close(fig)
print(json.dumps(A, indent=1))
print("wrote atus_trend.csv, findings.json[atus_diary], charts/atus_trend.png")
