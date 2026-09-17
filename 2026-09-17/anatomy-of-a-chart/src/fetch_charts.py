"""Fetch the Beatport Top 100 + five genre Top 100s and flatten to data/tracks.csv.

Beatport's Next.js pages embed the chart data in __NEXT_DATA__ as a dehydrated
react-query payload, so one GET per chart is enough — no API key, no JS.
Re-run any time to refresh the snapshot (data will drift as charts move).
"""
import re, json, csv, time, urllib.request

CHARTS = {
    "main": "https://www.beatport.com/top-100",
    "house": "https://www.beatport.com/genre/house/5/top-100",
    "tech-house": "https://www.beatport.com/genre/tech-house/11/top-100",
    "dance-pop": "https://www.beatport.com/genre/dance-pop/39/top-100",
    "melodic-house-techno": "https://www.beatport.com/genre/melodic-house-techno/90/top-100",
    "minimal-deep-tech": "https://www.beatport.com/genre/minimal-deep-tech/14/top-100",
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")

def tracks_from(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    d = json.loads(m.group(1))
    for q in d["props"]["pageProps"]["dehydratedState"]["queries"]:
        if "top-100" in str(q["queryKey"]):
            return q["state"]["data"]["results"]
    raise RuntimeError("no top-100 payload found")

def flat(chart, rank, t):
    key = t.get("key") or {}
    return {
        "chart": chart, "rank": rank, "track": t["name"],
        "artists": "; ".join(a["name"] for a in t.get("artists", [])),
        "remixers": "; ".join(a["name"] for a in t.get("remixers", [])),
        "mix": t.get("mix_name") or "", "genre": t["genre"]["name"],
        "bpm": t.get("bpm"), "key": key.get("name", ""),
        "key_letter": key.get("letter", ""),
        "key_chord": (key.get("chord_type") or {}).get("name", ""),
        "length_ms": t.get("length_ms"), "length": t.get("length", ""),
        "label": t["release"]["label"]["name"],
        "release_date": t.get("new_release_date") or t.get("publish_date"),
        "is_dj_edit": t.get("is_dj_edit"), "is_ugc_remix": t.get("is_ugc_remix"),
        "explicit": t.get("is_explicit"),
    }

rows = []
for chart, url in CHARTS.items():
    res = tracks_from(fetch(url))
    print(chart, len(res))
    rows += [flat(chart, i + 1, t) for i, t in enumerate(res)]
    time.sleep(2)

with open("data/tracks.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print("wrote", len(rows), "rows")
