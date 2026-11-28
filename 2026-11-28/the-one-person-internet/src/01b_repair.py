"""Repair pass for the npm census fetch (01_fetch.py).

The first pass hit intermittent egress-proxy disconnects (RemoteDisconnected)
on ~half the search queries and half the metadata fetches. Lesson from this
workspace (see AGENTS.md): requests.Session keep-alive connections hang
against the egress proxy. This script therefore uses a FRESH requests.get
per call, with up to 5 tries and exponential backoff, and only fetches what
is still missing:

  1. re-run the failed search queries (parsed from data/fetch_log.txt)
  2. re-run exact-name lookups for validation packages still missing
  3. rebuild data/packages.csv from the enlarged raw file
  4. fetch abbreviated metadata for any top-200 package missing from
     data/deps_top200.json
  5. last resort for a package the search API will not return: full
     registry metadata (maintainers + modified) + downloads API (weekly)

Appends to data/search_raw.jsonl; rewrites data/packages.csv,
data/deps_top200.json, data/deps_unique.txt; appends to data/fetch_log.txt.
"""
import csv
import json
import re
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
META_URL = "https://registry.npmjs.org/{name}"
DL_URL = "https://api.npmjs.org/downloads/point/last-week/{name}"
HEADERS_META = {
    "Accept": "application/vnd.npm.install-v1+json",
    "User-Agent": "musing-with-mike-npm-census/1.0 (research; github mzhou-ds)",
}
UA = {"User-Agent": "musing-with-mike-npm-census/1.0 (research; github mzhou-ds)"}

LOG = []


def get_json(url, params=None, headers=None, tries=5, timeout=30):
    """Fresh requests.get per attempt; exponential backoff on any failure."""
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
    log_text = (DATA / "fetch_log.txt").read_text()
    failed_queries = sorted(set(re.findall(r"QUERY FAIL (\S+):", log_text)))
    LOG.append(f"failed_queries_to_retry={len(failed_queries)}")

    # ---- 1. re-run failed queries
    ok_q, fail_q = 0, []
    for q in failed_queries:
        try:
            d = get_json(SEARCH_URL, params={"text": q, "size": 250}, headers=UA)
            for obj in d.get("objects", []):
                append_raw(obj)
            ok_q += 1
        except Exception as e:
            fail_q.append(q)
            LOG.append(f"RETRY QUERY FAIL {q}: {str(e)[:120]}")
        time.sleep(0.6)
    LOG.append(f"retried_queries ok={ok_q} still_failing={fail_q}")

    # ---- rebuild pool
    best = {}
    with open(DATA / "search_raw.jsonl") as f:
        for line in f:
            obj = json.loads(line)
            name = obj["package"]["name"]
            wk = (obj.get("downloads") or {}).get("weekly") or 0
            if name not in best or wk > (best[name].get("downloads") or {}).get("weekly", 0):
                best[name] = obj
    LOG.append(f"unique_packages_after_query_repair={len(best)}")

    # ---- 2. validation lookups for still-missing giants
    import importlib.util
    spec = importlib.util.spec_from_file_location("fetch", BASE / "src" / "01_fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [n for n in mod.VALIDATION if n not in best]
    LOG.append(f"validation_still_missing={len(missing)}: {missing}")
    for name in missing:
        try:
            d = get_json(SEARCH_URL, params={"text": name, "size": 5}, headers=UA)
            hit = next((o for o in d.get("objects", [])
                        if o["package"]["name"] == name), None)
            if hit:
                best[name] = hit
                append_raw(hit)
                LOG.append(f"LOOKUP OK {name}")
            else:
                LOG.append(f"LOOKUP NO-MATCH {name} -> metadata+downloads fallback")
                fallback(name, best)
        except Exception as e:
            LOG.append(f"LOOKUP FAIL {name}: {str(e)[:120]} -> fallback")
            fallback(name, best)
        time.sleep(0.6)

    # ---- 3. rebuild packages.csv
    rows = []
    for name, obj in best.items():
        pkg = obj["package"]
        rows.append({
            "name": name,
            "version": pkg.get("version"),
            "description": (pkg.get("description") or "")[:300],
            "weekly_downloads": (obj.get("downloads") or {}).get("weekly") or 0,
            "monthly_downloads": (obj.get("downloads") or {}).get("monthly") or 0,
            "dependents": int(obj.get("dependents") or 0),
            "last_publish": pkg.get("date"),
            "n_maintainers": len(pkg.get("maintainers") or []),
            "maintainers": ";".join(m.get("username", "") for m in (pkg.get("maintainers") or [])),
            "publisher": (pkg.get("publisher") or {}).get("username", ""),
            "license": pkg.get("license") or "",
            "search_score": obj.get("searchScore"),
        })
    rows.sort(key=lambda r: -r["weekly_downloads"])
    with open(DATA / "packages.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    LOG.append(f"packages.csv rows={len(rows)} top={rows[0]['name']} "
               f"{rows[0]['weekly_downloads']:,} weekly")

    # ---- 4. metadata for top-200 packages missing from deps file
    deps_path = DATA / "deps_top200.json"
    deps = json.loads(deps_path.read_text()) if deps_path.exists() else {}
    top200 = [r["name"] for r in rows[:200]]
    need = [n for n in top200 if n not in deps]
    LOG.append(f"deps_top200 already_have={len(deps)} need={len(need)}")
    for name in need:
        try:
            d = get_json(META_URL.format(name=name), headers=HEADERS_META)
            latest = d["dist-tags"]["latest"]
            deps[name] = sorted((d["versions"][latest].get("dependencies") or {}).keys())
        except Exception as e:
            LOG.append(f" META RETRY FAIL {name}: {str(e)[:120]}")
        time.sleep(0.4)
    deps_path.write_text(json.dumps(deps, indent=1))
    uniq = sorted({d for v in deps.values() for d in v})
    (DATA / "deps_unique.txt").write_text("\n".join(uniq))
    LOG.append(f"deps final: parents={len(deps)} edges={sum(len(v) for v in deps.values())} "
               f"unique_deps={len(uniq)}")

    with open(DATA / "fetch_log.txt", "a") as f:
        f.write("\n--- REPAIR PASS ---\n" + "\n".join(LOG) + "\n")
    print("\n".join(LOG))


def fallback(name, best):
    """Search API won't return this package: build a record from the full
    registry metadata (maintainers, modified) + the downloads API."""
    try:
        meta = get_json(META_URL.format(name=name),
                        headers={"User-Agent": UA["User-Agent"]})
        dl = get_json(DL_URL.format(name=name), headers=UA)
        wk = dl.get("downloads", 0)
        mods = meta.get("maintainers", [])
        times = meta.get("time", {})
        last = times.get("modified") or times.get(meta.get("dist-tags", {}).get("latest", ""), "")
        obj = {
            "package": {
                "name": name,
                "version": (meta.get("dist-tags") or {}).get("latest", ""),
                "description": (meta.get("description") or "")[:300],
                "date": last,
                "maintainers": [{"username": m.get("name", ""), "email": m.get("email", "")}
                                for m in mods],
                "publisher": {},
                "license": (meta.get("license") or ""),
            },
            "downloads": {"weekly": wk, "monthly": wk * 4},
            "dependents": "0",
            "searchScore": None,
        }
        best[name] = obj
        append_raw(obj)
        LOG.append(f"FALLBACK OK {name}: {wk:,} weekly, {len(mods)} maintainers")
    except Exception as e:
        LOG.append(f"FALLBACK FAIL {name}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
