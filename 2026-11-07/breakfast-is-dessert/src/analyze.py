"""Core analysis for build #61: is breakfast sweeter than a snack?

Primary population: day 1, reliable recall, age 20-79, day kcal 500-6000,
WTDRD1 > 0. Secondary: children 2-19. Day 2 is a sensitivity check.

Estimands (all survey-weighted with WTDRD1):
  * sugar density of an occasion type = sum(sugar) / sum(kcal), ratio of sums
  * median per-occasion sugar share of calories
  * share of breakfasts above thresholds (median snack share, 25%, 30%)
  * sugar clock: sugar grams by hour; share of daily sugar before noon
  * trend by cycle; splits by age, sex, PIR, race, BMI
  * food-group decomposition of breakfast sugar (FNDDS 1-digit groups)
Cluster bootstrap (resample persons) for CIs on the headline ratios.
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261107)

FOODGRP1 = {"1": "Milk & dairy", "2": "Meat, poultry, fish",
            "3": "Eggs", "4": "Legumes, nuts, seeds", "5": "Grains",
            "6": "Fruit", "7": "Vegetables", "8": "Fats & oils",
            "9": "Sugars, sweets & beverages"}


def wmean(s, w):
    return float(np.average(s, weights=w))


def ratio(df, num="sugar", den="kcal", w="WTDRD1"):
    """Weighted ratio of sums -> per-100-kcal density."""
    return float((df[num] * df[w]).sum() / (df[den] * df[w]).sum() * 100)


def boot_ratio(df, num="sugar", den="kcal", w="WTDRD1", reps=300,
               cluster="SEQN"):
    """Cluster bootstrap (resample persons) for a ratio of sums."""
    persons = df[cluster].unique()
    vals = []
    idx = {p: i for i, p in enumerate(persons)}
    codes = df[cluster].map(idx).to_numpy()
    n = len(df)
    numv = (df[num] * df[w]).to_numpy()
    denv = (df[den] * df[w]).to_numpy()
    for _ in range(reps):
        pick = rng.integers(0, len(persons), len(persons))
        counts = np.bincount(pick, minlength=len(persons))
        mult = counts[codes]
        vals.append((numv * mult).sum() / (denv * mult).sum() * 100)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def share_above(df, thr, w="WTDRD1"):
    m = df["sugar_share"] > thr
    return float((df.loc[m, w]).sum() / df[w].sum() * 100)


def main():
    occ = pd.read_parquet(os.path.join(DATA, "occasions.parquet"))
    items = pd.read_parquet(os.path.join(DATA, "items.parquet"))
    res = {}

    # ---- primary population: adults, day 1 ---------------------------------
    a1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()
    res["n_person_days_adult_d1"] = int(a1["SEQN"].nunique())
    res["n_occasions_adult_d1"] = int(len(a1))

    meals = {}
    for meal, d in a1.groupby("meal"):
        meals[meal] = {
            "n": int(len(d)),
            "sugar_per_100kcal": ratio(d),
            "sugar_per_100kcal_ci": boot_ratio(d),
            "median_sugar_share_pct": float(wmean(
                d["sugar_share"], d["WTDRD1"]) * 100) if False else float(
                d["sugar_share"].median() * 100),
            "median_kcal": float(d["kcal"].median()),
            "median_sugar_g": float(d["sugar"].median()),
            "mean_kcal": float(wmean(d["kcal"], d["WTDRD1"])),
        }
    res["meals_adult_d1"] = meals

    bf = a1[a1["meal"] == "breakfast"]
    sn = a1[a1["meal"] == "snack"]
    evening_snack = sn[sn["t_h"] >= 20]
    res["evening_snack"] = {
        "n": int(len(evening_snack)),
        "sugar_per_100kcal": ratio(evening_snack),
        "sugar_per_100kcal_ci": boot_ratio(evening_snack),
        "median_sugar_share_pct": float(evening_snack["sugar_share"].median() * 100),
    }
    med_snack_share = float(sn["sugar_share"].median())
    res["median_snack_sugar_share"] = med_snack_share
    res["breakfast_above_median_snack_pct"] = share_above(bf, med_snack_share)
    res["breakfast_above_25pct_pct"] = share_above(bf, 0.25)
    res["breakfast_above_30pct_pct"] = share_above(bf, 0.30)
    res["snack_above_25pct_pct"] = share_above(sn, 0.25)
    res["dinner_above_25pct_pct"] = share_above(a1[a1["meal"] == "dinner"], 0.25)
    res["lunch_above_25pct_pct"] = share_above(a1[a1["meal"] == "lunch"], 0.25)
    res["breakfast_above_evening_snack_median_pct"] = share_above(
        bf, float(evening_snack["sugar_share"].median()))

    # ---- sugar clock --------------------------------------------------------
    a1["hour"] = a1["t_h"].astype(int).clip(0, 23)
    clock = (a1.groupby("hour").apply(
        lambda d: pd.Series({
            "sugar_g": float((d["sugar"] * d["WTDRD1"]).sum()),
            "kcal": float((d["kcal"] * d["WTDRD1"]).sum()),
            "sugar_per_100kcal": ratio(d)}), include_groups=False)
        .reset_index())
    clock["sugar_share_of_day_pct"] = clock["sugar_g"] / clock["sugar_g"].sum() * 100
    clock.to_csv(os.path.join(OUT, "sugar_clock.csv"), index=False)
    before_noon = a1[a1["t_h"] < 12]
    res["sugar_before_noon_pct"] = float(
        (before_noon["sugar"] * before_noon["WTDRD1"]).sum()
        / (a1["sugar"] * a1["WTDRD1"]).sum() * 100)
    res["sugar_from_breakfast_pct"] = float(
        (bf["sugar"] * bf["WTDRD1"]).sum()
        / (a1["sugar"] * a1["WTDRD1"]).sum() * 100)
    res["kcal_from_breakfast_pct"] = float(
        (bf["kcal"] * bf["WTDRD1"]).sum()
        / (a1["kcal"] * a1["WTDRD1"]).sum() * 100)
    res["sugar_from_snacks_pct"] = float(
        (sn["sugar"] * sn["WTDRD1"]).sum()
        / (a1["sugar"] * a1["WTDRD1"]).sum() * 100)

    # ---- trend by cycle ------------------------------------------------------
    trend = []
    for cyc, d in a1.groupby("cycle"):
        b = d[d["meal"] == "breakfast"]
        s = d[d["meal"] == "snack"]
        trend.append({"cycle": cyc,
                      "breakfast_sugar_per_100kcal": ratio(b),
                      "snack_sugar_per_100kcal": ratio(s),
                      "breakfast_above_25pct": share_above(b, 0.25),
                      "n_breakfast": int(len(b))})
    res["trend"] = trend

    # ---- who eats the sweetest breakfast ------------------------------------
    def split(df, col, bins=None, labels=None):
        out = []
        d = df.copy()
        if bins is not None:
            d["_grp"] = pd.cut(d[col], bins, labels=labels)
        else:
            d["_grp"] = d[col]
        for g, dd in d.groupby("_grp", observed=True):
            if len(dd) < 200:
                continue
            out.append({"group": str(g), "n": int(len(dd)),
                        "sugar_per_100kcal": ratio(dd),
                        "above_25pct": share_above(dd, 0.25),
                        "median_kcal": float(dd["kcal"].median())})
        return out

    res["breakfast_by_age"] = split(bf, "age_band")
    res["breakfast_by_sex"] = split(bf, "sex")
    res["breakfast_by_pir"] = split(bf, "pir", bins=[0, 1.3, 3.5, 10],
                                    labels=["<1.3x poverty", "1.3-3.5x",
                                            ">3.5x"])
    res["breakfast_by_race"] = split(bf, "race")
    res["breakfast_by_bmi"] = split(bf, "bmi", bins=[0, 18.5, 25, 30, 100],
                                    labels=["<18.5", "18.5-25", "25-30",
                                            "30+"])

    # ---- children, secondary panel -------------------------------------------
    k1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 2) & (occ["age"] <= 19)
             & (occ["day_kcal"] >= 300) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()
    kids = {}
    for meal, d in k1.groupby("meal"):
        kids[meal] = {"n": int(len(d)),
                      "sugar_per_100kcal": ratio(d),
                      "median_sugar_share_pct": float(d["sugar_share"].median() * 100)}
    res["kids_meals_d1"] = kids
    kbf = k1[k1["meal"] == "breakfast"]
    res["kids_breakfast_above_25pct"] = share_above(kbf, 0.25)
    res["kids_breakfast_above_30pct"] = share_above(kbf, 0.30)
    res["kids_breakfast_by_age"] = split(kbf, "age_band")
    res["n_person_days_kids_d1"] = int(k1["SEQN"].nunique())

    # ---- food-group decomposition of breakfast sugar -------------------------
    it = items[(items["day"] == 1) & (items["reliable"] == 1)
               & (items["age"] >= 20) & (items["age"] <= 79)
               & (items["meal"] == "breakfast")].copy()
    # day-kcal filter needs person-day totals; recompute from items
    dayk = (items[(items["day"] == 1)].groupby(["SEQN", "cycle"])
            .agg(dk=("kcal", "sum")).reset_index())
    it = it.merge(dayk, on=["SEQN", "cycle"], how="left")
    it = it[(it["dk"] >= 500) & (it["dk"] <= 6000) & (it["WTDRD1"] > 0)]
    it["w_sugar"] = it["sugar"] * it["WTDRD1"]
    it["w_kcal"] = it["kcal"] * it["WTDRD1"]
    tot_sugar = it["w_sugar"].sum()
    grp = (it.groupby("foodgrp1").agg(
        sugar_share_pct=("w_sugar", lambda s: s.sum() / tot_sugar * 100),
        kcal_share_pct=("w_kcal", lambda s: s.sum() / it["w_kcal"].sum() * 100),
        sugar_per_100kcal=("w_sugar", lambda s: 0))
        .reset_index())
    grp["label"] = grp["foodgrp1"].map(FOODGRP1)
    # sugar density within each group
    dens = it.groupby("foodgrp1").apply(
        lambda d: (d["sugar"] * d["WTDRD1"]).sum()
        / (d["kcal"] * d["WTDRD1"]).sum() * 100, include_groups=False)
    grp["sugar_per_100kcal"] = grp["foodgrp1"].map(dens)
    grp = grp.sort_values("sugar_share_pct", ascending=False)
    res["breakfast_sugar_by_foodgrp1"] = grp.to_dict("records")

    grp2 = (it.groupby("foodgrp2").agg(
        sugar_share_pct=("w_sugar", lambda s: s.sum() / tot_sugar * 100),
        kcal_share_pct=("w_kcal", lambda s: s.sum() / it["w_kcal"].sum() * 100))
        .reset_index())
    dens2 = it.groupby("foodgrp2").apply(
        lambda d: (d["sugar"] * d["WTDRD1"]).sum()
        / (d["kcal"] * d["WTDRD1"]).sum() * 100, include_groups=False)
    grp2["sugar_per_100kcal"] = grp2["foodgrp2"].map(dens2)
    grp2 = grp2.sort_values("sugar_share_pct", ascending=False).head(15)
    res["breakfast_sugar_by_foodgrp2_top15"] = grp2.to_dict("records")
    res["n_breakfast_items"] = int(len(it))

    # ---- day 2 sensitivity ---------------------------------------------------
    a2 = occ[(occ["day"] == 2) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()
    d2 = {}
    for meal, dd in a2.groupby("meal"):
        d2[meal] = {"n": int(len(dd)), "sugar_per_100kcal": ratio(dd)}
    res["meals_adult_d2_sensitivity"] = d2
    res["breakfast_above_25pct_d2"] = share_above(
        a2[a2["meal"] == "breakfast"], 0.25)

    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(res, f, indent=2, default=float)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("trend", "breakfast_sugar_by_foodgrp2_top15")},
                     indent=2, default=float)[:4000])
    print("TREND:", json.dumps(res["trend"], default=float))
    print("GRP2:", json.dumps(res["breakfast_sugar_by_foodgrp2_top15"], default=float))


if __name__ == "__main__":
    main()
