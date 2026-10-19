"""Extract a clean, current cross-section of US branded foods from the USDA
FoodData Central Global Branded Food Products Database (April 2025 release).

Streams the two big CSVs (never loads them whole), keeps 10 label nutrients,
keeps current US products only, and dedupes GTIN versions (latest modified).
Output: data/products.parquet  (gitignored; ~430k rows x nutrient columns,
amounts per 100 g as published, plus serving size so per-serving label
values can be reconstructed exactly as a shopper sees them).
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "products.parquet"

NUTRIENTS = {
    1008: "kcal", 1003: "protein_g", 1004: "fat_g", 1258: "satfat_g",
    1257: "transfat_g", 2000: "sugar_g", 1235: "added_sugar_g",
    1093: "sodium_mg", 1253: "cholesterol_mg", 1079: "fiber_g",
    1005: "carb_g", 1092: "potassium_mg",
}

def load_nutrients():
    parts = []
    for chunk in pd.read_csv(RAW / "food_nutrient.csv",
                             usecols=["fdc_id", "nutrient_id", "amount"],
                             chunksize=2_000_000):
        chunk = chunk[chunk["nutrient_id"].isin(NUTRIENTS)]
        if len(chunk):
            parts.append(chunk)
    long = pd.concat(parts, ignore_index=True)
    print(f"nutrient rows kept: {len(long):,}")
    wide = long.pivot_table(index="fdc_id", columns="nutrient_id",
                            values="amount", aggfunc="first")
    wide = wide.rename(columns=NUTRIENTS).reset_index()
    return wide

def load_branded():
    cols = ["fdc_id", "brand_owner", "gtin_upc", "serving_size",
            "serving_size_unit", "household_serving_fulltext",
            "branded_food_category", "market_country", "discontinued_date",
            "modified_date", "short_description"]
    parts = []
    for chunk in pd.read_csv(RAW / "branded_food.csv", usecols=cols,
                             chunksize=200_000, low_memory=False):
        chunk = chunk[chunk["market_country"] == "United States"]
        chunk = chunk[chunk["discontinued_date"].isna()]
        if len(chunk):
            parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)
    print(f"current US branded rows: {len(df):,}")
    # one row per GTIN: keep most recently modified version
    df["modified_date"] = pd.to_datetime(df["modified_date"], errors="coerce")
    df = df.sort_values("modified_date").drop_duplicates("gtin_upc", keep="last")
    print(f"after GTIN dedupe: {len(df):,}")
    return df

def main():
    nut = load_nutrients()
    br = load_branded()
    df = br.merge(nut, on="fdc_id", how="inner")
    print(f"merged products with nutrients: {len(df):,}")
    df["serving_size"] = pd.to_numeric(df["serving_size"], errors="coerce")
    df["serving_unit"] = df["serving_size_unit"].str.lower().str.strip()
    mass = df["serving_unit"].isin(["g", "ml", "mlt"]) & df["serving_size"].notna() \
        & (df["serving_size"] > 0)
    print(f"with gram/ml serving size: {mass.sum():,} ({100*mass.mean():.1f}%)")
    df = df[mass].copy()
    # reconstruct the declared per-serving label values
    f = df["serving_size"] / 100.0
    for c in ["kcal", "protein_g", "fat_g", "satfat_g", "transfat_g",
              "sugar_g", "added_sugar_g", "fiber_g", "carb_g"]:
        df[c + "_serv"] = df[c] * f
    for c in ["sodium_mg", "cholesterol_mg", "potassium_mg"]:
        df[c + "_serv"] = df[c] * f
    df["gtin_upc"] = df["gtin_upc"].astype(str)
    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT} rows={len(df):,}")
    print(df["branded_food_category"].value_counts().head(15))

if __name__ == "__main__":
    main()
