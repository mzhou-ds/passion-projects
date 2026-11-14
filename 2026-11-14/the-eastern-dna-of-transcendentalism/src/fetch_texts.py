#!/usr/bin/env python3
"""Fetch public-domain texts for build #68. Uses curl (the egress proxy
drops requests.Session keep-alive connections; fresh curl calls work)."""
import json, os, subprocess, time

OUT = "/home/hatch/workspace/passion-projects/2026-11-14/the-eastern-dna-of-transcendentalism/data/raw"
os.makedirs(OUT, exist_ok=True)

QUERIES = {
    "walden":             "Walden Thoreau",
    "emerson_essays1":   "Essays First Series Emerson",
    "emerson_nature":    "Nature Emerson",
    "gita_arnold":       "Song Celestial Arnold",
    "upanishads_muller": "Upanishads Muller",
    "laws_manu":         "Laws of Manu Buhler",
    "vishnu_purana":     "Vishnu Purana Wilson",
    "kjv":               "King James Bible",
    "sartor":            "Sartor Resartus Carlyle",
}

def curl(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            r = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), "-A",
                                "MusingWithMike research build (non-commercial)",
                                "-w", "\n%{http_code}", url],
                               capture_output=True, text=True, timeout=timeout + 10)
            body, _, code = r.stdout.rpartition("\n")
            if code.strip() == "200" and body:
                return body
            print(f"  HTTP {code.strip()} for {url}", flush=True)
        except Exception as e:
            print(f"  try {i+1} failed: {e}", flush=True)
        time.sleep(4 * (i + 1))
    return None

def curl_bytes(url, path, tries=4, timeout=90):
    for i in range(tries):
        r = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), "-A",
                            "MusingWithMike research build (non-commercial)",
                            "-o", path, "-w", "%{http_code}", url],
                           capture_output=True, text=True, timeout=timeout + 10)
        if r.stdout.strip() == "200" and os.path.getsize(path) > 1000:
            return True
        print(f"  HTTP {r.stdout.strip()} for {url}", flush=True)
        time.sleep(4 * (i + 1))
    return False

manifest = {}
for key, q in QUERIES.items():
    print(f"resolving {key} ...", flush=True)
    body = curl(f"https://gutendex.com/books/?search={q.replace(' ', '%20')}")
    if not body:
        manifest[key] = {"error": "gutendex failed"}
        print("  !! gutendex failed", flush=True)
        continue
    data = json.loads(body)
    cands = data.get("results", [])
    pick = None
    for c in cands:
        fmts = c.get("formats", {})
        txt = fmts.get("text/plain; charset=utf-8") or fmts.get("text/plain")
        if txt:
            pick = (c["id"], c["title"], txt)
            break
    if not pick:
        manifest[key] = {"error": "no plain-text edition", "candidates": [c["id"] for c in cands]}
        print("  !! no plain-text edition", flush=True)
        continue
    gid, title, url = pick
    print(f"  -> #{gid} {title}", flush=True)
    path = os.path.join(OUT, f"{key}.txt")
    ok = curl_bytes(url, path)
    if not ok:
        manifest[key] = {"id": gid, "title": title, "error": "download failed"}
        print("  !! download failed", flush=True)
        continue
    manifest[key] = {"id": gid, "title": title, "url": url, "bytes": os.path.getsize(path)}
    print(f"  saved {os.path.getsize(path)} bytes", flush=True)
    time.sleep(2)

with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
print("DONE")
print(json.dumps({k: v.get("id", v) for k, v in manifest.items()}, indent=2))
