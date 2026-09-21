"""Fetch BLS Average Price Data series from FRED (no API key needed via fredgraph.csv).
Series IDs: APU + area(0000 = U.S. city average) + BLS AP item code.
"""
import time
import pandas as pd
import requests
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

# (short_name, bls_item_code, bls_description, unit)
ITEMS = [
    ("flour_white", "701111", "Flour, white, all purpose", "lb"),
    ("rice_white", "701312", "Rice, white, long grain, uncooked", "lb"),
    ("spaghetti", "701322", "Spaghetti and macaroni", "lb"),
    ("bread_white", "702111", "Bread, white, pan", "lb"),
    ("ground_chuck", "703111", "Ground chuck, 100% beef", "lb"),
    ("ground_beef", "703112", "Ground beef, 100% beef", "lb"),
    ("ground_beef_lean", "703113", "Ground beef, lean and extra lean", "lb"),
    ("chuck_roast_choice", "703213", "Chuck roast, USDA Choice, boneless", "lb"),
    ("round_steak_choice", "703511", "Steak, round, USDA Choice, boneless", "lb"),
    ("sirloin_steak_choice", "703613", "Steak, sirloin, USDA Choice, boneless", "lb"),
    ("bacon", "704111", "Bacon, sliced", "lb"),
    ("pork_chops", "704211", "Chops, center cut, bone-in", "lb"),
    ("ham_boneless", "704312", "Ham, boneless, excluding canned", "lb"),
    ("sausage_fresh", "704421", "Sausage, fresh, loose", "lb"),
    ("frankfurters", "705111", "Frankfurters, all meat or all beef", "lb"),
    ("bologna", "705121", "Bologna, all beef or mixed", "lb"),
    ("chicken_whole", "706111", "Chicken, fresh, whole", "lb"),
    ("chicken_breast_bonein", "706211", "Chicken breast, bone-in", "lb"),
    ("chicken_legs", "706212", "Chicken legs, bone-in", "lb"),
    ("turkey_whole", "706311", "Turkey, frozen, whole", "lb"),
    ("tuna_light", "707111", "Tuna, light, chunk", "lb"),
    ("eggs_large", "708111", "Eggs, grade A, large", "doz"),
    ("milk_whole_gal", "709112", "Milk, fresh, whole, fortified", "gal"),
    ("milk_lowfat_gal", "709213", "Milk, fresh, low fat", "gal"),
    ("butter", "710111", "Butter, salted, grade AA, stick", "lb"),
    ("yogurt", "710122", "Yogurt, natural, fruit flavored", "8oz"),
    ("cheese_american", "710211", "American processed cheese", "lb"),
    ("cheese_cheddar", "710212", "Cheddar cheese, natural", "lb"),
    ("ice_cream", "710411", "Ice cream, prepackaged, bulk, regular", "halfgal"),
    ("potatoes", "712112", "Potatoes, white", "lb"),
    ("beans_dried", "714233", "Beans, dried, any type", "lb"),
    ("peanut_butter", "716141", "Peanut butter, creamy", "lb"),
    # composite / special item codes
    ("ground_beef_all", "FC1101", "All uncooked ground beef", "lb"),
    ("chicken_breast_boneless", "FF1101", "Chicken breast, boneless", "lb"),
    ("milk_all_gal", "FJ1101", "Milk, fresh, low-fat/reduced/skim", "gal"),
    ("yogurt_all", "FJ4101", "Yogurt", "8oz"),
]

def fetch_series(fred_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def main():
    meta = []
    all_series = {}
    for short, code, desc, unit in ITEMS:
        fred_id = f"APU0000{code}"
        try:
            text = fetch_series(fred_id)
            lines = [l for l in text.strip().splitlines() if l.strip()]
            if len(lines) < 3:  # header + maybe one row
                print(f"SKIP {fred_id} ({desc}): only {len(lines)} lines")
                continue
            df = pd.read_csv(pd.io.common.StringIO(text), parse_dates=["observation_date"])
            df = df.rename(columns={fred_id: "price"})
            df = df.dropna()
            all_series[short] = df
            latest = df.iloc[-1]
            meta.append({
                "short": short, "bls_item_code": code, "fred_id": fred_id,
                "description": desc, "unit": unit,
                "n_months": len(df),
                "first_month": df.iloc[0]["observation_date"].date().isoformat(),
                "latest_month": latest["observation_date"].date().isoformat(),
                "latest_price": round(float(latest["price"]), 4),
            })
            print(f"OK {fred_id} {desc}: {len(df)} months, latest {latest['observation_date'].date()} = {latest['price']}")
        except Exception as e:
            print(f"FAIL {fred_id} ({desc}): {e}")
        time.sleep(0.4)  # be polite to FRED

    os.makedirs(DATA, exist_ok=True)
    # long-format panel
    rows = []
    for short, df in all_series.items():
        for _, r in df.iterrows():
            rows.append({"item": short, "date": r["observation_date"].date().isoformat(),
                         "price": float(r["price"])})
    panel = pd.DataFrame(rows)
    panel.to_csv(os.path.join(DATA, "bls_prices_panel.csv"), index=False)
    pd.DataFrame(meta).to_csv(os.path.join(DATA, "bls_items_meta.csv"), index=False)
    print(f"\nSaved panel: {len(panel)} rows, {len(all_series)} items -> {DATA}")

if __name__ == "__main__":
    main()
