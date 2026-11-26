"""Fetch US products from Open Food Facts (api/v2/search) for the protein-vs-fiber study.

Lessons from the first attempt (2026-11-26):
  - OFF v2 search 503s frequently and seems to cap results at ~10 pages
    (two groups failed exactly at page 11). So: max 10 pages per group,
    2s between requests, and a failed page keeps the partial group instead
    of discarding it.
  - search_terms may or may not filter when combined with a category tag;
    classification happens in 02_clean.py by product name/labels anyway, so
    the _protein fetches are only enrichment. Duplicates collapse by code.

Categories (US market, most-scanned first so the sample reflects what people buy):
  protein-bars, cereal-bars, yogurts, breakfast-cereals, breads, pastas, cookies.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://world.openfoodfacts.org/api/v2/search"
UA = {"User-Agent": "MusingWithMike-Research/1.0 (passion-project; contact: michaelzhou96@gmail.com)"}
FIELDS = "code,product_name,brands,nutriments,nutriscore_grade,labels_tags,categories_tags,quantity"
PAGE_SIZE = 100
MAX_PAGES = 10
DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

# (group, category_tag, search_terms or None)
GROUPS = [
    ("bars_protein", "protein-bars", None),
    ("bars_plain", "cereal-bars", None),
    ("yogurts_protein", "yogurts", "protein"),
    ("yogurts_plain", "yogurts", None),
    ("cereals_protein", "breakfast-cereals", "protein"),
    ("cereals_plain", "breakfast-cereals", None),
    ("breads_protein", "breads", "protein"),
    ("breads_plain", "breads", None),
    ("pastas_protein", "pastas", "protein"),
    ("pastas_plain", "pastas", None),
    ("cookies_protein", "cookies", "protein"),
    ("cookies_plain", "cookies", None),
]


def fetch_page(params, tries=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "products" in data:
                return data
        except Exception as e:  # noqa: BLE001 - retry on any transient failure
            print(f"    attempt {attempt + 1} failed: {e}", flush=True)
        time.sleep(3 * (attempt + 1))
    return None  # give up on this page; caller keeps partial results


def fetch_group(group, category, search_terms):
    out, seen, page = [], set(), 1
    while page <= MAX_PAGES:
        params = {
            "categories_tags_en": category,
            "countries_tags_en": "united-states",
            "fields": FIELDS,
            "page_size": PAGE_SIZE,
            "page": page,
            "sort_by": "unique_scans_n",
        }
        if search_terms:
            params["search_terms"] = search_terms
        data = fetch_page(params)
        if data is None:
            print(f"  {group}: page {page} FAILED after retries, keeping {len(out)} so far", flush=True)
            break
        products = data.get("products", [])
        if not products:
            break
        for p in products:
            code = p.get("code")
            if code and code not in seen:
                seen.add(code)
                p["_fetch_group"] = group
                out.append(p)
        print(f"  {group}: page {page}, got {len(products)}, total {len(out)} "
              f"(of {data.get('count')})", flush=True)
        if len(products) < PAGE_SIZE:
            break
        page += 1
        time.sleep(2)
    return out


def main():
    all_products, log = [], {}
    raw_path = DATA / "raw_products.jsonl"
    raw_path.write_text("")  # incremental: each group is appended as it lands
    for group, category, terms in GROUPS:
        print(f"fetching {group} (category={category}, terms={terms})", flush=True)
        products = fetch_group(group, category, terms)
        log[group] = {"category": category, "search_terms": terms, "n": len(products)}
        with open(raw_path, "a") as f:
            for p in products:
                f.write(json.dumps(p) + "\n")
        all_products.extend(products)
        with open(DATA / "fetch_log.json", "w") as f:
            json.dump({"groups": log, "total_so_far": len(all_products)}, f, indent=2)
    dedup, seen = [], set()
    for p in all_products:
        if p["code"] not in seen:
            seen.add(p["code"])
            dedup.append(p)
    with open(raw_path, "w") as f:
        for p in dedup:
            f.write(json.dumps(p) + "\n")
    with open(DATA / "fetch_log.json", "w") as f:
        json.dump({"groups": log, "total_unique": len(dedup)}, f, indent=2)
    print(f"total unique products: {len(dedup)}", flush=True)
    print(json.dumps(log, indent=2), flush=True)


if __name__ == "__main__":
    main()
