"""Thanksgiving coda: the holiday plate as a case study in the same trade.

Tries USDA FoodData Central (DEMO_KEY) for six classic dishes, falls back to
Open Food Facts US search if FDC is unreachable. Builds a typical plate
(150g turkey, 200g mashed potatoes, 100g stuffing, 60g cranberry sauce,
120g pumpkin pie, 100g green bean casserole) and reports its protein:fiber
ratio against the Dietary Guidelines reference (50g protein : 28g fiber
per 2,000 kcal, i.e. ~1.8:1).

Outputs: data/thanksgiving.json
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
UA = {"User-Agent": "MusingWithMike-Research/1.0 (passion-project)"}

PLATE = [
    ("turkey breast, roasted", 150),
    ("mashed potatoes", 200),
    ("stuffing", 100),
    ("cranberry sauce", 60),
    ("pumpkin pie", 120),
    ("green bean casserole", 100),
]


def fdc_search(query):
    url = ("https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&"
           + urllib.parse.urlencode({"query": query, "pageSize": 5, "dataType": "Foundation,SR Legacy"}))
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    for food in data.get("foods", []):
        nuts = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
        protein = nuts.get("Protein")
        fiber = nuts.get("Fiber, total dietary")
        if protein is not None and fiber is not None:
            return {"source": "USDA FDC", "food": food.get("description"),
                    "protein_100g": protein, "fiber_100g": fiber}
    return None


def off_search(query):
    url = ("https://world.openfoodfacts.org/api/v2/search?"
           + urllib.parse.urlencode({"search_terms": query, "countries_tags_en": "united-states",
                                     "fields": "product_name,nutriments", "page_size": 10,
                                     "sort_by": "unique_scans_n"}))
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    for p in data.get("products", []):
        n = p.get("nutriments") or {}
        if n.get("proteins_100g") is not None and n.get("fiber_100g") is not None:
            return {"source": "Open Food Facts", "food": p.get("product_name"),
                    "protein_100g": n["proteins_100g"], "fiber_100g": n["fiber_100g"]}
    return None


def main():
    items = []
    for query, grams in PLATE:
        hit = None
        for fn in (fdc_search, off_search):
            try:
                hit = fn(query)
            except Exception as e:  # noqa: BLE001
                print(f"  {query}: {fn.__name__} failed ({e})")
            if hit:
                break
            time.sleep(1)
        if not hit:
            print(f"  {query}: NO DATA")
            continue
        items.append({**hit, "query": query, "grams": grams,
                      "protein_g": round(hit["protein_100g"] * grams / 100, 1),
                      "fiber_g": round(hit["fiber_100g"] * grams / 100, 1)})
        print(f"  {query}: {hit['food']} ({hit['source']}) "
              f"{hit['protein_100g']}g protein / {hit['fiber_100g']}g fiber per 100g")
        time.sleep(1)
    total_protein = sum(i["protein_g"] for i in items)
    total_fiber = sum(i["fiber_g"] for i in items)
    result = {
        "items": items,
        "total_protein_g": round(total_protein, 1),
        "total_fiber_g": round(total_fiber, 1),
        "protein_fiber_ratio": round(total_protein / total_fiber, 2) if total_fiber else None,
        "dga_reference_ratio": round(50 / 28, 2),
        "fiber_as_pct_of_daily_target_women": round(100 * total_fiber / 25, 1),
        "fiber_as_pct_of_daily_target_men": round(100 * total_fiber / 38, 1),
    }
    with open(DATA / "thanksgiving.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
