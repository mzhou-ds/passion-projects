"""Build the protein-arbitrage dataset: USDA nutrition x BLS prices -> cost per protein.

Sources:
  - Prices: BLS Average Price Data (APU series), U.S. city average, via FRED fredgraph.csv.
  - Nutrition: USDA FoodData Central SR Legacy (April 2018), public domain, per 100 g.

Outputs data/protein_table.csv with one row per food.
"""
import pandas as pd
import numpy as np
import os

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "..", "data")
SR = os.path.join(D, "sr_legacy", "FoodData_Central_sr_legacy_food_csv_2018-04")

# BLS item -> (fdc_id, usda description, bls unit)
MAP = {
    "flour_white":         (168894, "Wheat flour, white, all-purpose, enriched, bleached", "lb"),
    "rice_white":          (168877, "Rice, white, long-grain, regular, raw, enriched", "lb"),
    "spaghetti":           (169736, "Pasta, dry, enriched", "lb"),
    "bread_white":         (174924, "Bread, white, commercially prepared", "lb"),
    "ground_chuck":        (174036, "Beef, ground, 80% lean meat / 20% fat, raw", "lb"),
    "ground_beef":         (174036, "Beef, ground, 80% lean meat / 20% fat, raw", "lb"),
    "ground_beef_lean":    (174030, "Beef, ground, 90% lean meat / 10% fat, raw", "lb"),
    "chuck_roast_choice":  (168668, "Beef, chuck, arm pot roast, separable lean and fat, trimmed to 1/8 in fat, choice, raw", "lb"),
    "round_steak_choice":  (168712, "Beef, round, top round steak, separable lean and fat, trimmed to 1/8 in fat, select, raw [grade subst.]", "lb"),
    "sirloin_steak_choice":(168726, "Beef, top sirloin steak, separable lean and fat, trimmed to 1/8 in fat, all grades, raw [grade subst.]", "lb"),
    "bacon":               (168277, "Pork, cured, bacon, unprepared", "lb"),
    "pork_chops":          (167829, "Pork, fresh, loin, center loin (chops), bone-in, separable lean only, raw", "lb"),
    "ham_boneless":        (168296, "Pork, cured, ham, boneless, extra lean and regular, roasted", "lb"),
    "chicken_whole":       (171447, "Chicken, broilers or fryers, meat and skin, raw", "lb"),
    "chicken_breast_boneless": (171077, "Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw", "lb"),
    "chicken_legs":        (172378, "Chicken, broilers or fryers, leg, meat and skin, raw", "lb"),
    "eggs_large":          (171287, "Egg, whole, raw, fresh", "doz"),
    "milk_whole_gal":      (171265, "Milk, whole, 3.25% milkfat, with added vitamin D", "gal"),
    "milk_all_gal":        (171267, "Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and D", "gal"),
    "yogurt_all":          (171284, "Yogurt, plain, whole milk", "8oz"),
    "cheese_american":     (171290, "Cheese, pasteurized process, American, without added vitamin D", "lb"),
    "cheese_cheddar":      (173414, "Cheese, cheddar", "lb"),
    "ice_cream":           (167575, "Ice creams, vanilla", "halfgal"),
    "potatoes":            (170028, "Potatoes, white, flesh and skin, raw", "lb"),
    "beans_dried":         (175199, "Beans, pinto, mature seeds, raw", "lb"),
    # discontinued BLS series - kept for reference, flagged with vintage
    "peanut_butter":       (174266, "Peanut butter, smooth style, with salt [BLS series ended Dec 2017]", "lb"),
    "tuna_light":          (173709, "Fish, tuna, light, canned in water, drained solids [BLS series ended Sep 2017]", "lb"),
}

LB_G = 453.592
# grams of product per BLS pricing unit
UNIT_G = {"lb": LB_G, "doz": 12 * 50.0, "gal": 3785.41 * 1.03,
          "8oz": 226.796, "halfgal": 1892.7 * 0.60}
BONE_IN = {"pork_chops", "chicken_whole", "chicken_legs"}


def load_nutrition():
    fn = pd.read_csv(os.path.join(SR, "food_nutrient.csv"), low_memory=False)
    # nutrient ids: 1003 protein g, 1008 energy kcal, 1004 fat g, 1005 carbs g
    fn = fn[fn["nutrient_id"].isin([1003, 1008, 1004, 1005])]
    piv = fn.pivot_table(index="fdc_id", columns="nutrient_id",
                         values="amount", aggfunc="mean")
    piv = piv.rename(columns={1003: "protein_g_per_100g", 1008: "kcal_per_100g",
                              1004: "fat_g_per_100g", 1005: "carbs_g_per_100g"})
    return piv


def main():
    nut = load_nutrition()
    meta = pd.read_csv(os.path.join(D, "bls_items_meta.csv"))
    panel = pd.read_csv(os.path.join(D, "bls_prices_panel.csv"), parse_dates=["date"])

    rows = []
    for item, (fdc, desc, unit) in MAP.items():
        m = meta[meta["short"] == item]
        if m.empty:
            print(f"WARN no BLS series for {item}")
            continue
        m = m.iloc[0]
        p = panel[panel["item"] == item].sort_values("date")
        latest = p.iloc[-1]
        price, pdate = float(latest["price"]), latest["date"].date().isoformat()
        current = pdate >= "2026-01-01"
        try:
            n = nut.loc[fdc]
        except KeyError:
            print(f"WARN no nutrition for fdc {fdc} ({item})")
            continue
        prot100, kcal100 = float(n["protein_g_per_100g"]), float(n["kcal_per_100g"])
        fat100 = float(n["fat_g_per_100g"]) if pd.notna(n["fat_g_per_100g"]) else np.nan
        grams_per_unit = UNIT_G[unit]
        protein_per_unit = prot100 / 100.0 * grams_per_unit
        kcal_per_unit = kcal100 / 100.0 * grams_per_unit
        cost_per_30g_protein = price / protein_per_unit * 30.0
        protein_density = prot100 / kcal100 * 100.0  # g protein per 100 kcal
        rows.append({
            "item": item, "label": m["description"], "bls_unit": unit,
            "price_usd": round(price, 3), "price_month": pdate, "price_current": current,
            "fdc_id": fdc, "usda_desc": desc,
            "protein_g_per_100g": round(prot100, 2), "kcal_per_100g": round(kcal100, 1),
            "fat_g_per_100g": round(fat100, 2) if pd.notna(fat100) else None,
            "grams_per_unit": round(grams_per_unit, 1),
            "protein_g_per_unit": round(protein_per_unit, 1),
            "cost_per_30g_protein_usd": round(cost_per_30g_protein, 3),
            "protein_g_per_100kcal": round(protein_density, 2),
            "bone_in": item in BONE_IN,
        })
    df = pd.DataFrame(rows).sort_values("cost_per_30g_protein_usd")
    df.to_csv(os.path.join(D, "protein_table.csv"), index=False)
    print(df[["label", "price_usd", "bls_unit", "price_month",
              "protein_g_per_100g", "cost_per_30g_protein_usd"]].to_string(index=False))
    print(f"\nSaved {len(df)} rows.")


if __name__ == "__main__":
    main()
