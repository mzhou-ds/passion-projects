#!/usr/bin/env python3
"""
01_fetch.py — Pull track catalogs from the iTunes Search API (no auth).

Panels are curated artist lists, chosen to span each genre's commercial
history from the 1990s to the 2020s. For every artist we take up to 200
song results (US storefront), which covers studio albums, singles, EPs
and remix packages — i.e. the version ecosystem as a normal listener
encounters it in the mainstream storefront.

Raw JSON is persisted per artist under data/raw/ so the run is resumable
and the analysis never needs to re-hit the API.

Source: https://itunes.apple.com/search (Apple iTunes Search API)
Fields used: trackId, trackName, collectionName, artistName, releaseDate,
trackTimeMillis, primaryGenreName, previewUrl, trackViewUrl.
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

PANELS = {
    "dance": [
        "The Prodigy", "Fatboy Slim", "The Chemical Brothers", "Daft Punk",
        "Underworld", "Basement Jaxx", "Groove Armada", "Moby",
        "Paul Oakenfold", "Tiësto", "Armin van Buuren", "Paul van Dyk",
        "Above & Beyond", "deadmau5", "Calvin Harris", "Avicii",
        "Swedish House Mafia", "Skrillex", "Diplo", "Disclosure",
        "Flume", "Martin Garrix", "Zedd", "Marshmello", "Illenium",
        "ODESZA", "Fred again..", "Peggy Gou", "Dom Dolla", "FISHER",
        "John Summit", "Four Tet", "Bicep", "Jamie xx", "KAYTRANADA",
        "David Guetta",
    ],
    "pop": [
        "Madonna", "Britney Spears", "Lady Gaga", "Dua Lipa",
        "Taylor Swift", "Billie Eilish", "The Weeknd", "Ariana Grande",
        "Justin Bieber", "Rihanna", "Katy Perry", "Ed Sheeran",
    ],
    "hiphop": [
        "Jay-Z", "Kanye West", "Drake", "Kendrick Lamar", "Eminem",
        "Nicki Minaj", "Travis Scott", "Cardi B", "50 Cent", "Snoop Dogg",
    ],
    "rock": [
        "Radiohead", "The Strokes", "Arctic Monkeys", "Coldplay", "U2",
        "Oasis", "Nirvana", "Foo Fighters", "Red Hot Chili Peppers",
        "The Killers", "Green Day", "Linkin Park",
    ],
}


def fetch_artist(name: str) -> list[dict]:
    r = requests.get(
        "https://itunes.apple.com/search",
        params={
            "term": name,
            "media": "music",
            "entity": "song",
            "limit": 200,
            "country": "US",
            "attribute": "artistTerm",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def main() -> None:
    manifest = []
    for panel, artists in PANELS.items():
        for artist in artists:
            slug = (
                artist.lower()
                .replace(" ", "_")
                .replace("&", "and")
                .replace("ë", "e")
                .replace(".", "")
            )
            out = RAW / f"{panel}__{slug}.json"
            if out.exists():
                rows = json.loads(out.read_text())
                print(f"skip (cached) {panel}/{artist}: {len(rows)}")
            else:
                rows = fetch_artist(artist)
                out.write_text(json.dumps(rows))
                print(f"fetched {panel}/{artist}: {len(rows)}")
                time.sleep(0.4)
            manifest.append(
                {"panel": panel, "artist_query": artist, "file": out.name, "n": len(rows)}
            )
    (ROOT / "data" / "fetch_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"total raw rows: {sum(m['n'] for m in manifest)}")


if __name__ == "__main__":
    main()
