"""Anatomy of a Chart — analysis of 600 Beatport Top-100 tracks (Sep 17, 2026).

Reads data/tracks.csv, writes figures/*.png and prints findings.
"""
import csv, json, statistics
from collections import Counter, defaultdict
from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA = "data/tracks.csv"
FIG = "figures"
TODAY = date(2026, 9, 17)
plt.rcParams.update({"font.size": 11, "figure.figsize": (10, 6)})

rows = list(csv.DictReader(open(DATA)))
for r in rows:
    r["rank"] = int(r["rank"])
    r["bpm"] = int(r["bpm"]) if r["bpm"] else None
    r["length_min"] = int(r["length_ms"]) / 60000 if r["length_ms"] else None

main = [r for r in rows if r["chart"] == "main"]
print(f"tracks: {len(rows)} (main top100: {len(main)})")

# ---------- Fig 1: genre landscape of the main Top 100 ----------
g = Counter(r["genre"] for r in main)
order = g.most_common()
fig, ax = plt.subplots()
ax.barh([x[0] for x in order][::-1], [x[1] for x in order][::-1], color="#e8792e")
ax.set_xlabel("Tracks in Beatport Top 100")
ax.set_title("Genre landscape of the Beatport Top 100 — Sep 17, 2026")
fig.tight_layout(); fig.savefig(f"{FIG}/fig1_genre_landscape.png", dpi=140); plt.close(fig)
print("top genres:", order[:6])

# ---------- Fig 2: BPM by genre (all charts) ----------
genre_bpm = defaultdict(list)
for r in rows:
    if r["bpm"]:
        genre_bpm[r["genre"]].append(r["bpm"])
big = sorted(genre_bpm, key=lambda k: len(genre_bpm[k]), reverse=True)[:9]
fig, ax = plt.subplots(figsize=(11, 6))
data = [genre_bpm[k] for k in big]
bp = ax.boxplot(data, labels=[k.replace(" / ", "/") for k in big], patch_artist=True)
for patch in bp["boxes"]:
    patch.set_facecolor("#7fb069")
ax.set_ylabel("BPM")
ax.set_title("Tempo conventions by genre (600 charting tracks, Sep 2026)")
ax.set_xticklabels([k.replace(" / ", "/") for k in big], rotation=22, ha="right")
fig.subplots_adjust(bottom=0.22)
fig.tight_layout(); fig.savefig(f"{FIG}/fig2_bpm_by_genre.png", dpi=140); plt.close(fig)
for k in big:
    v = genre_bpm[k]
    print(f"{k}: n={len(v)} mode={Counter(v).most_common(3)} median={statistics.median(v)}")

# ---------- Fig 3: key analysis (main chart) ----------
keys = Counter(r["key"] for r in main if r["key"])
chords = Counter(r["key_chord"] for r in main if r["key_chord"])
print("major/minor:", chords)
topk = keys.most_common(10)
fig, ax = plt.subplots()
ax.bar([x[0] for x in topk], [x[1] for x in topk], color="#4a7c9b")
ax.set_ylabel("Tracks")
ax.set_title("Most common musical keys in the Beatport Top 100")
ax.tick_params(axis="x", rotation=30)
fig.tight_layout(); fig.savefig(f"{FIG}/fig3_key_distribution.png", dpi=140); plt.close(fig)
print("top keys:", topk)

# ---------- Fig 4: label concentration (main chart) ----------
labels = Counter(r["label"] for r in main)
topl = labels.most_common(15)
fig, ax = plt.subplots(figsize=(11, 6.5))
names = [n if len(n) < 42 else n[:40] + "…" for n, _ in topl]
ax.barh(names[::-1], [c for _, c in topl][::-1], color="#9b59b6")
ax.set_xlabel("Tracks in Top 100")
ax.set_title("Label concentration: who owns the Beatport Top 100?")
fig.tight_layout(); fig.savefig(f"{FIG}/fig4_label_concentration.png", dpi=140); plt.close(fig)
top5 = sum(c for _, c in topl[:5]); top10 = sum(c for _, c in topl[:10])
print(f"label share: top5={top5}%, top10={top10}%, unique labels={len(labels)}")
print("top labels:", topl[:8])
majors = ["Universal", "Sony", "Warner", "Interscope", "Atlantic", "Columbia",
          "Republic", "Def Jam", "Island", "Capitol", "RCA", "Epic", "Polydor"]
major_tracks = [r for r in main if any(m.lower() in r["label"].lower() for m in majors)]
print(f"major-label tracks: {len(major_tracks)}")
print(sorted(set(r["label"] for r in major_tracks)))

# ---------- Fig 5: release freshness ----------
ages = []
for r in main:
    if r["release_date"]:
        try:
            y, m_, d = map(int, r["release_date"].split("-"))
            ages.append((TODAY - date(y, m_, d)).days)
        except ValueError:
            pass
fig, ax = plt.subplots()
ax.hist(ages, bins=range(0, max(ages) + 15, 15), color="#e8792e", edgecolor="white")
ax.set_xlabel("Days between release and chart date")
ax.set_ylabel("Tracks")
ax.set_title("How fresh is the chart? Release recency of Top 100 tracks")
fig.tight_layout(); fig.savefig(f"{FIG}/fig5_release_recency.png", dpi=140); plt.close(fig)
ages_sorted = sorted(ages)
print(f"release age: median={ages_sorted[len(ages_sorted)//2]}d, "
      f"<=30d={sum(a<=30 for a in ages)}, <=90d={sum(a<=90 for a in ages)}, n={len(ages)}")

# ---------- Track anatomy ----------
ext = sum("extended" in r["mix"].lower() for r in main)
remix = sum(bool(r["remixers"]) for r in main)
collab = sum(len(r["artists"].split(";")) > 1 for r in main)
lens = [r["length_min"] for r in main if r["length_min"]]
print(f"extended mixes: {ext}%, remixes: {remix}%, multi-artist: {collab}%, "
      f"median length: {statistics.median(lens):.1f} min")
uniq_artists = set()
for r in main:
    uniq_artists.update(a.strip() for a in r["artists"].split(";"))
print(f"unique artists in top 100: {len(uniq_artists)}")

# ---------- Spotify merge (data/spotify_artists.json) ----------
try:
    raw = json.load(open("data/spotify_artists.json"))
    sp = {a["name"]: a for a in raw if a.get("match_quality") != "fuzzy"}
    got = [a for a in sp.values() if a.get("monthly_listeners")]
    print(f"spotify matched: {len(got)}/{len(sp)} (4 fuzzy excluded)")
    top_sp = sorted(got, key=lambda a: a["monthly_listeners"], reverse=True)[:10]
    for a in top_sp:
        print(f"  {a['spotify_title']}: {a['monthly_listeners']:,}/mo")
    # fig6: monthly listeners of matched artists (log scale)
    vals = sorted([a["monthly_listeners"] for a in got])
    fig, ax = plt.subplots()
    ax.hist(np.log10(vals), bins=20, color="#1db954", edgecolor="white")
    ax.set_xlabel("log10(monthly listeners)")
    ax.set_ylabel("Artists")
    ax.set_title("Spotify audience of Beatport-charting artists (listener economy)")
    fig.tight_layout(); fig.savefig(f"{FIG}/fig6_spotify_audience.png", dpi=140); plt.close(fig)
    med = vals[len(vals)//2]
    print(f"median monthly listeners: {med:,}; >=10M: {sum(v>=10_000_000 for v in vals)}; "
          f"<1M: {sum(v<1_000_000 for v in vals)}")
except FileNotFoundError:
    print("spotify data not ready; skipping merge")
