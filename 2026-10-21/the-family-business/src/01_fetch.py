"""Fetch three samples from the Hugging Face Hub API (no key needed).

Samples (union is the analysis universe):
  - downloads: top 5,000 models by last-30-day downloads  (the demand side)
  - likes:     top 2,000 models by likes                  (the attention side)
  - newest:    3,000 most recently created models         (the supply firehose)

Fields kept per model: id, author, createdAt, lastModified, downloads
(last 30 days), downloadsAllTime, likes, pipeline_tag, library_name,
tags, cardData.base_model, safetensors parameter count, gated flag.

Pagination follows the Link: rel="next" cursor header. One fresh GET per
page (keep-alive sessions have hung against some APIs through proxies),
and every page is appended to disk immediately so a failure never loses
work already fetched.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

BASE = "https://huggingface.co/api/models"
OUT = Path(__file__).resolve().parent.parent / "data" / "models_raw.jsonl"
EXPAND = ["safetensors", "cardData", "downloadsAllTime"]

SAMPLES = [
    ("downloads", {"sort": "downloads", "direction": -1}, 5000),
    ("likes", {"sort": "likes", "direction": -1}, 2000),
    ("newest", {"sort": "createdAt", "direction": -1}, 3000),
]


def slim(m, sample):
    card = m.get("cardData") or {}
    base = card.get("base_model")
    if isinstance(base, str):
        base = [base]
    st = m.get("safetensors") or {}
    return {
        "sample": sample,
        "id": m.get("id"),
        "author": m.get("author"),
        "createdAt": m.get("createdAt"),
        "lastModified": m.get("lastModified"),
        "downloads": m.get("downloads") or 0,
        "downloadsAllTime": m.get("downloadsAllTime") or 0,
        "likes": m.get("likes") or 0,
        "pipeline_tag": m.get("pipeline_tag"),
        "library_name": m.get("library_name"),
        "tags": m.get("tags") or [],
        "card_base_model": base or [],
        "params": st.get("total"),
        "gated": bool(m.get("gated")),
    }


def fetch_sample(name, params, target, fh):
    got = 0
    cursor = None
    while got < target:
        p = [("limit", "100"), ("full", "true")]
        for k, v in params.items():
            p.append((k, str(v)))
        for e in EXPAND:
            p.append(("expand[]", e))
        if cursor:
            p.append(("cursor", cursor))
        r = requests.get(BASE, params=p, timeout=60)
        if r.status_code != 200:
            print(f"[{name}] HTTP {r.status_code} after {got} rows; stopping sample")
            return got
        rows = r.json()
        if not rows:
            break
        for m in rows:
            fh.write(json.dumps(slim(m, name)) + "\n")
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(OUT, "w") as fh:
        for name, params, target in SAMPLES:
            total += fetch_sample(name, params, target, fh)
    print(f"total rows (with sample overlap): {total} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
