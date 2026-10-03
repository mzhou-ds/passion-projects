"""
Fetch HN "Ask HN: Who is hiring?" threads + their top-level comments
(job posts) via the Algolia HN Search API (public, no key).

Strategy:
  1. Find monthly Who-is-Hiring stories by author whoishiring.
  2. For each story, pull comments with tags=comment,story_<id>,
     paginated (hitsPerPage=1000). Those comments are the job posts.

Output: data/threads.json, data/posts_raw.csv
Uses fresh requests.get per call (Session keep-alive hangs via proxy,
see AGENTS.md).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ALGOLIA = "https://hn.algolia.com/api/v1/search"
# only threads from 2023-01 onward: gives a clean pre/post ChatGPT-era window
START_TS = 1672531200  # 2023-01-01 UTC


def get(params, tries=4):
    for a in range(tries):
        try:
            r = requests.get(ALGOLIA, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  retry {a+1}: {e}", flush=True)
            time.sleep(2 * (a + 1))
    return None


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    # 1. threads
    threads, page = [], 0
    while True:
        payload = get({
            "query": "Who is hiring",
            "tags": "story,author_whoishiring",
            "numericFilters": f"created_at_i>{START_TS}",
            "hitsPerPage": 100,
            "page": page,
        })
        if not payload:
            break
        hits = payload.get("hits", [])
        for h in hits:
            title = (h.get("title") or "")
            if "Who is hiring" in title and "Freelancer" not in title and "Seeking freelancer" not in title:
                threads.append({
                    "story_id": h["objectID"],
                    "title": title,
                    "created_at": h.get("created_at"),
                    "created_at_i": h.get("created_at_i"),
                    "num_comments": h.get("num_comments"),
                })
        if page >= payload.get("nbPages", 1) - 1:
            break
        page += 1
        time.sleep(0.3)
    threads = sorted(threads, key=lambda t: t["created_at_i"])
    print(f"threads found: {len(threads)}")
    for t in threads:
        print(" ", t["created_at"], t["story_id"], t["title"][:60])
    (DATA / "threads.json").write_text(json.dumps(threads, indent=2))

    # 2. comments per thread
    rows = []
    for t in threads:
        page = 0
        while True:
            payload = get({
                "tags": f"comment,story_{t['story_id']}",
                "hitsPerPage": 1000,
                "page": page,
            })
            if not payload:
                break
            for h in payload.get("hits", []):
                # top-level comments only: parent_id == story_id
                if str(h.get("parent_id")) != str(t["story_id"]):
                    continue
                rows.append({
                    "post_id": h["objectID"],
                    "story_id": t["story_id"],
                    "thread_date": t["created_at"],
                    "author": h.get("author"),
                    "created_at": h.get("created_at"),
                    "text": h.get("comment_text") or "",
                })
            if page >= payload.get("nbPages", 1) - 1:
                break
            page += 1
            time.sleep(0.3)
        print(f"{t['created_at'][:7]} cumulative posts={len(rows)}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(DATA / "posts_raw.csv", index=False)
    print(f"\nposts={len(df)} -> {DATA/'posts_raw.csv'}")


if __name__ == "__main__":
    main()
