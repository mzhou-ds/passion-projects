"""Collect the raw data for The Canon and the Crowd.

Sources (all public, no keys):
  1. Wikipedia Action API — outgoing article links for every panel title
     (the field's own citation structure), plus title resolution.
  2. Wikimedia Pageviews API — monthly pageviews per article, Jan 2016
     through Sep 2026 (the crowd, recent).
  3. Google Books Ngram (English 2019 corpus) — yearly frequency of each
     philosopher's name in print, 1900-2019 (the crowd, long run).
  4. Project Gutenberg via Gutendex — full texts for the sentence-length
     (quotability) mechanism test.

Everything is cached under data/cache/ so the analysis is reproducible
without re-hitting the APIs.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from panel import PHILOSOPHERS, CONCEPTS, GUTENBERG

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "MusingWithMike/1.0 (research; contact: mzhou@example.com)"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def get_json(url, headers=UA, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  retry {attempt + 1} for {url[:90]}: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {url}")


def get_text(url, headers=UA, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  retry {attempt + 1} for {url[:90]}: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {url}")


# ---------------------------------------------------------------- Wikipedia
def resolve_titles(titles):
    """Resolve redirects/normalization; flag disambiguation pages."""
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        q = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2",
            "redirects": "1", "prop": "pageprops|categories",
            "cllimit": "50", "titles": "|".join(batch),
        })
        data = get_json(f"https://en.wikipedia.org/w/api.php?{q}")
        for page in data["query"]["pages"]:
            if "missing" in page:
                print(f"  MISSING: {page['title']}")
                continue
            cats = [c["title"] for c in page.get("categories", [])]
            is_disambig = "Category:Disambiguation pages" in cats
            out[page["title"]] = {
                "requested": None, "disambiguation": is_disambig,
                "pageid": page["pageid"],
            }
        for r in data["query"].get("redirects", []):
            if r["to"] in out:
                out[r["to"]]["requested"] = r["from"]
        time.sleep(0.2)
    return out


def fetch_links(title):
    """All outgoing main-namespace links of one article (paginated)."""
    links = []
    cont = None
    while True:
        params = {
            "action": "query", "format": "json", "formatversion": "2",
            "prop": "links", "titles": title, "plnamespace": "0",
            "pllimit": "500",
        }
        if cont:
            params["plcontinue"] = cont
        q = urllib.parse.urlencode(params)
        data = get_json(f"https://en.wikipedia.org/w/api.php?{q}")
        pages = data["query"]["pages"]
        if pages and "links" in pages[0]:
            links.extend(l["title"] for l in pages[0]["links"])
        cont = data.get("continue", {}).get("plcontinue")
        if not cont:
            break
        time.sleep(0.15)
    return links


# ---------------------------------------------------------------- Pageviews
def fetch_pageviews(title):
    safe = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia.org/all-access/user/{safe}/monthly/20160101/20260930")
    try:
        data = get_json(url)
    except Exception as e:
        print(f"  pageviews failed for {title}: {e}")
        return {}
    return {item["timestamp"][:6]: item["views"] for item in data.get("items", [])}


# ------------------------------------------------------------------- Ngram
def fetch_ngram(phrase):
    """Google Books Ngram timeseries for one phrase, 1900-2019."""
    q = urllib.parse.urlencode({
        "content": phrase, "year_start": 1900, "year_end": 2019,
        "corpus": "en-2019", "smoothing": 3,
    })
    html = get_text(f"https://books.google.com/ngrams/graph?{q}", headers=BROWSER_UA)
    series = re.findall(r'"timeseries":\s*\[([^\]]*)\]', html)
    if not series:
        print(f"  NGRAM no series for {phrase!r}")
        return None
    vals = [float(v) for v in series[0].split(",") if v.strip()]
    if len(vals) != 120:
        print(f"  NGRAM {phrase!r}: got {len(vals)} values, expected 120")
        return None
    return vals


# --------------------------------------------------------------- Gutenberg
def gutendex_search(title, author):
    q = urllib.parse.urlencode({"search": f"{title} {author}"})
    data = get_json(f"https://gutendex.com/books/?{q}")
    for book in data.get("results", []):
        fmts = book.get("formats", {})
        txt = fmts.get("text/plain; charset=utf-8") or fmts.get("text/plain")
        if txt:
            return book["id"], book["title"], txt
    return None, None, None


def main():
    titles = [p[0] for p in PHILOSOPHERS] + CONCEPTS

    print("== resolving titles ==")
    resolved = resolve_titles(titles)
    for t, info in resolved.items():
        if info["disambiguation"]:
            print(f"  DISAMBIGUATION: {t}")
    (CACHE / "resolved_titles.json").write_text(json.dumps(resolved, indent=2))
    canonical = sorted(resolved.keys())
    print(f"  resolved {len(canonical)} titles")

    print("== fetching Wikipedia links ==")
    links = {}
    for t in canonical:
        links[t] = fetch_links(t)
        print(f"  {t}: {len(links[t])} links", flush=True)
        time.sleep(0.2)
    (CACHE / "wikipedia_links.json").write_text(json.dumps(links, indent=2))

    print("== fetching pageviews ==")
    views = {}
    for t in canonical:
        views[t] = fetch_pageviews(t)
        n = len(views[t])
        print(f"  {t}: {n} months", flush=True)
        time.sleep(0.2)
    (CACHE / "pageviews.json").write_text(json.dumps(views, indent=2))

    print("== fetching Ngram series ==")
    ngrams = {}
    for title, _trad, _g, phrases in PHILOSOPHERS:
        series = None
        for phrase in phrases:
            vals = fetch_ngram(phrase)
            if vals is None:
                continue
            if series is None:
                series = vals
            else:
                series = [a + b for a, b in zip(series, vals)]
            time.sleep(0.6)
        ngrams[title] = series
        print(f"  {title}: {'ok' if series else 'FAILED'}", flush=True)
    (CACHE / "ngrams.json").write_text(json.dumps(ngrams, indent=2))

    print("== fetching Gutenberg texts ==")
    meta = {}
    for figure, title, author in GUTENBERG:
        gid, gtitle, url = gutendex_search(title, author)
        if url is None:
            print(f"  GUTENBERG NOT FOUND: {figure} / {title}")
            continue
        text = get_text(url)
        fname = f"gutenberg_{gid}.txt"
        (CACHE / fname).write_text(text)
        meta[figure] = {"gutenberg_id": gid, "title": gtitle, "file": fname}
        print(f"  {figure}: {gtitle} (id {gid}, {len(text):,} chars)", flush=True)
        time.sleep(0.3)
    (CACHE / "gutenberg_meta.json").write_text(json.dumps(meta, indent=2))

    print("done.")


if __name__ == "__main__":
    main()
