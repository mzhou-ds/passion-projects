"""Fetch the npm census.

Step 1: build a candidate pool of packages from many broad npm search queries.
The search API ranks by text relevance (not downloads), so we take the full
250-result page per query, dedupe, and rank by the weekly-downloads figure the
search payload itself carries. No auth needed.

Step 2: validate coverage against a list of known giants (exact-name lookups
for anything missing).

Step 3: fetch abbreviated registry metadata for the top N packages by weekly
downloads to get their direct dependency lists (for the blast-radius analysis).

Writes:
  data/search_raw.jsonl   - one JSON object per search hit (all queries)
  data/packages.csv       - deduped pool with the fields we analyse
  data/deps_topN.json     - {package: [direct deps]} for top N by downloads
  data/fetch_log.txt      - counts / validation outcome
"""
import json
import time
import sys
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
META_URL = "https://registry.npmjs.org/{name}"
HEADERS = {
    "Accept": "application/vnd.npm.install-v1+json",
    "User-Agent": "musing-with-mike-npm-census/1.0 (research; contact via github mzhou-ds)",
}
S = requests.Session()

# Broad terms: stopwords (match almost everything) + domain vocabulary.
# Each query returns up to 250 hits ordered by text relevance; we keep them all
# and rank by downloads afterwards, so ordering bias washes out across queries.
QUERIES = [
    "is", "to", "of", "in", "on", "it", "as", "by", "for", "the", "and",
    "with", "from", "js", "node", "web", "api", "app", "util", "test",
    "build", "cli", "core", "data", "dev", "tool", "lib", "react", "vue",
    "css", "http", "json", "date", "time", "file", "server", "client",
    "auth", "log", "cache", "event", "image", "chart", "form", "grid",
    "map", "graph", "code", "type", "func", "async", "fetch", "parse",
    "format", "valid", "mock", "doc", "plugin", "babel", "webpack",
    "express", "sql", "store", "state", "route", "style", "icon", "lint",
    "jest", "vite", "fastify", "graphql", "jwt", "oauth", "dotenv",
    "eslint", "prettier", "typescript", "axios", "socket", "redis",
    "prisma", "stream", "string", "array", "object", "crypto", "queue",
    "dom", "html", "yaml", "xml", "csv", "regex", "email", "url", "path",
    "browser", "npm", "git", "cloud", "micro", "tiny", "simple", "fast",
    "light", "zero", "minimal", "modern", "easy", "framework", "library",
    "module", "package", "component", "service", "manager", "helper",
    "common", "base", "shared", "standard", "universal", "native", "pure",
    "functional", "reactive", "serverless", "docker", "electron", "mobile",
]

# Known giants we expect in the pool; anything missing gets an exact lookup.
VALIDATION = [
    "semver", "debug", "chalk", "typescript", "react", "react-dom", "lodash",
    "express", "axios", "prettier", "agent-base", "ini", "inherits", "ms",
    "safe-buffer", "which", "path-key", "mime-types", "qs", "depd", "etag",
    "once", "send", "vary", "fresh", "cookie", "accepts", "type-is",
    "parseurl", "statuses", "encodeurl", "proxy-addr", "body-parser",
    "escape-html", "http-errors", "on-finished", "finalhandler",
    "range-parser", "serve-static", "cookie-signature", "merge-descriptors",
    "content-disposition", "vue", "next", "webpack", "jest", "eslint",
    "vite", "esbuild", "rollup", "core-js", "rxjs", "tslib", "@babel/core",
    "@types/node", "commander", "yargs", "glob", "rimraf", "fs-extra",
    "chokidar", "minimist", "picomatch", "anymatch", "ignore", "strip-ansi",
    "ansi-styles", "supports-color", "has-flag", "cors", "helmet", "morgan",
    "winston", "uuid", "nanoid", "deepmerge", "fast-deep-equal", "ws",
    "socket.io", "mongoose", "jsonwebtoken", "bcryptjs", "passport",
    "nodemon", "pm2", "concurrently", "cross-env", "graceful-fs",
    "iconv-lite", "js-yaml", "moment", "dayjs", "date-fns", "luxon",
    "validator", "joi", "yup", "zod", "ajv", "minimatch", "brace-expansion",
    "balanced-match", "concat-map", "wrappy", "isarray", "string_decoder",
    "readable-stream", "buffer", "events", "punycode", "querystring",
    "node-fetch", "form-data", "tough-cookie", "sharp", "three", "d3",
    "core-util-is", "is-plain-object", "kind-of", "define-property",
    "object-assign", "has-value", "isobject", "is-extendable", "extend-shallow",
]

