"""Print USDA SR Legacy candidate foods for each BLS item to finalize the mapping."""
import pandas as pd
import os

D = os.path.join(os.path.dirname(__file__), "..", "data", "sr_legacy",
                 "FoodData_Central_sr_legacy_food_csv_2018-04")
food = pd.read_csv(os.path.join(D, "food.csv"))
food["description"] = food["description"].astype(str)

QUERIES = {
    "flour_white": ["wheat flour, white, all-purpose"],
    "rice_white": ["rice, white, long-grain, regular, raw"],
    "spaghetti": ["spaghetti, dry", "macaroni, dry"],
    "bread_white": ["bread, white, commercially prepared"],
    "ground_chuck": ["beef, ground, 80% lean"],
    "ground_beef": ["beef, ground, 80% lean"],
    "ground_beef_lean": ["beef, ground, 90% lean"],
    "chuck_roast_choice": ["beef, chuck, arm pot roast"],
    "round_steak_choice": ["beef, round, top round steak"],
    "sirloin_steak_choice": ["beef, top sirloin, steak"],
    "bacon": ["pork, cured, bacon, raw"],
    "pork_chops": ["pork, fresh, loin, center loin"],
    "ham_boneless": ["pork, cured, ham, boneless"],
    "chicken_whole": ["chicken, broilers or fryers, meat and skin, raw"],
    "chicken_breast_boneless": ["chicken, broilers or fryers, breast, meat only, raw"],
    "chicken_legs": ["chicken, broilers or fryers, leg, meat and skin, raw"],
    "tuna_light": ["tuna, light, canned in water"],
    "eggs_large": ["egg, whole, raw, fresh"],
    "milk_whole_gal": ["milk, whole, 3.25%"],
    "milk_all_gal": ["milk, reduced fat, fluid, 2%"],
    "butter": ["butter, salted"],
    "yogurt_all": ["yogurt, plain, whole milk"],
    "cheese_american": ["cheese, pasteurized process, american"],
    "cheese_cheddar": ["cheese, cheddar"],
    "ice_cream": ["ice creams, vanilla"],
    "potatoes": ["potatoes, white, flesh and skin, raw"],
    "beans_dried": ["beans, pinto, mature seeds, raw"],
    "peanut_butter": ["peanut butter, smooth"],
}

def norm(s):
    return s.lower().replace(",", " ").replace("  ", " ")

for item, queries in QUERIES.items():
    print(f"\n=== {item} ===")
    shown = set()
    for q in queries:
        toks = [t for t in norm(q).split() if len(t) > 2]
        mask = pd.Series(True, index=food.index)
        for t in toks:
            mask &= food["description"].str.lower().str.contains(t, na=False)
        cands = food[mask]
        for _, r in cands.head(6).iterrows():
            if r["fdc_id"] not in shown:
                shown.add(r["fdc_id"])
                print(f"  {r['fdc_id']}: {r['description'][:110]}")
        if len(shown) >= 6:
            break
