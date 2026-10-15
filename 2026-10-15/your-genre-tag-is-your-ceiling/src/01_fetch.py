"""Fetch Beatport's overall Top 100 plus every genre Top 100 that Beatport
promotes in its own homepage navigation (17 genre charts), and save the raw
snapshot.

Beatport's Next.js pages embed chart data in __NEXT_DATA__ as a dehydrated
react-query payload, so one GET per chart is enough — no API key, no JS.
Each genre page's payload also carries Beatport's own genre metadata
(id, name, slug, sub-genres), which is how the chart list below was verified:
every slug/id pair here returned a payload whose genre object matches it.

Scope note: Beatport runs smaller charts beyond the promoted set. This census
covers the overall chart + the 17 genres Beatport itself puts in the homepage
nav — the shelves a casual buyer actually sees.

Re-run any time to refresh the snapshot (charts move daily). Requests are
spaced 2s apart, one fresh connection per chart.
"""
import re, json, time, gzip, os, requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "raw", "charts_raw.json.gz")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

CHARTS = {"main": "https://www.beatport.com/top-100"}
GENRES = [  # (slug, id) — both verified against each page's own genre payload
    ("afro-house", 89), ("bass-house", 91), ("dance-pop", 39),
    ("deep-house", 12), ("drum-bass", 1), ("funky-house", 81),
    ("house", 5), ("indie-dance", 37), ("indie-tech", 112),
    ("mainstage", 96), ("melodic-house-techno", 90),
    ("minimal-deep-tech", 14), ("progressive-house", 15),
    ("tech-house", 11), ("techno-peak-time-driving", 6),
    ("techno-raw-deep-hypnotic", 92), ("uk-garage-bassline", 86),
]
for slug, gid in GENRES:
    CHARTS[slug] = f"https://www.beatport.com/genre/{slug}/{gid}/top-100"


def fetch(url):
    r = requests.get(url, timeout=40, headers=UA)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  r.text, re.S)
    d = json.loads(m.group(1))
    pp = d["props"]["pageProps"]
    for q in pp["dehydratedState"]["queries"]:
        if "top-100" in str(q["queryKey"]):
            return q["state"]["data"]["results"], pp.get("genre")
    raise RuntimeError("no top-100 payload found: " + url)


def main():
    out = {}
    for name, url in CHARTS.items():
        results, genre = fetch(url)
        if name != "main":
            assert genre and genre["slug"] == name, (name, genre)
        out[name] = {"genre_meta": genre, "results": results}
        print(f"{name}: {len(results)} tracks")
        time.sleep(2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, "wt") as f:
        json.dump(out, f)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
