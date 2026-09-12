"""Build the wide per-food nutrient matrix from the SR Legacy CSVs.

Reads data/FoodData_Central_sr_legacy_food_csv_2018-04/*.csv and writes
output/foods_wide.csv: one row per food, one column per nutrient of interest
(all values per 100 g), plus the food category name.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "FoodData_Central_sr_legacy_food_csv_2018-04"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

# nutrient_id -> short column name
NUTRIENTS = {
    1008: "kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carb_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1258: "satfat_g",
    1093: "sodium_mg",
    1092: "potassium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1162: "vitc_mg",
    1106: "vita_mcg",
    1177: "folate_mcg",
    1210: "trp_g",
    1211: "thr_g",
    1212: "ile_g",
    1213: "leu_g",
    1214: "lys_g",
    1215: "met_g",
    1219: "val_g",
    1051: "water_g",
    1253: "chol_mg",
}


def main():
    food = pd.read_csv(RAW / "food.csv")
    cat = pd.read_csv(RAW / "food_category.csv")
    fn = pd.read_csv(RAW / "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])

    print(f"foods: {len(food):,}; nutrient records: {len(fn):,}")
    fn = fn[fn["nutrient_id"].isin(NUTRIENTS)]
    wide = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
    wide.columns = [NUTRIENTS[c] for c in wide.columns]
    wide = wide.reset_index()

    df = food.merge(wide, on="fdc_id", how="left")
    df = df.merge(cat[["id", "description"]].rename(
        columns={"id": "food_category_id", "description": "category"}),
        on="food_category_id", how="left")

    df = df[["fdc_id", "description", "category"] + list(NUTRIENTS.values())]
    df.to_csv(OUT / "foods_wide.csv", index=False)
    print(f"wrote {OUT / 'foods_wide.csv'}: {df.shape}")

    # coverage report for the key nutrients
    cov = df[list(NUTRIENTS.values())].notna().mean().sort_values(ascending=False)
    print("\ncoverage (fraction of foods with a value):")
    print(cov.round(3).to_string())


if __name__ == "__main__":
    main()
