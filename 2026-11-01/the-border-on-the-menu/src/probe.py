"""Probe Overpass mirrors with one small node-only tile query each, detached."""
import time, requests

EPS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
Q = ("[out:json][timeout:60];"
     "node[\"amenity\"=\"restaurant\"](49.20,-123.22,49.25,-123.12);out tags;")
with open("/tmp/probe.log", "w") as f:
    for ep in EPS:
        t0 = time.time()
        try:
            r = requests.post(ep, data={"data": Q}, timeout=90,
                              headers={"User-Agent": "MusingWithMike probe"})
            n = len(r.json().get("elements", [])) if r.status_code == 200 else -1
            f.write(f"{ep} -> {r.status_code} {n} elements {time.time()-t0:.1f}s\n")
        except Exception as ex:  # noqa: BLE001
            f.write(f"{ep} -> {type(ex).__name__}: {str(ex)[:150]} {time.time()-t0:.1f}s\n")
        f.flush()
print("probe done")
