"""Second fetch pass, plain list endpoint (no expand[], no full).

Why: the expand[] mode used in 01_fetch.py returns pipeline_tag as null
for every row, and depending on the sort it zeroes the non-sorted metric
(the likes-sorted pass returns downloads=0, and vice versa). The plain
endpoint returns honest downloads, likes and pipeline_tag together.
02_genealogy.py merges both passes: max() for the numeric counters,
first non-null for the categorical fields, expand-only fields (params,
downloadsAllTime, cardData) taken from pass 1.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

BASE = "https://huggingface.co/api/models"
OUT = Path(__file__).resolve().parent.parent / "data" / "models_plain.jsonl"
SAMPLES = [
    ("downloads", {"sort": "downloads", "direction": -1}, 5000),
    ("likes", {"sort": "likes", "direction": -1}, 2000),
    ("newest", {"sort": "createdAt", "direction": -1}, 3000),
]


def fetch_sample(name, params, target, fh):
    got, cursor = 0, None
    while got < target:
        p = [("limit", "100")]
        for k, v in params.items():
            p.append((k, str(v)))
        if cursor:
            p.append(("cursor", cursor))
        r = requests.get(BASE, params=p, timeout=60)
        if r.status_code != 200:
            print(f"[{name}] HTTP {r.status_code} after {got}; stopping")
            return got
        rows = r.json()
        if not rows:
            break
        for m in rows:
            fh.write(json.dumps({
                "sample": name, "id": m.get("id"), "author": m.get("author"),
                "createdAt": m.get("createdAt"),
                "downloads": m.get("downloads") or 0,
                "likes": m.get("likes") or 0,
                "pipeline_tag": m.get("pipeline_tag"),
                "library_name": m.get("library_name"),
                "tags": m.get("tags") or [],
            }) + "\n")
        fh.flush()
        got += len(rows)
        link = r.headers.get("link", "")
        mm = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not mm:
            break
        cursor = parse_qs(urlparse(mm.group(1)).query).get("cursor", [None])[0]
        if not cursor:
            break
        time.sleep(0.15)
    print(f"[{name}] fetched {got}")
    return got


def main():
    total = 0
    with open(OUT, "w") as fh:
        for name, params, target in SAMPLES:
            total += fetch_sample(name, params, target, fh)
    print(f"total rows: {total} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
