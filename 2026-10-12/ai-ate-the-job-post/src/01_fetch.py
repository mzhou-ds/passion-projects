"""Fetch HN 'Who is hiring?' (demand) and 'Who wants to be hired?' (supply)
threads via the Algolia HN API, monthly, Jan 2019 - Oct 2026.

Each thread's top-level comments are individual posts: job ads on the hiring
thread, candidate pitches on the wants thread. We keep top-level comments
only (parent_id == story id) so replies don't pollute the post counts.
"""
import html, re, time
import requests
import pandas as pd

API = "https://hn.algolia.com/api/v1/search"
THREADS = "https://hn.algolia.com/api/v1/search_by_date"

def find_threads(kind):
    """kind: 'Who is hiring?' or 'Who wants to be hired?'"""
    out, page = [], 0
    while True:
        r = requests.get(THREADS, params={
            "query": kind, "tags": "story,author_whoishiring",
            "hitsPerPage": 100, "page": page,
            "numericFilters": "created_at_i>1546300800",  # 2019-01-01
        }, timeout=30)
        r.raise_for_status()
        d = r.json()
        for h in d["hits"]:
            title = h.get("title") or ""
            if kind.split("?")[0].lower() in title.lower() and "freelancer" not in title.lower():
                out.append({"story_id": int(h["objectID"]), "title": title,
                            "date": h["created_at"][:10], "num_comments": h.get("num_comments", 0)})
        if page >= d["nbPages"] - 1:
            break
        page += 1
        time.sleep(0.3)
    df = pd.DataFrame(out).sort_values("date")
    # one thread per month (threads are posted monthly; keep earliest in month)
    df["ym"] = df["date"].str[:7]
    return df.drop_duplicates("ym", keep="first").drop(columns="ym")

def clean(t):
    t = html.unescape(t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def fetch_posts(story_id):
    posts, page = [], 0
    while True:
        r = requests.get(API, params={
            "tags": f"comment,story_{story_id}", "hitsPerPage": 1000, "page": page,
        }, timeout=30)
        r.raise_for_status()
        d = r.json()
        for h in d["hits"]:
            if h.get("parent_id") == story_id:  # top-level only
                posts.append({"story_id": story_id, "post_id": int(h["objectID"]),
                              "date": h["created_at"][:10],
                              "text": clean(h.get("comment_text"))})
        if page >= d["nbPages"] - 1:
            break
        page += 1
        time.sleep(0.3)
    return posts

def main():
    for kind, name in [("Who is hiring?", "hiring"), ("Who wants to be hired?", "seekers")]:
        threads = find_threads(kind)
        threads.to_csv(f"data/threads_{name}.csv", index=False)
        print(f"{name}: {len(threads)} monthly threads, {threads['date'].min()}..{threads['date'].max()}")
        all_posts = []
        for _, row in threads.iterrows():
            p = fetch_posts(row["story_id"])
            for post in p:
                post["thread_date"] = row["date"]
            all_posts.extend(p)
            print(f"  {row['date']} story {row['story_id']}: {len(p)} top-level posts")
            time.sleep(0.3)
        df = pd.DataFrame(all_posts)
        df.to_csv(f"data/posts_{name}.csv", index=False)
        print(f"  -> {len(df)} posts saved")

if __name__ == "__main__":
    main()
