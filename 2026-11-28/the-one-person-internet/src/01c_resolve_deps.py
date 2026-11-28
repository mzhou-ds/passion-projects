"""Resolve the top-200 packages' direct dependencies that the search-query
pool missed (23 names, incl. @babel/parser and acorn). Fetches each by exact
search lookup (fresh requests.get + retries, per the repair pass), with a
metadata+downloads fallback, appends to the raw file, and rebuilds
data/packages.csv. Run once, then re-run 02_analysis.py and 03_charts.py.
"""
import csv
import json
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
META_URL = "https://registry.npmjs.org/{name}"
DL_URL = "https://api.npmjs.org/downloads/point/last-week/{name}"
UA = {"User-Agent": "musing-with-mike-npm-census/1.0 (research; github mzhou-ds)"}


def get_json(url, params=None, headers=None, tries=5, timeout=30):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(2 ** i + 0.5)
    raise last


def append_raw(obj):
    with open(DATA / "search_raw.jsonl", "a") as f:
        f.write(json.dumps(obj) + "\n")


def main():
    df = __import__("pandas").read_csv(DATA / "packages.csv").dropna(subset=["name"])
    pool = set(df["name"])
    deps = json.load(open(DATA / "deps_top200.json"))
    top200 = set(df.head(200)["name"])
    unres = sorted({c for k, v in deps.items() if k in top200
                    for c in v if c not in pool})
    print(f"unresolved deps: {len(unres)}")
    best = {}
    for name in unres:
        try:
            d = get_json(SEARCH_URL, params={"text": name, "size": 5}, headers=UA)
            hit = next((o for o in d.get("objects", [])
                        if o["package"]["name"] == name), None)
            if hit:
                best[name] = hit
                append_raw(hit)
                print(f"OK {name}: {hit['downloads']['weekly']:,} weekly, "
                      f"{len(hit['package'].get('maintainers') or [])} maintainers")
                continue
            print(f"NO-MATCH {name} -> fallback")
        except Exception as e:
            print(f"LOOKUP FAIL {name}: {str(e)[:100]} -> fallback")
        # fallback: full metadata + downloads API
        try:
            meta = get_json(META_URL.format(name=name), headers=UA)
            dl = get_json(DL_URL.format(name=name), headers=UA)
        except Exception as e:
            print(f"FALLBACK FAIL {name}: {str(e)[:100]} (skipped; not resolvable)")
            time.sleep(0.5)
            continue
        mods = meta.get("maintainers", [])
        times = meta.get("time", {})
        last = times.get("modified") or ""
        obj = {
            "package": {"name": name,
                        "version": (meta.get("dist-tags") or {}).get("latest", ""),
                        "description": (meta.get("description") or "")[:300],
                        "date": last,
                        "maintainers": [{"username": m.get("name", ""),
                                         "email": m.get("email", "")} for m in mods],
                        "publisher": {}, "license": meta.get("license") or ""},
            "downloads": {"weekly": dl.get("downloads", 0),
                          "monthly": dl.get("downloads", 0) * 4},
            "dependents": "0", "searchScore": None,
        }
        best[name] = obj
        append_raw(obj)
        print(f"FALLBACK OK {name}: {dl.get('downloads', 0):,} weekly, "
              f"{len(mods)} maintainers")
        time.sleep(0.5)

    # rebuild packages.csv from the full raw file
    all_best = {}
    with open(DATA / "search_raw.jsonl") as f:
        for line in f:
            obj = json.loads(line)
            nm = obj["package"]["name"]
            wk = (obj.get("downloads") or {}).get("weekly") or 0
            if nm not in all_best or wk > (all_best[nm].get("downloads") or {}).get("weekly", 0):
                all_best[nm] = obj
    rows = []
    for nm, obj in all_best.items():
        pkg = obj["package"]
        rows.append({
            "name": nm, "version": pkg.get("version"),
            "description": (pkg.get("description") or "")[:300],
            "weekly_downloads": (obj.get("downloads") or {}).get("weekly") or 0,
            "monthly_downloads": (obj.get("downloads") or {}).get("monthly") or 0,
            "dependents": int(obj.get("dependents") or 0),
            "last_publish": pkg.get("date"),
            "n_maintainers": len(pkg.get("maintainers") or []),
            "maintainers": ";".join(m.get("username", "")
                                     for m in (pkg.get("maintainers") or [])),
            "publisher": (pkg.get("publisher") or {}).get("username", ""),
            "license": pkg.get("license") or "",
            "search_score": obj.get("searchScore"),
        })
    rows.sort(key=lambda r: -r["weekly_downloads"])
    with open(DATA / "packages.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"packages.csv rows={len(rows)}")
    print("new top 15:", [r["name"] for r in rows[:15]])


if __name__ == "__main__":
    main()
