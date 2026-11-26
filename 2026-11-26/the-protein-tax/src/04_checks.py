"""Robustness checks for the protein-vs-fiber finding.

  A. Same comparison per 100g instead of per 100 kcal.
  B. Drop products with 'fiber'/'fibre' in the name (fiber-fortified plain
     products could inflate the plain side).
  C. Drop the single largest brand in each category (one brand driving it?).
  D. Means instead of medians.
  E. Spot-check the classifier: print sample protein-branded names per category.
  F. The pasta exception: legume-based protein pasta vs whey-fortified protein
     pasta (does the protein source decide whether fiber survives?).

Outputs: data/checks.json (plus printed tables).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CATS = ["bars", "yogurts", "cereals", "breads", "pastas", "cookies"]


def pooled_diff(df, col):
    p = df[df["group"] == "protein"][col].dropna()
    q = df[df["group"] == "plain"][col].dropna()
    if len(p) == 0 or len(q) == 0:
        return {"protein_median": None, "plain_median": None, "diff": None,
                "pct_lower": None, "mwu_p": None, "n_protein": len(p), "n_plain": len(q)}
    u = stats.mannwhitneyu(p, q)
    med_q = q.median()
    return {
        "protein_median": round(float(p.median()), 3),
        "plain_median": round(float(med_q), 3),
        "diff": round(float(p.median() - med_q), 3),
        "pct_lower": round(100 * (med_q - p.median()) / med_q, 1) if med_q else None,
        "mwu_p": float(u.pvalue),
        "n_protein": len(p),
        "n_plain": len(q),
    }


def main():
    df = pd.read_csv(DATA / "clean_products.csv").dropna(subset=["fiber_100g"])
    rng = np.random.default_rng(26)
    checks = {}

    # E. classifier spot-check (print first, store names)
    spot = {}
    for cat in CATS:
        names = df[(df["category"] == cat) & (df["group"] == "protein")]["name"]
        sample = list(names.sample(min(8, len(names)), random_state=26)) if len(names) else []
        spot[cat] = sample
        print(f"[{cat}] protein-branded sample: {sample}")
    checks["classifier_spot_check"] = spot

    # A. per-100g instead of per-100kcal
    checks["A_per_100g"] = pooled_diff(df, "fiber_100g")
    # B. drop fiber-named products
    no_fiber_named = df[~df["name"].str.lower().str.contains("fiber|fibre", na=False)]
    checks["B_drop_fiber_named"] = pooled_diff(no_fiber_named, "fiber_per_100kcal")
    checks["B_n_dropped"] = int(len(df) - len(no_fiber_named))
    # C. drop largest brand per category
    keep = []
    for cat in CATS:
        sub = df[df["category"] == cat]
        top = sub["brands"].value_counts().index[0]
        keep.append(sub[sub["brands"] != top])
        print(f"[{cat}] dropped top brand: {top!r} ({(sub['brands'] == top).sum()} products)")
    checks["C_drop_top_brand_per_category"] = pooled_diff(pd.concat(keep), "fiber_per_100kcal")
    # D. means instead of medians
    p = df[df["group"] == "protein"]["fiber_per_100kcal"]
    q = df[df["group"] == "plain"]["fiber_per_100kcal"]
    checks["D_means"] = {
        "protein_mean": round(float(p.mean()), 3),
        "plain_mean": round(float(q.mean()), 3),
        "pct_lower": round(100 * (q.mean() - p.mean()) / q.mean(), 1),
    }
    # main result, for reference
    checks["MAIN_per_100kcal"] = pooled_diff(df, "fiber_per_100kcal")

    # F. pasta exception: protein source
    pasta = df[(df["category"] == "pastas") & (df["group"] == "protein")].copy()
    legume = pasta["name"].str.lower().str.contains("chickpea|lentil|bean|pea|edamame", na=False)
    pasta["legume_based"] = legume
    if legume.sum() >= 5 and (~legume).sum() >= 5:
        checks["F_pasta_legume_vs_other"] = {
            "legume_n": int(legume.sum()),
            "legume_fiber_per_100kcal_med": round(float(pasta[legume]["fiber_per_100kcal"].median()), 3),
            "other_n": int((~legume).sum()),
            "other_fiber_per_100kcal_med": round(float(pasta[~legume]["fiber_per_100kcal"].median()), 3),
            "plain_pasta_fiber_per_100kcal_med": round(
                float(df[(df["category"] == "pastas") & (df["group"] == "plain")]["fiber_per_100kcal"].median()), 3
            ),
        }
    # per-category fiber gaps (for the README table)
    per_cat = {}
    for cat in CATS:
        sub = df[df["category"] == cat]
        per_cat[cat] = pooled_diff(sub, "fiber_per_100kcal")
    checks["per_category"] = per_cat

    with open(DATA / "checks.json", "w") as f:
        json.dump(checks, f, indent=2)
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
