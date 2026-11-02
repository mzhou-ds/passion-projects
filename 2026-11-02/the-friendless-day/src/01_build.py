"""The Friendless Day - per-respondent-day companion minutes from ATUS 2003-2025 (vectorized).

Question: when friend time fell, did everyone lose a little (thinning) or did a
growing share of people lose the whole day (going to zero)? Is that pattern
unique to friendship, or do family and spouse/partner show it too?

Data: BLS ATUS multi-year microdata 2003-2025, cached from the 2026-10-27 build.
One diary day per respondent, weighted by TUFINLWGT. "Who" is not asked for
sleeping, personal care, or work, so minutes are inside who-eligible activities;
a "friend day" = at least one friend episode. 2020 excluded (collection break).
Who codes: 18/19 alone, 20 spouse, 21 unmarried partner, 22 own hh child,
23 grandchild, 24 parent, 25 brother/sister, 26 other related, 27 foster child,
40 own nonhh child <18, 51 parents (nonhh), 52/53 other nonhh family, 54 friends.
Episodes can carry several codes, so companion minutes overlap like BLS TRT*.
"""
import glob, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = pathlib.Path.home() / "workspace/passion-projects/2026-10-27/the-friend-workout-died/data/raw"
OUT = ROOT / "data"; OUT.mkdir(exist_ok=True)
ERAS = [(2003, 2007, "2003-07"), (2008, 2012, "2008-12"),
        (2013, 2019, "2013-19"), (2021, 2025, "2021-25")]
def era_of(y):
    for lo, hi, lab in ERAS:
        if lo <= y <= hi: return lab
    return None
def find(pat):
    hits = sorted(glob.glob(str(RAW / pat))); assert hits, f"missing {pat}"
    return hits[0]

act = pd.read_csv(find("atusact*.dat"), usecols=["TUCASEID", "TUACTIVITY_N",
    "TUACTDUR", "TUSTARTTIM", "TEWHERE"], low_memory=False)
who = pd.read_csv(find("atuswho*.dat"), usecols=["TUCASEID", "TUACTIVITY_N", "TUWHO_CODE"])
resp = pd.read_csv(find("atusresp*.dat"), usecols=["TUCASEID", "TULINENO", "TUYEAR",
    "TUDIARYDAY", "TUFNWGTP", "TEHRUSL1", "TRHHCHILD", "TRCHILDNUM", "TRNUMHOU",
    "TESPEMPNOT", "TRSPPRES", "TEHRFTPT", "TELFS"], low_memory=False)
rost = pd.read_csv(find("atusrost*.dat"), usecols=["TUCASEID", "TULINENO", "TEAGE", "TESEX"])
for df in (act, who, resp, rost): df.columns = [c.upper() for c in df.columns]
resp = resp.rename(columns={"TUFNWGTP": "TUFINLWGT"})
resp = resp.merge(rost, on=["TUCASEID", "TULINENO"], how="left")

w = who[who["TUWHO_CODE"] > 0].copy()
w["alone"] = w["TUWHO_CODE"].isin([18, 19]).astype(np.int8)
w["friend"] = (w["TUWHO_CODE"] == 54).astype(np.int8)
w["partner"] = w["TUWHO_CODE"].isin([20, 21]).astype(np.int8)
w["family"] = w["TUWHO_CODE"].isin([22, 23, 24, 25, 26, 27, 40, 51, 52, 53]).astype(np.int8)
w["sibling"] = (w["TUWHO_CODE"] == 25).astype(np.int8)
w["parent"] = w["TUWHO_CODE"].isin([24, 51]).astype(np.int8)
w["child"] = w["TUWHO_CODE"].isin([22, 40]).astype(np.int8)
w["alone_only"] = w["alone"]  # alone episodes carry only 18/19 by construction
comp = w.groupby(["TUCASEID", "TUACTIVITY_N"])[["alone", "friend", "partner",
    "family", "sibling", "parent", "child"]].max().reset_index()
comp["alone"] = comp["alone"] & (comp[["friend", "partner", "family"]].sum(axis=1) == 0)

