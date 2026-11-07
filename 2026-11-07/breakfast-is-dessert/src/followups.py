"""Follow-ups for build #61: trend decomposition, sensitivity checks,
kids trend, and the breakfast-vs-snack classifier."""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")


def ratio(df, num="sugar", den="kcal", w="WTDRD1"):
    return float((df[num] * df[w]).sum() / (df[den] * df[w]).sum() * 100)


def share_above(df, thr, w="WTDRD1"):
    m = df["sugar_share"] > thr
    return float((df.loc[m, w]).sum() / df[w].sum() * 100)


def main():
    occ = pd.read_parquet(os.path.join(DATA, "occasions.parquet"))
    items = pd.read_parquet(os.path.join(DATA, "items.parquet"))
    res = {}

    a1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()
    bf = a1[a1["meal"] == "breakfast"].copy()

    # --- sensitivity: drop tiny breakfasts (coffee-with-sugar only) ----------
    res["sensitivity_min_kcal"] = {}
    for mn in (0, 100, 200, 300):
        d = bf[bf["kcal"] >= mn]
        res["sensitivity_min_kcal"][str(mn)] = {
            "n": int(len(d)),
            "sugar_per_100kcal": ratio(d),
            "above_25pct": share_above(d, 0.25),
            "above_30pct": share_above(d, 0.30),
            "median_sugar_share_pct": float(d["sugar_share"].median() * 100),
        }

    # --- trend decomposition: what drove the 2007->2018 breakfast decline? ---
    it = items[(items["day"] == 1) & (items["reliable"] == 1)
               & (items["age"] >= 20) & (items["age"] <= 79)
               & (items["meal"] == "breakfast")].copy()
    dayk = (items[(items["day"] == 1)].groupby(["SEQN", "cycle"])
            .agg(dk=("kcal", "sum")).reset_index())
    it = it.merge(dayk, on=["SEQN", "cycle"], how="left")
    it = it[(it["dk"] >= 500) & (it["dk"] <= 6000) & (it["WTDRD1"] > 0)].copy()
    it["w_sugar"] = it["sugar"] * it["WTDRD1"]
    it["w_kcal"] = it["kcal"] * it["WTDRD1"]
    FOODGRP1 = {"1": "Milk & dairy", "2": "Meat, poultry, fish",
                "3": "Eggs", "4": "Legumes, nuts, seeds", "5": "Grains",
                "6": "Fruit", "7": "Vegetables", "8": "Fats & oils",
                "9": "Sugars, sweets & beverages"}
    trend_grp = []
    for cyc, d in it.groupby("cycle"):
        tot_s = d["w_sugar"].sum()
        tot_k = d["w_kcal"].sum()
        row = {"cycle": cyc,
               "breakfast_sugar_per_100kcal": tot_s / tot_k * 100}
        for g, dd in d.groupby("foodgrp1"):
            row[f"sugar_share_{FOODGRP1[g]}"] = float(
                dd["w_sugar"].sum() / tot_s * 100)
            row[f"kcal_share_{FOODGRP1[g]}"] = float(
                dd["w_kcal"].sum() / tot_k * 100)
        trend_grp.append(row)
    res["trend_by_foodgrp"] = trend_grp

    # which groups' sugar fell? per-group sugar per 100 kcal of breakfast
    grp_trend = []
    for g, dd in it.groupby("foodgrp1"):
        per_cyc = []
        for cyc, d in dd.groupby("cycle"):
            per_cyc.append({
                "cycle": cyc,
                "sugar_g_per_breakfast": float(
                    (d["sugar"] * d["WTDRD1"]).sum()
                    / (d["WTDRD1"].sum() / d.groupby("SEQN")["WTDRD1"].first().shape[0] * 0 + 1))})
        grp_trend.append({"group": FOODGRP1[g], "per_cycle": per_cyc})
    res["group_sugar_per_cycle_raw"] = grp_trend

    # --- kids trend -----------------------------------------------------------
    k1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 2) & (occ["age"] <= 19)
             & (occ["day_kcal"] >= 300) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()
    ktrend = []
    for cyc, d in k1.groupby("cycle"):
        b = d[d["meal"] == "breakfast"]
        s = d[d["meal"] == "snack"]
        ktrend.append({"cycle": cyc,
                       "breakfast_sugar_per_100kcal": ratio(b),
                       "snack_sugar_per_100kcal": ratio(s),
                       "breakfast_above_25pct": share_above(b, 0.25)})
    res["kids_trend"] = ktrend

    # --- breakfast vs snack: how much sugar does the average breakfast carry
    #     in grams, and what does a "typical" one look like -------------------
    res["median_breakfast_sugar_g"] = float(bf["sugar"].median())
    res["median_breakfast_kcal"] = float(bf["kcal"].median())
    sn = a1[a1["meal"] == "snack"]
    res["median_snack_sugar_g"] = float(sn["sugar"].median())
    # teaspoons: 4g sugar = 1 tsp
    res["median_breakfast_sugar_tsp"] = float(bf["sugar"].median() / 4.0)
    res["median_snack_sugar_tsp"] = float(sn["sugar"].median() / 4.0)
    # distribution of breakfast sugar share: deciles
    w = bf["WTDRD1"].to_numpy()
    s = bf["sugar_share"].to_numpy()
    order = np.argsort(s)
    cw = np.cumsum(w[order]) / w.sum()
    dec = [float(s[order][np.searchsorted(cw, q)]) * 100
           for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    res["breakfast_sugar_share_deciles_pct"] = dec

    with open(os.path.join(OUT, "followups.json"), "w") as f:
        json.dump(res, f, indent=2, default=float)
    print(json.dumps(res, indent=2, default=float)[:5000])


if __name__ == "__main__":
    main()
