"""Fetch ~60k US products from the Open Food Facts API (v2).

Source: Open Food Facts (https://world.openfoodfacts.org) — open database of
food products (ODbL). The `us.` subdomain scopes the search to US products.
Products are returned in popularity order, so the sample represents what
people actually buy. Please see the README for full methodology and
limitations (crowd-sourced data, incomplete fields).

Usage: python3 01_fetch.py
Writes: /tmp/off_raw.jsonl (deleted after 02_build_dataset.py builds the parquet)
"""
import json
import time

import requests

UA = "MusingWithMike/1.0 (daily nutrition research; https://github.com/mzhou-ds/passion-projects)"
BASE = "https://us.openfoodfacts.org/api/v2/search"
FIELDS = ",".join(
    [
        "code",
        "product_name",
        "brands",
        "categories_tags",
        "labels_tags",
        "nutriscore_grade",
        "nova_group",
        "nutriments.energy-kcal_100g",
        "nutriments.proteins_100g",
        "nutriments.carbohydrates_100g",
        "nutriments.sugars_100g",
        "nutriments.fat_100g",
        "nutriments.saturated-fat_100g",
        "nutriments.fiber_100g",
        "nutriments.sodium_100g",
        "nutriments.salt_100g",
    ]
)
PAGE_SIZE = 1000
MAX_PAGES = 60
OUT = "/tmp/off_raw.jsonl"
SLEEP = 0.8


def main():
    seen = 0
    with open(OUT, "w") as f:
        for page in range(1, MAX_PAGES + 1):
            params = {"page": page, "page_size": PAGE_SIZE, "fields": FIELDS}
            for attempt in range(4):
                try:
                    r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=60)
                    r.raise_for_status()
                    data = r.json()
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"page {page}: attempt {attempt + 1} failed: {e}")
                    time.sleep(3 * (attempt + 1))
            else:
                print(f"page {page}: giving up, stopping")
                break
            prods = data.get("products", [])
            if not prods:
                print(f"page {page}: empty, stopping")
                break
            for p in prods:
                f.write(json.dumps(p) + "\n")
                seen += 1
            print(f"page {page}: +{len(prods)} (total {seen})", flush=True)
            time.sleep(SLEEP)
    print(f"done: {seen} raw records -> {OUT}")


if __name__ == "__main__":
    main()