ep = act.merge(comp, on=["TUCASEID", "TUACTIVITY_N"], how="left")
n_act, n_who = len(act), int(ep["alone"].notna().sum())
ep = ep[ep["alone"].notna()].copy()
ep["hour"] = pd.to_datetime(ep["TUSTARTTIM"], format="%H:%M:%S", errors="coerce").dt.hour
ep["at_home"] = (ep["TEWHERE"] == 1).astype(np.int8)
for f in ["alone", "friend", "partner", "family", "sibling", "parent", "child"]:
    ep[f + "_min"] = ep["TUACTDUR"] * ep[f]
    ep[f + "_ep"] = ep[f].astype(np.int8)
ep["eligible_min"] = ep["TUACTDUR"]
ep["friend_home_min"] = ep["TUACTDUR"] * ep["friend"] * ep["at_home"]
ep["friend_away_min"] = ep["TUACTDUR"] * ep["friend"] * (1 - ep["at_home"])
ep["friend_home_ep"] = ep["friend"] * ep["at_home"]
ep["friend_away_ep"] = ep["friend"] * (1 - ep["at_home"])
aggcols = ["friend_min", "family_min", "partner_min", "sibling_min", "parent_min",
    "child_min", "alone_min", "eligible_min", "friend_ep", "friend_home_min",
    "friend_away_min", "friend_home_ep", "friend_away_ep"]
day = ep.groupby("TUCASEID")[aggcols].sum().reset_index()
day = day.merge(resp, on="TUCASEID", how="left")
day = day[day["TUYEAR"] != 2020].copy()
day["era"] = day["TUYEAR"].apply(era_of)
day = day[day["era"].notna()].copy()
day["weekend"] = day["TUDIARYDAY"].isin([1, 7])
day["ageband"] = pd.cut(day["TEAGE"], [14, 24, 34, 44, 54, 64, 120],
                         labels=["15-24", "25-34", "35-44", "45-54", "55-64", "65+"])
day["has_kids_hh"] = day["TRHHCHILD"] == 1
day["spouse_in_hh"] = day["TRSPPRES"] == 1
day.to_parquet(OUT / "respondent_day.parquet", index=False)
day[["TUCASEID", "TUYEAR", "era", "TEAGE", "ageband", "TESEX", "weekend", "TUFINLWGT",
    "friend_min", "family_min", "partner_min", "sibling_min", "alone_min",
    "eligible_min", "friend_ep", "friend_home_min", "friend_away_min",
    "has_kids_hh", "spouse_in_hh", "TRNUMHOU", "TEHRUSL1", "TELFS"]].to_csv(
    OUT / "respondent_day.csv", index=False)

ep2 = ep[ep["friend"] == 1].merge(resp[["TUCASEID", "TUYEAR", "TUFINLWGT"]],
    on="TUCASEID", how="left")
ep2 = ep2[ep2["TUYEAR"] != 2020].copy()
ep2["era"] = ep2["TUYEAR"].apply(era_of)
ep2 = ep2[ep2["era"].notna()].copy()
ep2["wmin"] = ep2["TUACTDUR"] * ep2["TUFINLWGT"]
ep2.groupby(["era", "hour"])["wmin"].sum().reset_index().to_csv(
    OUT / "friend_minutes_by_hour.csv", index=False)

def wm(d, c):
    return float(np.average(d[c], weights=d["TUFINLWGT"]))
def wshare(d, mask):
    return float(d.loc[mask, "TUFINLWGT"].sum() / d["TUFINLWGT"].sum())

R = {"n_respondents": int(day["TUCASEID"].nunique()),
     "n_episodes_with_who": n_who, "n_episodes_total": n_act,
     "coverage_pct": round(100 * n_who / n_act, 1),
     "mean_eligible_min": round(wm(day, "eligible_min"), 1)}
for col, lbl in [("friend_min", "friend"), ("family_min", "family"),
                 ("partner_min", "partner"), ("sibling_min", "sibling"),
                 ("alone_min", "alone")]:
    rows = []
    for lab in [e[2] for e in ERAS]:
        d = day[day["era"] == lab]; pos = d[d[col] > 0]
        rows.append({"era": lab, "n": int(len(d)),
            "mean_min": round(wm(d, col), 1),
            "zero_share_pct": round(100 * wshare(d, d[col] == 0), 1),
            "mean_if_positive": round(wm(pos, col), 1) if len(pos) else None,
            "median_if_positive": round(float(np.median(pos[col])), 1) if len(pos) else None,
            "brief_share_of_positive_pct": round(100 * wshare(pos, pos[col] < 30), 1) if len(pos) else None,
            "long_share_of_positive_pct": round(100 * wshare(pos, pos[col] >= 120), 1) if len(pos) else None})
    R[lbl] = rows
    a, b = rows[0], rows[-1]
    pa, pb = 1 - a["zero_share_pct"] / 100, 1 - b["zero_share_pct"] / 100
    R[lbl + "_decomp"] = {"delta_mean": round(b["mean_min"] - a["mean_min"], 1),
        "extensive": round((pb - pa) * a["mean_if_positive"], 1),
        "intensive": round(pb * (b["mean_if_positive"] - a["mean_if_positive"]), 1)}

