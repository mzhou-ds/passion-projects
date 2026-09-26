"""Fetch Spotify monthly listeners for every Portola 2026 artist.

Uses the connected `spotify-api` CLI (search --search-type ARTISTS returns
"X monthly listeners" in each result's subtitle). One call per artist.
b2b bills are resolved to the max of the two artists' listener counts.
"""
import csv, json, re, subprocess, time

# Billed name -> Spotify search query (or list of queries for b2b, take max)
OVERRIDES = {
    "Beltran b2b Ben Sterling": ["Beltran", "Ben Sterling"],
    "erika b2b sfcowboy": ["erika", "sfcowboy"],
    "Ranger Trucco b2b Alisha": ["Ranger Trucco", "Alisha"],
    "Mike D 5D": ["Mike D"],
    "Melanie C": ["Melanie C"],
    "DOG BLOOD": ["Dog Blood"],
    "DESPACIO": ["Despacio"],
    "Tiësto": ["Tiesto"],
    "Chloé Caillet": ["Chloe Caillet"],
    "basspunk.": ["basspunk"],
    "ZULAN": ["ZULAN"],
}

def search_artist(query):
    """Return (title, url, monthly_listeners) for the top search hit, or Nones."""
    try:
        out = subprocess.run(
            ["spotify-api", "search", "--search-type", "ARTISTS", "--query", query],
            capture_output=True, text=True, timeout=60,
        ).stdout
        d = json.loads(out)
    except Exception as e:
        return None, None, None, f"cli_error: {e}"
    items = (d.get("sections") or [{}])[0].get("items") or []
    if not items:
        return None, None, None, "no_results"
    top = items[0]
    title = top.get("title")
    url = top.get("spotify_url")
    sub = top.get("subtitle") or ""
    m = re.search(r"([\d,]+)\s+monthly listeners", sub)
    listeners = int(m.group(1).replace(",", "")) if m else None
    return title, url, listeners, None

def match_quality(billed, found):
    if not found:
        return "none"
    a = re.sub(r"[^a-z0-9]", "", billed.lower())
    b = re.sub(r"[^a-z0-9]", "", found.lower())
    if a == b or a in b or b in a:
        return "exact"
    return "fuzzy"

results = []
with open("data/lineup.csv") as f:
    artists = [r["artist"] for r in csv.DictReader(f)]

for artist in artists:
    queries = OVERRIDES.get(artist, [artist])
    if not isinstance(queries, list):
        queries = [queries]
    best = None
    for q in queries:
        title, url, listeners, err = search_artist(q)
        time.sleep(0.4)
        if listeners is None:
            continue
        if best is None or listeners > best["monthly_listeners"]:
            best = {"query": q, "spotify_title": title, "spotify_url": url,
                    "monthly_listeners": listeners, "error": err}
    if best is None:
        results.append({"artist": artist, "query": "|".join(queries),
                        "spotify_title": None, "spotify_url": None,
                        "monthly_listeners": None,
                        "match_quality": "none", "error": "no_listeners_found"})
    else:
        results.append({"artist": artist, "query": best["query"],
                        "spotify_title": best["spotify_title"],
                        "spotify_url": best["spotify_url"],
                        "monthly_listeners": best["monthly_listeners"],
                        "match_quality": match_quality(artist, best["spotify_title"]),
                        "error": best["error"]})
    ml = results[-1]["monthly_listeners"]
    print(f"{artist:32s} -> {results[-1]['spotify_title']}  {ml}")

with open("data/spotify_listeners.json", "w") as f:
    json.dump(results, f, indent=1)
n_ok = sum(1 for r in results if r["monthly_listeners"])
print(f"\n{n_ok}/{len(results)} artists resolved")
