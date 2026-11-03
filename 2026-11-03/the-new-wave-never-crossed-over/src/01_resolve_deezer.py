"""Step 1: resolve the panel to Deezer artist IDs.

Deezer's public API needs no key. Output: data/deezer_matches.csv (top
pick + top-3 candidates for review). The album fetch (02_fetch_deezer.py)
reads the pinned deezer_id column, so a wrong top pick can be corrected
by hand before any discography is pulled.
"""

import csv
import time

import requests

OUT = "data/deezer_matches.csv"


def search(name):
    r = requests.get("https://api.deezer.com/search/artist",
                     params={"q": name}, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def main():
    with open("data/artists.csv", newline="") as f:
        panel = list(csv.DictReader(f))
    rows = []
    for artist in panel:
        name = artist["name"]
        try:
            cands = search(name)
        except Exception as e:  # noqa: BLE001
            print(f"  search error for {name}: {e}")
            cands = []
        top = cands[0] if cands else {}
        rows.append({
            "name": name,
            "cohort": artist["cohort"],
            "breakout_anchor": artist["breakout_anchor"],
            "deezer_id": top.get("id", ""),
            "deezer_name": top.get("name", ""),
            "deezer_fans": top.get("nb_fan", ""),
            "top3": " | ".join(f"{c.get('name')} (id {c.get('id')}, "
                                   f"{c.get('nb_fan', 0)} fans)"
                                   for c in cands[:3]),
        })
        print(f"{name:20s} -> {top.get('name', '?')} "
              f"(id {top.get('id', '?')}, {top.get('nb_fan', '?')} fans)")
        time.sleep(0.3)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} artists)")


if __name__ == "__main__":
    main()
