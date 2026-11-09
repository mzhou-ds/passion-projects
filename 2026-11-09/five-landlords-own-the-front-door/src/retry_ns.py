"""Retry failed NS lookups sequentially with backoff, alternating DoH endpoints."""
import json, sys, time
import requests
sys.path.insert(0, "src")
from collect import classify_ns
from collect_ns import query_ns

raw = json.load(open("data/raw.json"))
failed = [r for r in raw["ns"] if r["error"]]
print("retrying", len(failed))
sess = requests.Session()
sess.headers.update({"User-Agent": "MusingWithMike-research/1.0 (academic measurement)"})
fixed = 0
for i, r in enumerate(failed):
    nss = query_ns(sess, r["domain"])
    if nss:
        provs = [classify_ns(ns) or "other" for ns in nss]
        r["ns"] = nss
        r["providers"] = provs
        r["provider"] = max(set(provs), key=provs.count)
        r["mixed"] = len(set(provs)) > 1
        r["error"] = None
        fixed += 1
    if i % 25 == 0:
        print(f"  {i}/{len(failed)} fixed={fixed}", flush=True)
    time.sleep(0.15)
print(f"fixed {fixed} of {len(failed)}")
json.dump(raw, open("data/raw.json", "w"), indent=1)
