"""Step 2: pull every album (incl. singles/EPs) + full details from Deezer.

For each pinned artist: page /artist/{id}/albums (limit 100), then fetch
/album/{id} for contributors, genres, track durations and fans. Details
are fetched with 4 workers (each sleeping 0.3s between its own calls) to
stay well under Deezer's burst limits; 403/429 responses back off and
retry. Appends to data/deezer_albums_raw.jsonl after each album, and
skips album ids already present, so the fetch is resumable. Album
listings themselves (title, record_type, release_date) are saved to
data/deezer_listings.jsonl so counts never depend on detail calls.
"""

import csv
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

MATCHES = "data/deezer_matches.csv"
OUT = "data/deezer_albums_raw.jsonl"
LISTINGS = "data/deezer_listings.jsonl"
LOCK = threading.Lock()


def get(url, **params):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code in (403, 429):
                wait = 10 * (attempt + 1)
                print(f"  rate-limited ({r.status_code}), waiting {wait}s",
                      flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"  request error {url} attempt {attempt}: {e}", flush=True)
            time.sleep(5)
    return None


def detail_worker(album_id, panel_name, cohort, out_f, done):
    full = get(f"https://api.deezer.com/album/{album_id}")
    if full is None:
        print(f"  FAILED detail for album {album_id} ({panel_name})",
              flush=True)
        return
    rec = {
        "_panel_artist": panel_name,
        "_panel_cohort": cohort,
        "album_id": album_id,
        "title": full.get("title"),
        "record_type": full.get("record_type"),
        "release_date": full.get("release_date", ""),
        "main_artist": (full.get("artist") or {}).get("name", ""),
        "contributors": [c.get("name", "")
                         for c in full.get("contributors", [])],
        "genres": [g.get("name", "")
                   for g in (full.get("genres") or {}).get("data", [])],
        "nb_tracks": full.get("nb_tracks"),
        "duration": full.get("duration"),
        "fans": full.get("fans"),
        "track_durations": [t.get("duration")
                            for t in (full.get("tracks") or {})
                            .get("data", [])],
    }
    with LOCK:
        out_f.write(json.dumps(rec) + "\n")
        out_f.flush()
        done.add(album_id)
    time.sleep(0.3)


def main():
    with open(MATCHES, newline="") as f:
        artists = list(csv.DictReader(f))
    done = set()
    try:
        with open(OUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["album_id"])
                except Exception:  # noqa: BLE001
                    pass
    except FileNotFoundError:
        pass
    print(f"resuming: {len(done)} album details already saved", flush=True)
    out_f = open(OUT, "a")
    list_f = open(LISTINGS, "a")
    for a in artists:
        name, aid = a["name"], a["deezer_id"]
        listings, index = [], 0
        while True:
            d = get(f"https://api.deezer.com/artist/{aid}/albums",
                    limit=100, index=index)
            if d is None:
                print(f"  FAILED listing page for {name} at index {index}",
                      flush=True)
                break
            listings.extend(d.get("data", []))
            if len(listings) >= d.get("total", 0) or not d.get("next"):
                break
            index += 100
            time.sleep(0.2)
        with LOCK:
            for alb in listings:
                list_f.write(json.dumps({
                    "_panel_artist": name, "_panel_cohort": a["cohort"],
                    "album_id": alb["id"], "title": alb["title"],
                    "record_type": alb.get("record_type"),
                    "release_date": alb.get("release_date", "")}) + "\n")
            list_f.flush()
        todo = [alb["id"] for alb in listings if alb["id"] not in done]
        print(f"{name}: {len(listings)} listings, {len(todo)} details to fetch",
              flush=True)
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda alb_id: detail_worker(
                alb_id, name, a["cohort"], out_f, done), todo))
        print(f"  done {name}", flush=True)
    out_f.close()
    list_f.close()
    print("done")


if __name__ == "__main__":
    main()
