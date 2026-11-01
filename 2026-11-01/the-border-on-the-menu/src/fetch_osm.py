"""Fetch amenity=restaurant elements (tags only) for 16 city bboxes from
Overpass, splitting each city into a 2x2 tile grid: full-city queries timed
out on both default endpoints on 2026-11-01, so tiles keep each response
small. Elements are deduplicated by (type, id) across tiles and saved
untouched in structure under data/raw/.

v2 replaces the v1 single-query fetch (which failed for Vancouver).
"""
import json, time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

CITIES = [
    ("vancouver", "CA", 49.20, -123.22, 49.30, -123.02),
    ("toronto",   "CA", 43.60, -79.55, 43.85, -79.10),
    ("montreal",  "CA", 45.45, -73.95, 45.70, -73.50),
    ("calgary",   "CA", 50.95, -114.25, 51.15, -113.95),
    ("edmonton",  "CA", 53.40, -113.65, 53.65, -113.40),
    ("ottawa",    "CA", 45.30, -75.80, 45.50, -75.55),
    ("winnipeg",  "CA", 49.80, -97.30, 49.95, -97.05),
    ("halifax",   "CA", 44.60, -63.70, 44.72, -63.50),
    ("san-francisco", "US", 37.70, -122.52, 37.82, -122.36),
    ("los-angeles",   "US", 33.95, -118.45, 34.35, -118.15),
    ("new-york",      "US", 40.50, -74.25, 40.92, -73.70),
    ("seattle",       "US", 47.50, -122.42, 47.73, -122.24),
    ("boston",        "US", 42.28, -71.17, 42.40, -71.00),
    ("chicago",       "US", 41.65, -87.85, 42.02, -87.52),
    ("houston",       "US", 29.55, -95.78, 30.00, -95.10),
    ("portland",      "US", 45.43, -122.75, 45.60, -122.48),
]

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

def tiles(s, w, n, e):
    mid_lat, mid_lon = (s + n) / 2, (w + e) / 2
    return [(s, w, mid_lat, mid_lon), (s, mid_lon, mid_lat, e),
            (mid_lat, w, n, mid_lon), (mid_lat, mid_lon, n, e)]

def fetch_tile(s, w, n, e):
    q = (f"[out:json][timeout:180];"
         f"(node[\"amenity\"=\"restaurant\"]({s},{w},{n},{e});"
         f"way[\"amenity\"=\"restaurant\"]({s},{w},{n},{e});"
         f"relation[\"amenity\"=\"restaurant\"]({s},{w},{n},{e}););"
         f"out tags;")
    last = None
    for attempt in range(2):
        for ep in ENDPOINTS:
            try:
                r = requests.post(ep, data={"data": q},
                                  headers={"User-Agent": "MusingWithMike daily-build research"},
                                  timeout=200)
                if r.status_code == 200:
                    return r.json()["elements"], ep
                last = f"HTTP {r.status_code} from {ep}"
            except Exception as ex:  # noqa: BLE001
                last = f"{type(ex).__name__} from {ep}"
            time.sleep(3)
        time.sleep(10)
    raise RuntimeError(f"tile ({s},{w},{n},{e}) failed: {last}")

def main():
    log = []
    for slug, country, s, w, n, e in CITIES:
        out = RAW / f"osm_{slug}.json"
        if out.exists() and out.stat().st_size > 1000:
            print(f"skip {slug} (already fetched)", flush=True)
            log.append({"city": slug, "country": country, "status": "cached",
                        "elements": len(json.loads(out.read_text())["elements"])})
            continue
        print(f"fetching {slug} ...", flush=True)
        seen, merged = set(), []
        ok = True
        for ts, tw, tn, te in tiles(s, w, n, e):
            try:
                els, ep = fetch_tile(ts, tw, tn, te)
                for el in els:
                    k = (el["type"], el["id"])
                    if k not in seen:
                        seen.add(k)
                        merged.append(el)
                print(f"  {slug} tile ok: {len(els)} elements via {ep} (merged {len(merged)})", flush=True)
            except Exception as ex:  # noqa: BLE001
                print(f"  {slug} tile FAILED: {ex}", flush=True)
                ok = False
            time.sleep(3)
        if merged:
            out.write_text(json.dumps({"elements": merged}))
            print(f"  {slug}: saved {len(merged)} elements (all_tiles_ok={ok})", flush=True)
            log.append({"city": slug, "country": country, "status": "ok" if ok else "partial",
                        "elements": len(merged)})
        else:
            print(f"  {slug}: NO DATA", flush=True)
            log.append({"city": slug, "country": country, "status": "failed"})
        time.sleep(5)
    (RAW / "fetch_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))

if __name__ == "__main__":
    main()
