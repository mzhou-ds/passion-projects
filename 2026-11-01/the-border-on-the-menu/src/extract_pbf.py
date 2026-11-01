"""Extract amenity=restaurant elements from BBBike city PBF extracts,
clipped to the same city-core bboxes as the (failed) Overpass fetch.

BBBike extracts are metro-wide, so every element is filtered to the core
bbox by node location (ways: centroid of member nodes). Output mirrors the
Overpass JSON shape ({"elements": [...]}) so 02_analysis.py runs unchanged.

Overpass was abandoned on 2026-11-01: all four mirrors timed out even on a
tiny node-only tile query (90s+), and full-city queries never completed.
"""
import json
from pathlib import Path
import osmium

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PBF = BASE / "data" / "pbf"
RAW.mkdir(parents=True, exist_ok=True)

# BBBike has no Edmonton/Winnipeg extracts; use Geofabrik province files.
PBF_OVERRIDE = {"edmonton": "alberta.osm.pbf", "winnipeg": "manitoba.osm.pbf",
                "boston": "massachusetts.osm.pbf", "houston": "texas.osm.pbf"}
CITIES = [
    ("vancouver", "CA", "Vancouver", 49.20, -123.22, 49.30, -123.02),
    ("toronto",   "CA", "Toronto",   43.60, -79.55, 43.85, -79.10),
    ("montreal",  "CA", "Montreal",  45.45, -73.95, 45.70, -73.50),
    ("calgary",   "CA", "Calgary",   50.95, -114.25, 51.15, -113.95),
    ("edmonton",  "CA", "Edmonton",  53.40, -113.65, 53.65, -113.40),
    ("ottawa",    "CA", "Ottawa",    45.30, -75.80, 45.50, -75.55),
    ("winnipeg",  "CA", "Winnipeg",  49.80, -97.30, 49.95, -97.05),
    ("halifax",   "CA", "Halifax",   44.60, -63.70, 44.72, -63.50),
    ("san-francisco", "US", "SanFrancisco", 37.70, -122.52, 37.82, -122.36),
    ("los-angeles",   "US", "LosAngeles",   33.95, -118.45, 34.35, -118.15),
    ("new-york",      "US", "NewYork",      40.50, -74.25, 40.92, -73.70),
    ("seattle",       "US", "Seattle",      47.50, -122.42, 47.73, -122.24),
    ("boston",        "US", "Boston",       42.28, -71.17, 42.40, -71.00),
    ("chicago",       "US", "Chicago",      41.65, -87.85, 42.02, -87.52),
    ("houston",       "US", "Houston",      29.55, -95.78, 30.00, -95.10),
    ("portland",      "US", "Portland",     45.43, -122.75, 45.60, -122.48),
]

class RestaurantHandler(osmium.SimpleHandler):
    def __init__(self, s, w, n, e):
        super().__init__()
        self.s, self.w, self.n, self.e = s, w, n, e
        self.out = []

    def _in(self, lat, lon):
        return self.s <= lat <= self.n and self.w <= lon <= self.e

    def node(self, nd):
        if nd.tags.get("amenity") != "restaurant":
            return
        if nd.location.valid() and self._in(nd.location.lat, nd.location.lon):
            self.out.append({"type": "node", "id": nd.id,
                             "tags": dict(nd.tags)})

    def way(self, wy):
        if wy.tags.get("amenity") != "restaurant":
            return
        lats, lons = [], []
        for nd in wy.nodes:
            if nd.location.valid():
                lats.append(nd.location.lat)
                lons.append(nd.location.lon)
        if lats and self._in(sum(lats) / len(lats), sum(lons) / len(lons)):
            self.out.append({"type": "way", "id": wy.id,
                             "tags": dict(wy.tags)})

def main():
    import sys
    wanted = set(sys.argv[1:]) or None
    log = []
    for slug, country, bb, s, w, n, e in CITIES:
        if wanted and slug not in wanted:
            continue
        pbf = PBF / PBF_OVERRIDE.get(slug, f"{bb}.osm.pbf")
        out = RAW / f"osm_{slug}.json"
        if out.exists() and out.stat().st_size > 1000:
            print(f"skip {slug} (already extracted)", flush=True)
            log.append({"city": slug, "country": country, "status": "cached",
                        "elements": len(json.loads(out.read_text())["elements"])})
            continue
        if not pbf.exists():
            print(f"skip {slug}: no PBF {pbf}", flush=True)
            log.append({"city": slug, "country": country, "status": "no-pbf"})
            continue
        h = RestaurantHandler(s, w, n, e)
        h.apply_file(str(pbf), locations=True, idx="sparse_mem_array")
        out.write_text(json.dumps({"elements": h.out}))
        print(f"{slug}: {len(h.out)} restaurants in core bbox", flush=True)
        log.append({"city": slug, "country": country, "status": "ok",
                    "elements": len(h.out), "extract": bb})
    (RAW / "fetch_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))

if __name__ == "__main__":
    main()