buck = []
for lab in [e[2] for e in ERAS]:
    d = day[day["era"] == lab]
    buck.append({"era": lab,
        "zero": round(100 * wshare(d, d["friend_min"] == 0), 1),
        "1-29": round(100 * wshare(d, (d["friend_min"] > 0) & (d["friend_min"] < 30)), 1),
        "30-119": round(100 * wshare(d, (d["friend_min"] >= 30) & (d["friend_min"] < 120)), 1),
        "120+": round(100 * wshare(d, d["friend_min"] >= 120), 1)})
R["friend_buckets"] = buck

zf = []
for lab in [e[2] for e in ERAS]:
    for ab, d in day[day["era"] == lab].groupby("ageband", observed=True):
        zf.append({"era": lab, "ageband": str(ab), "n": int(len(d)),
            "zero_friend_pct": round(100 * wshare(d, d["friend_min"] == 0), 1),
            "friend_mean": round(wm(d, "friend_min"), 1),
            "zero_family_pct": round(100 * wshare(d, d["family_min"] == 0), 1)})
R["zero_by_age"] = zf
sub = []
for name, col in [("weekend", "weekend"), ("has_kids_hh", "has_kids_hh"), ("spouse_in_hh", "spouse_in_hh")]:
    for lab in ["2003-07", "2021-25"]:
        for val, d in day[day["era"] == lab].groupby(col):
            sub.append({"group": name, "value": bool(val), "era": lab, "n": int(len(d)),
                "zero_friend_pct": round(100 * wshare(d, d["friend_min"] == 0), 1),
                "friend_mean": round(wm(d, "friend_min"), 1)})
R["zero_by_subgroup"] = sub
loc = []
for lab in [e[2] for e in ERAS]:
    d = day[day["era"] == lab]; f = d[d["friend_min"] > 0]
    loc.append({"era": lab,
        "home_share_of_friend_min_pct": round(100 * (d["friend_home_min"] * d["TUFINLWGT"]).sum() /
            max(1, (d["friend_min"] * d["TUFINLWGT"]).sum()), 1),
        "home_only_share_of_friend_days_pct": round(100 * wshare(f, f["friend_away_ep"] == 0), 1),
        "away_only_share_of_friend_days_pct": round(100 * wshare(f, f["friend_home_ep"] == 0), 1)})
R["location"] = loc
sib = []
for lab in [e[2] for e in ERAS]:
    for ab, d in day[day["era"] == lab].groupby("ageband", observed=True):
        sib.append({"era": lab, "ageband": str(ab), "n": int(len(d)),
            "sibling_mean": round(wm(d, "sibling_min"), 1),
            "any_sibling_pct": round(100 * wshare(d, d["sibling_min"] > 0), 1)})
R["sibling_by_age"] = sib
ys = []
for y, d in day.groupby("TUYEAR"):
    ys.append({"year": int(y), "n": int(len(d)),
        "zero_friend_pct": round(100 * wshare(d, d["friend_min"] == 0), 1),
        "friend_mean": round(wm(d, "friend_min"), 1),
        "zero_family_pct": round(100 * wshare(d, d["family_min"] == 0), 1)})
R["yearly"] = ys
json.dump(R, open(OUT / "results.json", "w"), indent=1)
print("respondents:", R["n_respondents"], "coverage:", R["coverage_pct"], "eligible:", R["mean_eligible_min"])
for lbl in ["friend", "family", "partner"]:
    print(lbl, R[lbl][0], R[lbl][-1], R[lbl + "_decomp"])
print("buckets:", R["friend_buckets"])
print("location:", R["location"])
