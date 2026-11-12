"""02_classify.py — Parse Billboard performer strings, flag EDM-involved entries,
classify each entry's billing, and aggregate to the song level.

Billing taxonomy (per song-week entry):
  solo          — exactly one credited artist, and it is an EDM act
                  (e.g. "Avicii", "Marshmello", "Baauer")
  edm_collab    — several credited artists, all of them EDM acts
                  (e.g. "Skrillex & Diplo", "Dillon Francis & DJ Snake")
  edm_lead      — first-billed artist is EDM, at least one credited artist is not
                  (e.g. "David Guetta Featuring Sia", "Zedd & Katy Perry")
  edm_featured  — first-billed artist is not EDM, an EDM act is credited later
                  (e.g. "Rihanna Featuring Calvin Harris", "Ariana Grande Featuring Zedd")

Matching is token-subsequence matching on parsed artist segments: a roster name
matches a segment only if its tokens appear contiguously in the segment's tokens.
That kills substring false positives ("Ame" inside "Metro Boomin", "Kirk" inside
"Kirk Franklin" is killed by removing Kirk from the roster).

Song key: (normalized title, normalized first-billed artist). A song's type is the
type of its debut-week performer string; a song's peak is its best rank and its
run length is its max WKS ON CHART.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SEP = re.compile(r"\s+(?:featuring|feat\.?|ft\.?|with|x|&|and|vs\.?|presents)\s+|,|/", re.IGNORECASE)


def toks(s):
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return [t for t in s.split() if t]


def contains_seq(hay, needle):
    n = len(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def segments(perf):
    return [s.strip() for s in SEP.split(str(perf)) if s.strip()]


def norm_key(s):
    return " ".join(toks(str(s)))


def main():
    raw = pd.read_csv(DATA / "raw" / "hot100.csv")
    raw["d"] = pd.to_datetime(raw["CHART WEEK"])
    df = raw[raw["d"] >= "2010-01-01"].copy()
    df = df.rename(columns={"CHART WEEK": "week", "THIS WEEK": "rank",
                            "TITLE": "title", "PERFORMER": "performer",
                            "LAST WEEK": "last_week", "PEAK POS.": "peak_pos",
                            "WKS ON CHART": "wks_on_chart"})
    df["year"] = df["d"].dt.year
    df.to_csv(DATA / "hot100_2010_2026.csv", index=False)
    print(f"2010+ rows: {len(df):,} across {df['d'].nunique()} weeks")

    roster = json.load(open(DATA / "edm_roster.json"))
    roster_t = {a: toks(a) for a in roster}
    # safety: drop any remaining single-token names of <=2 chars
    roster_t = {a: t for a, t in roster_t.items() if not (len(t) == 1 and len(t[0]) <= 2)}

    def edm_hits(perf):
        hits = []
        for seg in segments(perf):
            st = toks(seg)
            for orig, rt in roster_t.items():
                if contains_seq(st, rt) and orig not in hits:
                    hits.append(orig)
        return hits

    def classify(row):
        segs = segments(row["performer"])
        hits = edm_hits(row["performer"])
        hit_set = set(hits)
        seg_is_edm = []
        for seg in segs:
            st = toks(seg)
            seg_is_edm.append(any(contains_seq(st, rt) for rt in roster_t.values()))
        if not hits:
            return "none", hits, segs
        if len(segs) == 1:
            return "solo", hits, segs
        if all(seg_is_edm):
            return "edm_collab", hits, segs
        if seg_is_edm[0]:
            return "edm_lead", hits, segs
        return "edm_featured", hits, segs

    out = []
    for _, r in df.iterrows():
        typ, hits, segs = classify(r)
        out.append({"week": r["d"], "year": r["year"], "rank": r["rank"],
                    "title": r["title"], "performer": r["performer"],
                    "peak_pos": r["peak_pos"], "wks_on_chart": r["wks_on_chart"],
                    "n_artists": len(segs), "edm_type": typ,
                    "edm_artists": "; ".join(hits),
                    "lead_artist": segs[0] if segs else ""})
    entries = pd.DataFrame(out)
    entries.to_csv(DATA / "entries_classified.csv", index=False)

    edm = entries[entries["edm_type"] != "none"].copy()
    print(f"EDM-involved rows: {len(edm):,} ({len(edm)/len(entries)*100:.2f}% of slots)")
    print(edm["edm_type"].value_counts().to_string())
    edm.to_csv(DATA / "edm_entries.csv", index=False)

    # song-level aggregation
    edm["song_key"] = edm["title"].apply(norm_key) + " || " + edm["lead_artist"].apply(norm_key)
    songs = []
    for key, g in edm.groupby("song_key"):
        g = g.sort_values("week")
        first = g.iloc[0]
        songs.append({
            "song_key": key, "title": first["title"], "lead_artist": first["lead_artist"],
            "performer_debut": first["performer"], "edm_type": first["edm_type"],
            "edm_artists": first["edm_artists"], "n_artists": int(first["n_artists"]),
            "debut": first["week"], "debut_year": int(first["week"].year),
            "peak": int(g["rank"].min()), "weeks": int(g["wks_on_chart"].max()),
            "top10": int(g["rank"].min() <= 10), "top40": int(g["rank"].min() <= 40),
        })
    songs = pd.DataFrame(songs).sort_values("debut")
    songs.to_csv(DATA / "edm_songs.csv", index=False)
    print(f"distinct EDM songs: {len(songs)}")
    print(songs["edm_type"].value_counts().to_string())

    # chart-wide baseline: collab share of all Hot 100 rows per year
    base = entries.groupby("year").agg(slots=("rank", "size"),
                                       collab_rows=("n_artists", lambda s: (s > 1).sum()))
    base["collab_share_all"] = base["collab_rows"] / base["slots"]
    ey = edm.groupby("year").agg(edm_slots=("rank", "size"),
                                 solo=("edm_type", lambda s: (s == "solo").sum()),
                                 edm_collab=("edm_type", lambda s: (s == "edm_collab").sum()),
                                 edm_lead=("edm_type", lambda s: (s == "edm_lead").sum()),
                                 edm_featured=("edm_type", lambda s: (s == "edm_featured").sum()))
    yearly = base.join(ey, how="left").fillna(0)
    yearly["edm_share"] = yearly["edm_slots"] / yearly["slots"]
    yearly["edm_collab_share"] = 1 - yearly["solo"] / yearly["edm_slots"].replace(0, pd.NA)
    yearly["edm_songs_debut"] = songs.groupby("debut_year").size()
    yearly = yearly.fillna(0)
    yearly.to_csv(DATA / "yearly.csv")
    print(yearly[["slots", "edm_slots", "edm_share", "solo", "edm_collab_share",
                  "collab_share_all", "edm_songs_debut"]].round(3).to_string())


if __name__ == "__main__":
    main()
