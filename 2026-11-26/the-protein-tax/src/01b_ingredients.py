"""Supplementary fetch: ingredient lists for a sample of bars, to test whether
the fiber in protein bars is mostly added isolated fiber (chicory root fiber,
inulin, soluble corn fiber, polydextrose) rather than whole-food fiber.

Fetches the 100 most-scanned protein bars and 100 most-scanned plain cereal
bars with ingredients_text. Outputs data/bar_ingredients.jsonl.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://world.openfoodfacts.org/api/v2/search"
UA = {"User-Agent": "MusingWithMike-Research/1.0 (passion-project; contact: michaelzhou96@gmail.com)"}
DATA = Path(__file__).resolve().parent.parent / "data"


def fetch(params, tries=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "products" in data:
                return data
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt + 1} failed: {e}", flush=True)
        time.sleep(3 * (attempt + 1))
    return None


def main():
    out = []
    for group, category in (("bars_protein", "protein-bars"), ("bars_plain", "cereal-bars")):
        data = fetch({
            "categories_tags_en": category,
            "countries_tags_en": "united-states",
            "fields": "code,product_name,ingredients_text,nutriments",
            "page_size": 100,
            "page": 1,
            "sort_by": "unique_scans_n",
        })
        if data is None:
            print(f"{group}: FAILED", flush=True)
            continue
        for p in data.get("products", []):
            p["_fetch_group"] = group
            out.append(p)
        print(f"{group}: got {len(data.get('products', []))}", flush=True)
        time.sleep(2)
    with open(DATA / "bar_ingredients.jsonl", "w") as f:
        for p in out:
            f.write(json.dumps(p) + "\n")
    print(f"total: {len(out)}", flush=True)


if __name__ == "__main__":
    main()