TOP_N_DEPS = 200
SLEEP = 0.25


def search(text, size=250):
    r = S.get(SEARCH_URL, params={"text": text, "size": size}, timeout=30)
    r.raise_for_status()
    return r.json()


def exact_lookup(name):
    """Search by exact name; return the hit whose name matches, else None."""
    d = search(name, size=5)
    for obj in d.get("objects", []):
        if obj["package"]["name"] == name:
            return obj
    return None


def main():
    log = []
    raw_path = DATA / "search_raw.jsonl"
    seen = set()
    n_hits = 0
    with open(raw_path, "w") as f:
        for q in QUERIES:
            try:
                d = search(q)
            except Exception as e:
                log.append(f"QUERY FAIL {q}: {e}")
                continue
            for obj in d.get("objects", []):
                f.write(json.dumps(obj) + "\n")
                n_hits += 1
            time.sleep(SLEEP)
    log.append(f"queries={len(QUERIES)} raw_hits={n_hits}")

    # Dedupe by name, keeping the hit with the highest weekly downloads
    # (the same package can appear under several queries with slightly
    # different download snapshots).
    best = {}
    with open(raw_path) as f:
        for line in f:
            obj = json.loads(line)
            pkg = obj["package"]
            name = pkg["name"]
            wk = (obj.get("downloads") or {}).get("weekly") or 0
            if name not in best or wk > (best[name].get("downloads") or {}).get("weekly", 0):
                best[name] = obj
    log.append(f"unique_packages={len(best)}")

    # Validation: exact lookup for any known giant missing from the pool
    missing = [n for n in VALIDATION if n not in best]
    log.append(f"validation_missing_before_lookup={len(missing)}: {missing}")
    for name in missing:
        try:
            obj = exact_lookup(name)
        except Exception as e:
            log.append(f"LOOKUP FAIL {name}: {e}")
            continue
        if obj:
            best[name] = obj
            with open(raw_path, "a") as f:
                f.write(json.dumps(obj) + "\n")
        else:
            log.append(f"LOOKUP NO-MATCH {name}")
        time.sleep(SLEEP)
    log.append(f"unique_packages_after_validation={len(best)}")

    # Flatten to CSV
    import csv

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
    log.append(f"packages.csv rows={len(rows)} top={rows[0]['name']} "
               f"{rows[0]['weekly_downloads']:,} weekly downloads")

    # Direct deps for the top N by downloads (abbreviated metadata)
    deps = {}
    fails = []
    for row in rows[:TOP_N_DEPS]:
        name = row["name"]
        try:
            r = S.get(META_URL.format(name=name), headers=HEADERS, timeout=30)
            r.raise_for_status()
            d = r.json()
            latest = d["dist-tags"]["latest"]
            v = d["versions"][latest]
            deps[name] = sorted((v.get("dependencies") or {}).keys())
        except Exception as e:
            fails.append(name)
            log.append(f" META FAIL {name}: {e}")
        time.sleep(0.15)
    with open(DATA / "deps_top200.json", "w") as f:
        json.dump(deps, f, indent=1)
    n_dep_edges = sum(len(v) for v in deps.values())
    uniq_deps = sorted({d for v in deps.values() for d in v})
    log.append(f"deps: topN={TOP_N_DEPS} ok={len(deps)} fails={len(fails)} "
               f"edges={n_dep_edges} unique_deps={len(uniq_deps)}")
    with open(DATA / "deps_unique.txt", "w") as f:
        f.write("\n".join(uniq_deps))
    with open(DATA / "fetch_log.txt", "w") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
