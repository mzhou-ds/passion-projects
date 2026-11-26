"""Clean raw Open Food Facts products into an analysis-ready table.

Classification (the treatment is the marketing, not the nutrient):
  - bars:    protein iff 'protein-bars' in categories_tags, plain iff 'cereal-bars'
  - all other categories: protein iff 'protein' appears in the product name
             or the labels carry a high-protein claim; plain otherwise.
             (The _protein fetch groups are only a sampling device.)

Outputs: data/clean_products.csv, data/clean_summary.json
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

HIGH_PROTEIN_LABELS = {"en:high-proteins", "en:rich-in-proteins", "en:source-of-proteins"}


def num(nutr, key):
    try:
        v = nutr.get(key)
        if v is None:
            return np.nan
        v = float(v)
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def classify(row):
    name = (row.get("product_name") or "").lower()
    cats = [c.lower() for c in (row.get("categories_tags") or [])]
    labels = [str(x).lower() for x in (row.get("labels_tags") or [])]
    group = row.get("_fetch_group", "")
    if group.startswith("bars_"):
        if "en:protein-bars" in cats or "protein-bars" in cats:
            return "protein"
        if "en:cereal-bars" in cats or "cereal-bars" in cats:
            return "plain"
        return None  # unclassifiable bar
    is_protein = ("protein" in name) or bool(
        set(labels) & {x.lower() for x in HIGH_PROTEIN_LABELS}
    )
    return "protein" if is_protein else "plain"


def category_of(row):
    group = row.get("_fetch_group", "")
    return group.replace("_protein", "").replace("_plain", "")


def main():
    rows = []
    with open(DATA / "raw_products.jsonl") as f:
        for line in f:
            rows.append(json.loads(line))
    print(f"raw products: {len(rows)}")

    recs, missing_fiber = [], {"protein": 0, "plain": 0}
    dropped = {"no_name_or_code": 0, "unclassifiable": 0, "bad_nutrients": 0}
    for r in rows:
        if not r.get("product_name") or not r.get("code"):
            dropped["no_name_or_code"] += 1
            continue
        cls = classify(r)
        if cls is None:
            dropped["unclassifiable"] += 1
            continue
        nutr = r.get("nutriments") or {}
        kcal = num(nutr, "energy-kcal_100g")
        protein = num(nutr, "proteins_100g")
        fiber = num(nutr, "fiber_100g")
        if pd.isna(kcal) or pd.isna(protein) or not (10 <= kcal <= 900) or not (0 <= protein <= 100):
            dropped["bad_nutrients"] += 1
            continue
        if pd.isna(fiber):
            missing_fiber[cls] += 1
        sugar = num(nutr, "sugars_100g")
        fat = num(nutr, "fat_100g")
        salt = num(nutr, "salt_100g")
        grade = (r.get("nutriscore_grade") or "").upper()
        recs.append(
            {
                "code": r["code"],
                "name": r["product_name"],
                "brands": r.get("brands") or "",
                "category": category_of(r),
                "group": cls,
                "kcal_100g": kcal,
                "protein_100g": protein,
                "fiber_100g": fiber,
                "sugars_100g": sugar,
                "fat_100g": fat,
                "salt_100g": salt,
                "nutriscore": grade if grade in "ABCDE" else np.nan,
                "nutriscore_num": "ABCDE".index(grade) + 1 if grade in "ABCDE" else np.nan,
            }
        )
    df = pd.DataFrame(recs)
    # derived quantities
    df["protein_kcal_share"] = df["protein_100g"] * 4 / df["kcal_100g"]
    df["protein_per_100kcal"] = df["protein_100g"] / df["kcal_100g"] * 100
    df["fiber_per_100kcal"] = df["fiber_100g"] / df["kcal_100g"] * 100
    df["fiber_source"] = df["fiber_100g"] >= 3.0  # EU 'source of fibre' threshold
    df["high_protein"] = df["protein_kcal_share"] >= 0.20  # EU 'high protein' threshold
    df["fiber_poor"] = df["fiber_100g"] < 3.0

    df.to_csv(DATA / "clean_products.csv", index=False)
    summary = {
        "n_raw": len(rows),
        "n_clean": len(df),
        "dropped": dropped,
        "missing_fiber_counts": missing_fiber,
        "by_category_group": {f"{k[0]}|{k[1]}": int(v) for k, v in df.groupby(["category", "group"]).size().items()},
        "missing_fiber_rate": {
            g: round(float(missing_fiber[g] / max(1, (df["group"] == g).sum() + missing_fiber[g])), 3)
            for g in ("protein", "plain")
        },
    }
    with open(DATA / "clean_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print(df.groupby(["category", "group"])["fiber_per_100kcal"].median())


if __name__ == "__main__":
    main()
