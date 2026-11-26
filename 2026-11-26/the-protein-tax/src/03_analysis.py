"""Analysis: does protein branding cost you fiber?

Questions:
  1. Within each grocery category, do protein-branded products carry less
     fiber per calorie than the plain versions they replace?
  2. What is the exchange rate: grams of fiber lost per gram of protein gained?
  3. How many protein-branded products actually meet the 'high protein' bar
     (20% of energy from protein), and how many are fiber-poor?
  4. Does the protein version score worse overall (Nutri-Score)?
  5. What does a full day of protein swaps cost in fiber, vs the fiber gap?

Outputs: data/category_table.csv, data/exchange_rates.csv, data/swap_scenario.csv,
         data/claim_audit.csv, data/analysis.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CATS = ["bars", "yogurts", "cereals", "breads", "pastas", "cookies"]
# typical serving (grams) used for the daily-swap scenario
SERVING = {"bars": 60, "yogurts": 170, "cereals": 40, "breads": 50, "pastas": 56, "cookies": 30}


def main():
    df = pd.read_csv(DATA / "clean_products.csv")
    df = df.dropna(subset=["fiber_100g"])  # fiber analyses need fiber declared
    out = {}

    # ---- 1. per-category medians, protein vs plain -------------------------
    rows = []
    for cat in CATS:
        sub = df[df["category"] == cat]
        for grp in ("protein", "plain"):
            g = sub[sub["group"] == grp]
            rows.append(
                {
                    "category": cat,
                    "group": grp,
                    "n": len(g),
                    "protein_100g_med": g["protein_100g"].median(),
                    "fiber_100g_med": g["fiber_100g"].median(),
                    "fiber_per_100kcal_med": g["fiber_per_100kcal"].median(),
                    "protein_per_100kcal_med": g["protein_per_100kcal"].median(),
                    "protein_kcal_share_med": g["protein_kcal_share"].median(),
                    "sugars_100g_med": g["sugars_100g"].median(),
                    "kcal_100g_med": g["kcal_100g"].median(),
                    "nutriscore_num_med": g["nutriscore_num"].median(),
                    "pct_fiber_source": 100 * g["fiber_source"].mean(),
                    "pct_high_protein": 100 * g["high_protein"].mean(),
                    "pct_fiber_poor": 100 * g["fiber_poor"].mean(),
                    "pct_nutriscore_ab": 100 * (g["nutriscore_num"] <= 2).mean(),
                    "pct_nutriscore_de": 100 * (g["nutriscore_num"] >= 4).mean(),
                }
            )
        p = sub[sub["group"] == "protein"]["fiber_per_100kcal"]
        q = sub[sub["group"] == "plain"]["fiber_per_100kcal"]
        if len(p) >= 10 and len(q) >= 10:
            u = stats.mannwhitneyu(p, q, alternative="two-sided")
            rows[-2]["fiber_mwu_p"] = u.pvalue
            rows[-2]["fiber_median_diff"] = p.median() - q.median()
    table = pd.DataFrame(rows)
    table.to_csv(DATA / "category_table.csv", index=False)

    # ---- 2. exchange rate: fiber per 100 kcal ~ protein per 100 kcal -------
    ex_rows = []
    for cat in CATS:
        sub = df[df["category"] == cat]
        if len(sub) < 10 or sub["protein_per_100kcal"].nunique() < 2:
            continue
        r = stats.linregress(sub["protein_per_100kcal"], sub["fiber_per_100kcal"])
        ex_rows.append(
            {
                "category": cat,
                "n": len(sub),
                "slope_fiber_per_protein": r.slope,
                "intercept": r.intercept,
                "r_value": r.rvalue,
                "p_value": r.pvalue,
            }
        )
    # pooled with category fixed effects (demeaned OLS via numpy lstsq)
    d = df.copy()
    for c in ["protein_per_100kcal", "fiber_per_100kcal"]:
        d[c + "_dm"] = d[c] - d.groupby("category")[c].transform("mean")
    X = d[["protein_per_100kcal_dm"]].to_numpy()
    y = d["fiber_per_100kcal_dm"].to_numpy()
    slope = float(np.linalg.lstsq(X, y, rcond=None)[0][0])
    resid = y - slope * X[:, 0]
    se = float(np.sqrt((resid ** 2).sum() / (len(y) - 2) / (X ** 2).sum()))
    ex_rows.append(
        {
            "category": "POOLED (category fixed effects)",
            "n": len(d),
            "slope_fiber_per_protein": slope,
            "intercept": np.nan,
            "r_value": np.nan,
            "p_value": float(2 * stats.t.sf(abs(slope / se), len(y) - 2)),
        }
    )
    ex = pd.DataFrame(ex_rows)
    ex.to_csv(DATA / "exchange_rates.csv", index=False)

    # ---- 3. claim audit ------------------------------------------------------
    prot = df[df["group"] == "protein"]
    audit = pd.DataFrame(
        [
            {
                "metric": "protein-branded products meeting EU 'high protein' bar (>=20% energy)",
                "pct": 100 * prot["high_protein"].mean(),
                "n": len(prot),
            },
            {
                "metric": "protein-branded products that are fiber-poor (<3g fiber/100g)",
                "pct": 100 * prot["fiber_poor"].mean(),
                "n": len(prot),
            },
            {
                "metric": "protein-branded AND fiber-poor AND below high-protein bar",
                "pct": 100 * ((prot["fiber_poor"]) & (~prot["high_protein"])).mean(),
                "n": len(prot),
            },
            {
                "metric": "plain products that are fiber-poor (<3g fiber/100g)",
                "pct": 100 * df[df["group"] == "plain"]["fiber_poor"].mean(),
                "n": int((df["group"] == "plain").sum()),
            },
            {
                "metric": "protein-branded with Nutri-Score D or E",
                "pct": 100 * (prot["nutriscore_num"] >= 4).mean(),
                "n": int(prot["nutriscore_num"].notna().sum()),
            },
            {
                "metric": "plain with Nutri-Score D or E",
                "pct": 100 * (df[df["group"] == "plain"]["nutriscore_num"] >= 4).mean(),
                "n": int(df[df["group"] == "plain"]["nutriscore_num"].notna().sum()),
            },
        ]
    )
    audit.to_csv(DATA / "claim_audit.csv", index=False)

    # ---- 4. daily swap scenario ---------------------------------------------
    # Swap the plain version for the protein version at equal calories, for a
    # typical day: breakfast cereal + yogurt, a bar as a snack. Breads and
    # pastas are excluded: their protein samples are small (n=6, n=17) and
    # both point the same direction, so including them would overstate precision.
    swap_rows = []
    total_fiber_lost = 0.0
    for cat in ["cereals", "yogurts", "bars"]:
        sub = df[df["category"] == cat]
        if "protein" not in sub["group"].values or "plain" not in sub["group"].values:
            continue
        med = sub.groupby("group")[["fiber_per_100kcal", "kcal_100g"]].median()
        # calories in a typical plain serving
        plain_kcal = med.loc["plain", "kcal_100g"] * SERVING[cat] / 100
        plain_fiber = med.loc["plain", "fiber_per_100kcal"] * plain_kcal / 100
        prot_fiber = med.loc["protein", "fiber_per_100kcal"] * plain_kcal / 100
        prot_protein_gain = (
            sub[sub["group"] == "protein"]["protein_per_100kcal"].median()
            - sub[sub["group"] == "plain"]["protein_per_100kcal"].median()
        ) * plain_kcal / 100
        swap_rows.append(
            {
                "category": cat,
                "serving_g": SERVING[cat],
                "plain_kcal": round(plain_kcal, 1),
                "plain_fiber_g": round(plain_fiber, 2),
                "protein_version_fiber_g": round(prot_fiber, 2),
                "fiber_lost_g": round(plain_fiber - prot_fiber, 2),
                "protein_gained_g": round(prot_protein_gain, 1),
            }
        )
        total_fiber_lost += plain_fiber - prot_fiber
    swap = pd.DataFrame(swap_rows)
    swap.to_csv(DATA / "swap_scenario.csv", index=False)

    # ---- 5. pooled headline numbers ------------------------------------------
    pooled = df.groupby("group")["fiber_per_100kcal"].median()
    pooled_protein = df.groupby("group")["protein_per_100kcal"].median()
    u = stats.mannwhitneyu(
        df[df["group"] == "protein"]["fiber_per_100kcal"],
        df[df["group"] == "plain"]["fiber_per_100kcal"],
    )
    out = {
        "n_products": len(df),
        "n_protein_branded": int((df["group"] == "protein").sum()),
        "n_plain": int((df["group"] == "plain").sum()),
        "pooled_fiber_per_100kcal": {
            "protein": round(float(pooled["protein"]), 3),
            "plain": round(float(pooled["plain"]), 3),
        },
        "pooled_protein_per_100kcal": {
            "protein": round(float(pooled_protein["protein"]), 2),
            "plain": round(float(pooled_protein["plain"]), 2),
        },
        "pooled_fiber_mwu_p": float(u.pvalue),
        "pooled_exchange_slope": slope,
        "pooled_exchange_slope_se": se,
        "daily_swap_fiber_lost_g": round(total_fiber_lost, 2),
        "fiber_gap_women_g": 25 - 16,  # recommended 25g vs mean intake ~16g
        "fiber_gap_men_g": 38 - 16,
        "swap_as_pct_of_women_gap": round(100 * total_fiber_lost / 9, 1),
        "swap_as_pct_of_men_gap": round(100 * total_fiber_lost / 22, 1),
    }
    with open(DATA / "analysis.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(table.to_string())
    print(ex.to_string())
    print(audit.to_string())
    print(swap.to_string())


if __name__ == "__main__":
    main()
