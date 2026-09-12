"""Core analyses for the Protein Atlas.

Reads output/foods_wide.csv and produces derived tables in output/ plus
findings.txt and summary.json.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

EXCLUDE_CATS = {
    "Spices and Herbs",  # per-100-kcal rankings meaningless at spice serving sizes
    "Quality Control Materials",
    "Branded Food Products Database",
    "American Indian/Alaska Native Foods",  # n too small for category stats
}

# FDA Daily Values, for the NRF-style nutrient-density score
DV = {
    "protein_g": 50, "fiber_g": 28, "vita_mcg": 900, "vitc_mg": 90,
    "calcium_mg": 1300, "iron_mg": 18, "magnesium_mg": 420,
    "potassium_mg": 4700, "folate_mcg": 400,
    "satfat_g": 20, "sodium_mg": 2300, "sugar_g": 50,
}
BENEFICIAL = ["protein_g", "fiber_g", "vita_mcg", "vitc_mg", "calcium_mg",
              "iron_mg", "magnesium_mg", "potassium_mg", "folate_mcg"]
LIMIT = ["satfat_g", "sodium_mg", "sugar_g"]


def main():
    df = pd.read_csv(OUT / "foods_wide.csv")
    df = df[df["kcal"].fillna(0) > 0].copy()
    print(f"foods with kcal>0: {len(df):,}")

    k = 100.0 / df["kcal"]  # scale factor: per-100-kcal
    df["prot_100kcal"] = df["protein_g"] * k
    df["fiber_100kcal"] = df["fiber_g"].fillna(0) * k
    df["sugar_100kcal"] = df["sugar_g"].fillna(0) * k
    df["satfat_100kcal"] = df["satfat_g"].fillna(0) * k
    df["sodium_100kcal"] = df["sodium_mg"].fillna(0) * k
    df["prot_kcal_share"] = df["protein_g"] * 4 / df["kcal"] * 100
    df["sugar_kcal_share"] = df["sugar_g"].fillna(0) * 4 / df["kcal"] * 100
    df["energy_density"] = df["kcal"]  # per 100 g
    df["leu_100kcal_mg"] = df["leu_g"] * 1000 * k
    df["kcal_per_3g_leu"] = np.where(df["leu_g"] > 0, 3.0 / (df["leu_g"] * k) * 100, np.nan)

    # NRF-style nutrient density score (per 100 kcal).
    # Missing values are treated as 0 (conservative for beneficial nutrients;
    # for sugar/sodium the missing cases are overwhelmingly ~0 foods like meats).
    per100 = df[[c for c in DV]].fillna(0).mul(k, axis=0)
    pos = sum(np.minimum(100, 100 * per100[c] / DV[c]) for c in BENEFICIAL)
    neg = sum(100 * per100[c] / DV[c] for c in LIMIT)
    df["nrf_score"] = pos - neg

    # satiety proxy: protein + fiber per 100 kcal, plus water share
    df["satiety"] = df["prot_100kcal"] + df["fiber_100kcal"] + df["water_g"].fillna(0) / 100

    df.to_csv(OUT / "foods_derived.csv", index=False)

    sub = df[~df["category"].isin(EXCLUDE_CATS)].copy()
    # per-100-kcal leaderboards need a sane calorie floor (excludes ~0 kcal
    # drinks/bouillons where trace protein explodes the ratio)
    lead = sub[sub["kcal"] >= 25].copy()
    findings = []

    # ---- 1. protein density ----
    top25 = lead.nlargest(25, "prot_100kcal")[
        ["description", "category", "kcal", "protein_g", "prot_100kcal"]]
    top25.to_csv(OUT / "top25_protein_density.csv", index=False)
    cat_prot = sub.groupby("category")["prot_100kcal"].agg(["median", "count"]).round(2)
    cat_prot = cat_prot[cat_prot["count"] >= 20].sort_values("median", ascending=False)
    cat_prot.to_csv(OUT / "category_protein_density.csv")
    findings.append(
        f"Protein density: the single most protein-dense food is "
        f"'{top25.iloc[0]['description']}' at {top25.iloc[0]['prot_100kcal']:.1f} g protein "
        f"per 100 kcal; the median food across the database delivers only "
        f"{sub['prot_100kcal'].median():.1f} g/100 kcal."
    )
    findings.append(
        f"By category (median g protein/100 kcal): "
        + "; ".join(f"{c}: {v['median']:.1f}" for c, v in cat_prot.head(5).iterrows())
        + f". Lowest: {cat_prot.tail(3).index.tolist()}."
    )

    # ---- 2. protein leverage ----
    r = sub[["prot_kcal_share", "energy_density"]].corr(method="spearman").iloc[0, 1]
    prot_cats = ["Beef Products", "Poultry Products", "Pork Products",
                 "Lamb, Veal, and Game Products", "Finfish and Shellfish Products",
                 "Dairy and Egg Products", "Legumes and Legume Products",
                 "Sausages and Luncheon Meats"]
    pf = sub[sub["category"].isin(prot_cats)]
    r_pf = pf[["prot_kcal_share", "energy_density"]].corr(method="spearman").iloc[0, 1]
    findings.append(
        f"Protein leverage, tested in food-composition data: across all {len(sub):,} foods the "
        f"share of calories from protein barely predicts energy density (Spearman r = {r:.2f}) "
        f"because water content dominates — but within protein-food categories "
        f"(meat, fish, dairy, legumes; n={len(pf):,}) the leverage pattern is clear: r = {r_pf:.2f}."
    )

    # ---- 3. leucine ----
    leu = lead[lead["leu_g"].notna()].copy()
    leu["fam"] = leu["description"].str.split(",").str[:2].str.join(",")
    leu = leu.sort_values("leu_100kcal_mg", ascending=False).drop_duplicates("fam")
    top_leu = leu.head(20)[["description", "category", "leu_100kcal_mg", "kcal_per_3g_leu"]]
    top_leu.to_csv(OUT / "top20_leucine_density.csv", index=False)
    chick = sub[sub["description"].str.contains("Chicken, breast", case=False, na=False)]
    findings.append(
        f"Leucine density (the muscle-protein-synthesis trigger, ~3 g/meal threshold): leader is "
        f"'{top_leu.iloc[0]['description']}' at {top_leu.iloc[0]['leu_100kcal_mg']:.0f} mg/100 kcal "
        f"— just {top_leu.iloc[0]['kcal_per_3g_leu']:.0f} kcal to hit 3 g leucine."
        + (f" Chicken breast: {chick['leu_100kcal_mg'].median():.0f} mg/100 kcal."
           if len(chick) and chick["leu_100kcal_mg"].notna().any() else "")
    )

    # ---- 4. nutrient density ----
    top_nrf = sub.nlargest(25, "nrf_score")[["description", "category", "nrf_score"]]
    top_nrf.to_csv(OUT / "top25_nutrient_density.csv", index=False)
    cat_nrf = sub.groupby("category")["nrf_score"].agg(["median", "count"]).round(1)
    cat_nrf = cat_nrf[cat_nrf["count"] >= 20].sort_values("median", ascending=False)
    cat_nrf.to_csv(OUT / "category_nutrient_density.csv")
    findings.append(
        f"NRF-style nutrient density (per 100 kcal): top food is "
        f"'{top_nrf.iloc[0]['description']}' (score {top_nrf.iloc[0]['nrf_score']:.0f}); "
        f"top categories by median: "
        + "; ".join(f"{c} ({v['median']:.0f})" for c, v in cat_nrf.head(3).iterrows())
        + f"; bottom: {cat_nrf.tail(2).index.tolist()}."
    )

    # ---- 5. sugar bombs (grams of sugar per 100 kcal; these are ~100% sugar calories) ----
    sug = lead[lead["sugar_g"].notna()]
    top_sug = sug.nlargest(15, "sugar_100kcal")[
        ["description", "category", "sugar_100kcal"]]
    top_sug.to_csv(OUT / "top15_sugar.csv", index=False)
    findings.append(
        f"Sugar bombs: '{top_sug.iloc[0]['description']}' packs "
        f"{top_sug.iloc[0]['sugar_100kcal']:.1f} g sugar per 100 kcal "
        f"(essentially 100% of its calories from sugar); median food: "
        f"{sug['sugar_100kcal'].median():.1f} g/100 kcal."
    )

    # ---- 6. sodium traps ----
    cat_na = sub.groupby("category")["sodium_100kcal"].agg(["median", "count"]).round(0)
    cat_na = cat_na[cat_na["count"] >= 20].sort_values("median", ascending=False)
    cat_na.to_csv(OUT / "category_sodium.csv")
    findings.append(
        f"Sodium per 100 kcal, category medians: "
        + "; ".join(f"{c}: {v['median']:.0f} mg" for c, v in cat_na.head(3).iterrows())
        + f" vs lowest {cat_na.tail(2).index.tolist()}."
    )

    # ---- 7. fiber gap ----
    fib = sub["fiber_100kcal"]
    pct_hi = (sub["fiber_g"] >= 3).mean() * 100
    findings.append(
        f"Fiber gap: only {pct_hi:.1f}% of foods deliver >=3 g fiber per 100 g; "
        f"median fiber is {fib.median():.2f} g/100 kcal."
    )

    # ---- 8. asian spotlight ----
    pats = {
        "Tofu": "tofu", "Tempeh": "tempeh", "Edamame": "edamame",
        "Seitan/wheat gluten": "seitan|wheat gluten", "Natto": "natto",
        "Chicken breast": "chicken, breast", "Salmon": "salmon",
        "Beef (lean)": "beef,.*lean|beef, loin",
        "Lentils": "lentils", "Chickpeas": "chickpeas",
    }
    rows = []
    for label, pat in pats.items():
        m = sub[sub["description"].str.contains(pat, case=False, na=False)]
        if len(m):
            rows.append({
                "food": label, "n": len(m),
                "prot_100kcal": round(m["prot_100kcal"].median(), 1),
                "leu_mg_100kcal": round(m["leu_100kcal_mg"].median(), 0)
                if m["leu_100kcal_mg"].notna().any() else None,
            })
    asia = pd.DataFrame(rows)
    asia.to_csv(OUT / "asian_spotlight.csv", index=False)
    tofu = asia[asia["food"] == "Tofu"]
    findings.append(
        "Asian spotlight (median g protein/100 kcal): "
        + "; ".join(f"{r['food']} {r['prot_100kcal']}" for _, r in asia.iterrows())
    )

    with open(OUT / "findings.txt", "w") as f:
        for i, x in enumerate(findings, 1):
            f.write(f"{i}. {x}\n")

    summary = {
        "n_foods": int(len(df)),
        "n_categories": int(df["category"].nunique()),
        "median_protein_per_100kcal": round(float(sub["prot_100kcal"].median()), 2),
        "protein_leverage_spearman_r": round(float(r), 3),
        "pct_foods_ge3g_fiber": round(float(pct_hi), 1),
        "top_protein_food": top25.iloc[0]["description"],
        "top_protein_value": round(float(top25.iloc[0]["prot_100kcal"]), 1),
        "top_nrf_food": top_nrf.iloc[0]["description"],
        "top_nrf_score": round(float(top_nrf.iloc[0]["nrf_score"]), 0),
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print("\nfindings written to output/findings.txt")


if __name__ == "__main__":
    main()
