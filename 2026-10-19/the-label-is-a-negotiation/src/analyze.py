"""The Label Is a Negotiation - analysis.

Data: data/products.parquet (629k current US branded products, USDA FoodData
Central Global Branded Food Products Database, April 2025 release).
Nutrient amounts are the manufacturers' own submissions per 100 g; the
per-serving label value is reconstructed as amount x serving_size / 100,
which is exactly the arithmetic the printed Nutrition Facts panel performs.

Modules:
 1. Zero-window census: products whose per-100g data shows a nutrient but
    whose per-serving value falls inside the FDA legal-zero window
    (21 CFR 101.9(c): <0.5 g fats/sugars, <5 mg sodium, <2 mg cholesterol,
    <5 kcal may all be declared as 0). Plus a 'material' tier per nutrient.
 2. Threshold-proximity scoreboard at FDA nutrient-content claim lines
    vs placebo lines (does mass pile up just under the famous lines?).
 3. Tiny servings + hideable capacity: how much nutrient per 100 g a
    printed 0 can legally hide, as a function of the chosen serving size.
 4. Standard-serving counterfactual: relabel every product at its own
    category's median serving; count printed zeros and claim eligibilities
    that exist only because the serving is smaller than standard.
 5. Declaration-grid measurement: what share of printed values sit exactly
    on the FDA rounding grid for each nutrient.
 6. XGBoost + SHAP: among products that contain a nutrient, what predicts
    printing a zero for it - the content, or the serving size?
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
rng = np.random.default_rng(7)

df = pd.read_parquet(ROOT / "data" / "products.parquet")
R = {"n_products": int(len(df)),
     "source": "USDA FoodData Central, Global Branded Food Products Database, April 2025 release",
     "n_categories": int(df["branded_food_category"].nunique()),
     "n_brands": int(df["brand_owner"].nunique())}

# ---------------------------------------------------------------- module 1
ZERO = [  # col, label, zero threshold per serving, material per-100g cut
    ("transfat_g", "trans fat", 0.5, 1.0),
    ("fat_g", "total fat", 0.5, 5.0),
    ("satfat_g", "saturated fat", 0.5, 2.0),
    ("sugar_g", "sugar", 0.5, 10.0),
    ("sodium_mg", "sodium", 5.0, 400.0),
    ("cholesterol_mg", "cholesterol", 2.0, 10.0),
    ("kcal", "calories", 5.0, 50.0),
]
census, examples = [], []
for col, name, thr, mat in ZERO:
    s = df.dropna(subset=[col + "_serv"]).copy()
    has = s[col] > 0
    zw = s[has & (s[col + "_serv"] < thr)]
    mat_zw = zw[zw[col] >= mat]
    census.append({
        "nutrient": name, "n_reporting": int(len(s)),
        "n_print_zero_total": int((s[col + "_serv"] < thr).sum()),
        "n_zero_window": int(len(zw)),
        "pct_of_reporters": round(100 * len(zw) / len(s), 2),
        "n_zero_window_material": int(len(mat_zw)),
        "material_cut_per100g": mat,
        "median_serving_zero_window": float(zw["serving_size"].median()) if len(zw) else None,
        "median_serving_all": float(s["serving_size"].median()),
        "top_categories": zw["branded_food_category"].value_counts().head(5)
                            .rename_axis("cat").reset_index(name="n")
                            .to_dict("records"),
    })
    ex = mat_zw.sort_values(col, ascending=False).head(12)
    for _, r in ex.iterrows():
        examples.append({"nutrient": name, "description": r["description"],
                         "brand_owner": r["brand_owner"],
                         "category": r["branded_food_category"],
                         "serving_size": float(r["serving_size"]),
                         "household": r["household_serving_fulltext"],
                         "per100g": float(r[col]),
                         "per_serving": float(r[col + "_serv"])})
R["zero_window_census"] = census
R["zero_window_total_pairs"] = int(sum(c["n_zero_window"] for c in census))
R["zero_window_material_total"] = int(sum(c["n_zero_window_material"] for c in census))
pd.DataFrame(examples).to_csv(OUT / "zero_window_examples.csv", index=False)

# ---------------------------------------------------------------- module 2
def prox(col, thr, band):
    s = df[col + "_serv"].dropna()
    lo, hi = thr * (1 - band), thr * (1 + band)
    b = int(((s >= lo) & (s < thr)).sum()); a = int(((s >= thr) & (s <= hi)).sum())
    return {"below": b, "above": a, "below_share": round(b / max(b + a, 1), 3)}

R["proximity"] = {
    "sodium_140_low_sodium": prox("sodium_mg", 140, 0.15),
    "sodium_98_placebo": prox("sodium_mg", 98, 0.15),
    "sodium_182_placebo": prox("sodium_mg", 182, 0.15),
    "sodium_35_very_low": prox("sodium_mg", 35, 0.25),
    "satfat_1_low": prox("satfat_g", 1.0, 0.25),
    "satfat_0.7_placebo": prox("satfat_g", 0.7, 0.25),
    "fat_3_low_fat": prox("fat_g", 3.0, 0.20),
    "fat_2.1_placebo": prox("fat_g", 2.1, 0.20),
    "kcal_40_low_calorie": prox("kcal", 40, 0.20),
    "kcal_28_placebo": prox("kcal", 28, 0.20),
    "cholesterol_20_low": prox("cholesterol_mg", 20, 0.25),
    "potassium_140_no_claim_exists": prox("potassium_mg", 140, 0.15),
}

# ---------------------------------------------------------------- module 3
tiny = {}
for t in [0.5, 1, 2, 5, 10]:
    tiny[f"serving_lt_{t}g"] = int((df["serving_size"] < t).sum())
R["tiny_servings"] = tiny
# hideable capacity for a printed 0 of fat / sugar: thr*100/serving grams per 100 g
for col, name, thr in [("fat_g", "fat", 0.5), ("sugar_g", "sugar", 0.5),
                       ("transfat_g", "trans_fat", 0.5)]:
    cap = thr * 100.0 / df["serving_size"]
    R[f"hideable_{name}"] = {
        "products_can_hide_ge_5g_per100g": int((cap >= 5).sum()),
        "products_can_hide_ge_10g_per100g": int((cap >= 10).sum()),
        "products_can_hide_ge_25g_per100g": int((cap >= 25).sum()),
        "products_can_hide_ge_50g_per100g": int((cap >= 50).sum()),
        "products_can_hide_ge_100g_per100g": int((cap >= 100).sum()),
    }
# the spray contrast: a product that is oil, in the oil aisle, printing zeros
oils = df[df["branded_food_category"] == "Vegetable & Cooking Oils"].copy()
spray = oils[oils["description"].str.contains("SPRAY", case=False, na=False)]
bottled = oils[~oils["description"].str.contains("SPRAY", case=False, na=False)]
R["spray_contrast"] = {
    "n_sprays": int(len(spray)),
    "spray_median_serving_g": float(spray["serving_size"].median()),
    "spray_share_fat_submitted_0_per100g": round(float((spray["fat_g"] == 0).mean()), 3),
    "spray_share_print_0_fat_and_0_kcal": round(float(((spray["fat_g_serv"] < 0.5) &
                                                      (spray["kcal_serv"] < 5)).mean()), 3),
    "n_bottled_oils": int(len(bottled)),
    "bottled_median_fat_per100g": float(bottled["fat_g"].median()),
    "bottled_median_serving_g": float(bottled["serving_size"].median()),
    "bottled_median_kcal_serv": float(bottled["kcal_serv"].median()),
}
# named emblems
tic = df[df["description"].str.contains("TIC TAC", case=False, na=False) &
         df["brand_owner"].str.contains("Ferrero", case=False, na=False)]
R["tictac"] = {"n_skus": int(len(tic)),
               "serving_size_g": float(tic["serving_size"].median()),
               "kcal_per100g": float(tic["kcal"].median()),
               "sugar_submitted_per100g": float(tic["sugar_g"].median())}
sw = df[df["description"].str.contains("ZERO CALORIE SWEETENER", case=False, na=False)]
R["zero_cal_sweetener"] = {
    "n_skus": int(len(sw)),
    "share_sugar_ge_90_per100g": round(float((sw["sugar_g"] >= 90).mean()), 3),
    "median_serving_g": float(sw["serving_size"].median()),
    "median_sugar_per100g": float(sw["sugar_g"].median()),
}

# ---------------------------------------------------------------- module 4
med = df.groupby("branded_food_category")["serving_size"].median().rename("cat_med")
df = df.join(med, on="branded_food_category")
CLAIMS = [("transfat_g", "trans fat 0", 0.5, "zero"), ("fat_g", "total fat 0", 0.5, "zero"),
          ("satfat_g", "saturated fat 0", 0.5, "zero"), ("sugar_g", "sugar 0", 0.5, "zero"),
          ("kcal", "calorie 0", 5.0, "zero"),
          ("sodium_mg", "low sodium (<=140mg)", 140.0, "claim_le"),
          ("fat_g", "low fat (<=3g)", 3.0, "claim_le"),
          ("kcal", "low calorie (<=40)", 40.0, "claim_le"),
          ("satfat_g", "low sat fat (<=1g)", 1.0, "claim_le")]
flips = []
for col, name, thr, kind in CLAIMS:
    s = df.dropna(subset=[col + "_serv"]).copy()
    s["cf"] = s[col] * s["cat_med"] / 100.0
    if kind == "zero":
        now = s[col + "_serv"] < thr; cf = s["cf"] < thr
    else:
        now = s[col + "_serv"] <= thr; cf = s["cf"] <= thr
    flips.append({"label": name, "eligible_now": int(now.sum()),
                  "lost_at_standard_serving": int((now & ~cf).sum()),
                  "pct_lost": round(100 * (now & ~cf).sum() / max(now.sum(), 1), 1)})
R["counterfactual_flips"] = flips
R["counterfactual_zero_flips_total"] = int(sum(f["lost_at_standard_serving"]
                                               for f in flips if f["label"].endswith(" 0")))

# ---------------------------------------------------------------- module 5
def grid_share(values, grid, tol_frac=0.06):
    v = values.dropna(); v = v[(v > 0) & (v <= grid * 200)]
    r = v / grid
    dist = np.abs(r - np.round(r)) * grid
    return round(float((dist <= tol_frac * grid + 0.01).mean()), 3), int(len(v))

R["grid_shares"] = {}
for col, name, grid in [("satfat_g", "saturated fat (0.5g grid)", 0.5),
                        ("transfat_g", "trans fat (0.5g grid)", 0.5),
                        ("fat_g", "total fat (0.5g grid, <5g)", 0.5),
                        ("cholesterol_mg", "cholesterol (5mg grid)", 5.0),
                        ("sodium_mg", "sodium (5mg grid)", 5.0),
                        ("kcal", "calories (5 kcal grid)", 5.0),
                        ("fiber_g", "fiber (1g grid)", 1.0),
                        ("potassium_mg", "potassium (10mg grid, placebo-ish)", 10.0)]:
    share, n = grid_share(df[col + "_serv"], grid)
    R["grid_shares"][name] = {"on_grid_share": share, "n": n}

# ---------------------------------------------------------------- module 6
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import shap

def zero_model(col, thr, seed=7):
    s = df.dropna(subset=[col, col + "_serv", "kcal"]).copy()
    s = s[s[col] > 0]
    s["y"] = (s[col + "_serv"] < thr).astype(int)
    top_cats = s["branded_food_category"].value_counts().head(15).index
    X = pd.DataFrame({
        "log_serving": np.log(s["serving_size"]),
        "log_content100": np.log(s[col].clip(lower=0.01)),
        "log_kcal100": np.log(s["kcal"].clip(lower=1)),
        "serving_lt_5g": (s["serving_size"] < 5).astype(int),
        "serving_lt_30g": (s["serving_size"] < 30).astype(int),
    })
    for c in top_cats:
        X["cat_" + c[:18]] = (s["branded_food_category"] == c).astype(int)
    if len(s) > 120_000:
        idx = rng.choice(len(s), 120_000, replace=False)
        X, y = X.iloc[idx], s["y"].iloc[idx]
    else:
        y = s["y"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=seed)
    m = XGBClassifier(n_estimators=350, max_depth=5, learning_rate=0.06,
                      subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
                      n_jobs=4, random_state=seed)
    m.fit(Xtr, ytr)
    auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
    def auc_only(cols):
        mm = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.08,
                           eval_metric="logloss", n_jobs=4, random_state=seed)
        mm.fit(Xtr[cols], ytr)
        return float(roc_auc_score(yte, mm.predict_proba(Xte[cols])[:, 1]))
    auc_serv = auc_only(["log_serving", "serving_lt_5g", "serving_lt_30g"])
    auc_cont = auc_only(["log_content100"])
    expl = shap.TreeExplainer(m)
    sv = expl.shap_values(Xte.iloc[:4000])
    shap_mean = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
    return {"n": int(len(y)), "base_rate_prints_zero": round(float(y.mean()), 4),
            "auc_full": round(auc, 3), "auc_serving_only": round(auc_serv, 3),
            "auc_content_only": round(auc_cont, 3),
            "top_shap": {k: round(float(v), 4) for k, v in shap_mean.head(8).items()},
            "_shap_sample": (Xte.iloc[:4000], sv)}

zm_fat = zero_model("fat_g", 0.5)
zm_kcal = zero_model("kcal", 5.0)
for tag, zm in [("fat_zero_model", zm_fat), ("kcal_zero_model", zm_kcal)]:
    R[tag] = {k: v for k, v in zm.items() if not k.startswith("_")}
np.savez(OUT / "shap_fat.npz", values=zm_fat["_shap_sample"][1],
         columns=np.array(list(zm_fat["_shap_sample"][0].columns)),
         X=zm_fat["_shap_sample"][0].to_numpy())

(OUT / "results.json").write_text(json.dumps(R, indent=1, default=str))
print(json.dumps({k: R[k] for k in ["n_products", "zero_window_total_pairs",
                                    "zero_window_material_total",
                                    "counterfactual_zero_flips_total"]}, indent=1))
print("spray:", R["spray_contrast"]); print("tictac:", R["tictac"])
print("fat model:", R["fat_zero_model"]); print("kcal model:", R["kcal_zero_model"])
