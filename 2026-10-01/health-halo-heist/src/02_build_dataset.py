"""Build the analysis dataset from the sampled bulk TSV.

- Dedupes by product code
- Derives front-of-pack health-claim flags from labels_tags + product_name
- Picks a main category per product
Writes data/products.parquet + reference CSVs in output/.
"""
import re

import pandas as pd

SRC = "data/off_us_sample.tsv"
OUT = "data/products.parquet"


def strip_lang(tag):
    return re.sub(r"^[a-z]{2}:", "", tag or "").strip()


# claim -> (label predicate on stripped tag, name regex)
CLAIMS = {
    "organic": (lambda t: "organic" in t, r"\borganic\b"),
    "gluten_free": (lambda t: "gluten" in t and ("free" in t or t == "no-gluten"),
                    r"\bgluten[\s-]?free\b"),
    "high_protein": (lambda t: "protein" in t and "no-protein" not in t, r"\bprotein\b"),
    "low_fat": (lambda t: "fat" in t and any(w in t for w in ("low", "free", "reduced", "lite", "light")),
                r"\b(low[\s-]?fat|fat[\s-]?free|reduced[\s-]?fat)\b"),
    "low_sugar": (lambda t: "sugar" in t and any(w in t for w in ("no", "low", "free", "reduced", "less", "unsweetened", "zero")),
                  r"\b(no[\s-]?sugar|sugar[\s-]?free|low[\s-]?sugar|unsweetened|no[\s-]?added[\s-]?sugar)\b"),
    "natural": (lambda t: t in ("natural", "100-natural", "all-natural"), r"\ball[\s-]?natural\b"),
    "whole_grain": (lambda t: "whole-grain" in t or "whole grain" in t, r"\bwhole[\s-]?grain\b"),
    "keto": (lambda t: "keto" in t, r"\bketo(genic)?\b"),
    "paleo": (lambda t: "paleo" in t, r"\bpaleo\b"),
    "low_calorie": (lambda t: "calor" in t and any(w in t for w in ("low", "reduced", "free", "light", "lite")),
                    r"\b(low[\s-]?cal(orie)?s?|reduced[\s-]?cal)\b"),
    "non_gmo": (lambda t: "gmo" in t and t != "gmos" and any(w in t for w in ("no", "non")),
                r"\bnon[\s-]?gmo\b"),
    "vegan": (lambda t: "vegan" in t, r"\bvegan\b"),
    "high_fiber": (lambda t: ("fibre" in t or "fiber" in t),
                   r"\b(high[\s-]?fib(er|re)|fiber|fibre)\b"),
    "clean_label": (lambda t: "artificial" in t or t in ("no-preservatives",),
                    r"\bno\s+(artificial|preservatives)\b"),
    "heart_healthy": (lambda t: "heart" in t, r"\bheart[\s-]?healthy\b"),
    "low_sodium": (lambda t: "sodium" in t and any(w in t for w in ("low", "free", "reduced", "no")),
                   r"\blow[\s-]?sodium\b"),
}

NAME_RES = {k: re.compile(pat, re.I) for k, (_, pat) in CLAIMS.items()}


def claim_flags(labels, name):
    labels = labels if isinstance(labels, str) else ""
    name = name if isinstance(name, str) else ""
    tags = [strip_lang(t).lower() for t in labels.split(",")]
    name = name or ""
    return {
        f"claim_{claim}": any(lab_fn(t) for t in tags) or bool(NAME_RES[claim].search(name))
        for claim, (lab_fn, _p) in CLAIMS.items()
    }


def main():
    df = pd.read_csv(SRC, sep="\t", dtype=str).drop_duplicates("code")
    num_cols = ["energy-kcal_100g", "proteins_100g", "carbohydrates_100g", "sugars_100g",
                "fat_100g", "saturated-fat_100g", "fiber_100g", "sodium_100g", "salt_100g"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.rename(columns={c: c.replace("-", "_") for c in num_cols})
    df["nova_group"] = pd.to_numeric(df["nova_group"], errors="coerce")
    df["nutriscore"] = df["nutriscore_grade"].str.lower().str.strip().replace("", None)

    cats = df["categories_tags"].fillna("").str.split(",")
    df["main_category"] = cats.apply(lambda ts: strip_lang(ts[-1]) if ts and ts[0] else None)
    df["top_category"] = cats.apply(lambda ts: strip_lang(ts[0]) if ts and ts[0] else None)

    flags = df.apply(lambda r: claim_flags(r["labels_tags"], r["product_name"]), axis=1, result_type="expand")
    df = pd.concat([df, flags], axis=1)
    claim_cols = [c for c in df.columns if c.startswith("claim_")]
    df["n_claims"] = df[claim_cols].sum(axis=1)
    df["nutri_points"] = df["nutriscore"].map({"a": 5, "b": 4, "c": 3, "d": 2, "e": 1})
    df["is_upf"] = (df["nova_group"] == 4)

    # sanity: drop absurd energy values
    df.loc[(df["energy_kcal_100g"] > 950) | (df["energy_kcal_100g"] < 0), "energy_kcal_100g"] = None

    keep = ["code", "product_name", "brands", "main_category", "top_category",
            "nova_group", "nutriscore", "nutri_points", "is_upf", "n_claims",
            "energy_kcal_100g", "proteins_100g", "carbohydrates_100g", "sugars_100g",
            "fat_100g", "saturated_fat_100g", "fiber_100g", "sodium_100g", "salt_100g"] + claim_cols
    df[keep].to_parquet(OUT, index=False)
    print(f"{len(df):,} products -> {OUT}")
    print("nova coverage:", df["nova_group"].notna().mean().round(3))
    print("nutriscore coverage:", df["nutriscore"].notna().mean().round(3))
    print("products with >=1 claim:", (df["n_claims"] > 0).mean().round(3))
    print("\nclaim prevalence (%):")
    print((df[claim_cols].mean().sort_values(ascending=False) * 100).round(1).to_string())
    df[claim_cols].mean().sort_values(ascending=False).to_csv("output/claim_prevalence.csv")
    df["main_category"].value_counts().head(80).to_csv("output/top_categories.csv")


if __name__ == "__main__":
    main()
