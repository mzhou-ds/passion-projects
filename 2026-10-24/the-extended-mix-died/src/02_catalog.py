#!/usr/bin/env python3
"""
02_catalog.py — Clean the iTunes catalog and measure the version ecosystem.

Key constructions:
- Version tag: parsed from the track title's parenthetical / bracket /
  trailing descriptor (Extended, Radio Edit, Club Mix, Original Mix,
  Remix, VIP Mix, Dub, Instrumental, ...). Untagged album cuts are
  "album / untagged".
- Title stem: the song identity with version descriptors, feat. credits
  and remix attributions stripped, so all versions of one song group
  together within an artist.
- Stem era: year of the earliest version of that stem in the catalog.
- Version spread: for stems with >= 2 distinct durations, max - min
  seconds. This is the "two songs in one" measurement: a radio edit and
  an extended mix coexisting for the same song.

Outputs:
- data/tracks_clean.csv      one row per track
- data/stems.csv             one row per (artist, stem)
- data/catalog_stats.json    headline aggregates used by README/charts
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

ERA_BINS = [(1990, 1999, "1990s"), (2000, 2004, "2000-04"), (2005, 2009, "2005-09"),
            (2010, 2014, "2010-14"), (2015, 2019, "2015-19"), (2020, 2026, "2020-26")]

VERSION_PATTERNS = [
    (r"extended", "extended"),
    (r"radio edit|radio mix|radio version|single edit|single version", "radio_edit"),
    (r"club mix|club edit|club version", "club"),
    (r"original mix|original version", "original_mix"),
    (r"\bvip\b", "vip"),
    (r"\bdub\b", "dub"),
    (r"instrumental", "instrumental"),
    (r"a ?capp?ella|acapella", "acapella"),
    (r"remix", "remix"),
    (r"\bedit\b", "edit_other"),
    (r"\bmix\b", "mix_other"),
]


def era_of(year: float) -> str:
    for lo, hi, lab in ERA_BINS:
        if lo <= year <= hi:
            return lab
    return "pre-1990" if year < 1990 else "2020-26"


def version_tag(track_name: str) -> str:
    low = track_name.lower()
    # look at descriptors after the bare title: (…) […] or " - …"
    desc = low
    for pat, lab in VERSION_PATTERNS:
        if re.search(pat, desc):
            return lab
    return "untagged"


def primary_artist(artist_name: str) -> str:
    """First-billed artist: 'Calvin Harris & Dua Lipa' -> 'Calvin Harris'."""
    s = re.split(r"\s&\s|,|\bfeat\.?\b|\bfeaturing\b|\bwith\b", artist_name.lower())
    return s[0].strip()


def stem_of(track_name: str, artist_name: str) -> str:
    s = track_name.lower()
    # drop bracketed / parenthesised segments entirely
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\[[^\]]*\]", " ", s)
    # drop " - <descriptor>" suffixes
    s = re.sub(r"\s-\s.*$", " ", s)
    # drop feat. tails
    s = re.split(r"\bfeat\.?\b|\bfeaturing\b|\bwith\b", s)[0]
    # drop trailing version words that appear bare
    s = re.sub(
        r"\b(extended|radio|club|original|vip|dub|instrumental|remix|edit|mix|version|single)\b",
        " ",
        s,
    )
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return f"{primary_artist(artist_name)} :: {s}"


def load_tracks() -> pd.DataFrame:
    rows = []
    for f in sorted(RAW.glob("*.json")):
        panel = f.name.split("__")[0]
        for t in json.loads(f.read_text()):
            if t.get("kind") != "song" or not t.get("trackTimeMillis"):
                continue
            rows.append(
                {
                    "panel_query": panel,
                    "track_id": t["trackId"],
                    "track_name": t.get("trackName", ""),
                    "artist": t.get("artistName", ""),
                    "collection": t.get("collectionName", ""),
                    "genre": t.get("primaryGenreName", ""),
                    "release": t.get("releaseDate", ""),
                    "seconds": t["trackTimeMillis"] / 1000.0,
                    "preview": t.get("previewUrl", ""),
                }
            )
    df = pd.DataFrame(rows).drop_duplicates("track_id")
    df["year"] = pd.to_datetime(df["release"], errors="coerce", utc=True).dt.year
    df = df[(df["year"] >= 1985) & (df["year"] <= 2026) & (df["seconds"] >= 30)]
    # keep only rows whose artist matches the queried panel artist family:
    # iTunes attribute=artistTerm still returns features; the queried artist
    # is the file's artist, so rebuild panel from the file mapping instead.
    df["version"] = df["track_name"].map(version_tag)
    df["primary_artist"] = df["artist"].map(primary_artist)
    df["stem"] = [stem_of(n, a) for n, a in zip(df["track_name"], df["artist"])]
    df["era"] = df["year"].map(era_of)
    df["is_long"] = df["seconds"] >= 330  # >= 5:30, classic club territory
    df["is_short"] = df["seconds"] <= 210  # <= 3:30, radio territory
    return df


def main() -> None:
    df = load_tracks()
    df.to_csv(ROOT / "data" / "tracks_clean.csv", index=False)
    print(f"tracks: {len(df)}  artists: {df['artist'].nunique()}")

    # ---- stem table ------------------------------------------------------
    stems = (
        df.groupby("stem")
        .agg(
            artist=("primary_artist", "first"),
            panel=("panel_query", "first"),
            n_versions=("track_id", "nunique"),
            n_distinct_durations=("seconds", "nunique"),
            min_s=("seconds", "min"),
            max_s=("seconds", "max"),
            first_year=("year", "min"),
            has_extended=("version", lambda v: (v == "extended").any()),
            has_club=("version", lambda v: (v == "club").any()),
            has_radio=("version", lambda v: (v == "radio_edit").any()),
            has_remix=("version", lambda v: (v == "remix").any()),
        )
        .reset_index()
    )
    stems["spread_s"] = stems["max_s"] - stems["min_s"]
    stems["multi"] = stems["n_distinct_durations"] >= 2
    # "True versioning": versions that actually differ in length, as opposed
    # to remaster / reissue duplicates of the same cut (controls' multi-
    # version stems have median spreads of ~2-20s — same song, new master).
    stems["true_versioned"] = stems["spread_s"] >= 60
    # The classic dance-single pair: a radio-length cut AND a club-length
    # cut of the same song coexisting in the catalog.
    stems["radio_club_pair"] = (stems["min_s"] <= 225) & (stems["max_s"] >= 330)
    stems["era"] = stems["first_year"].map(era_of)
    stems.to_csv(ROOT / "data" / "stems.csv", index=False)
    print(f"stems: {len(stems)}  multi-version: {stems['multi'].mean():.1%}")

    stats: dict = {"n_tracks": int(len(df)), "n_stems": int(len(stems))}

    # ---- catalog stats by panel x era ------------------------------------
    cat = (
        df.groupby(["panel_query", "era"])
        .agg(
            n=("track_id", "count"),
            median_s=("seconds", "median"),
            p25_s=("seconds", lambda s: s.quantile(0.25)),
            p75_s=("seconds", lambda s: s.quantile(0.75)),
            share_long=("is_long", "mean"),
            share_short=("is_short", "mean"),
            share_extended_tag=("version", lambda v: (v == "extended").mean()),
            share_radio_tag=("version", lambda v: (v == "radio_edit").mean()),
            share_remix_tag=("version", lambda v: (v == "remix").mean()),
        )
        .reset_index()
    )
    cat.to_csv(ROOT / "data" / "catalog_by_era.csv", index=False)
    stats["catalog_by_era"] = cat.to_dict("records")

    # ---- stem versioning by era (dance vs controls) ----------------------
    sv = (
        stems.groupby(["panel", "era"])
        .agg(
            n_stems=("stem", "count"),
            share_multi=("multi", "mean"),
            share_true_versioned=("true_versioned", "mean"),
            share_radio_club_pair=("radio_club_pair", "mean"),
            median_spread_multi=("spread_s", lambda s: np.nan),
        )
        .reset_index()
    )
    # median spread among multi-version stems only
    med = (
        stems[stems["multi"]]
        .groupby(["panel", "era"])["spread_s"]
        .median()
        .rename("median_spread_s")
        .reset_index()
    )
    sv = sv.drop(columns=["median_spread_multi"]).merge(med, on=["panel", "era"], how="left")
    sv.to_csv(ROOT / "data" / "stems_by_era.csv", index=False)
    stats["stems_by_era"] = sv.to_dict("records")

    # ---- duration histogram shares (bimodality view), dance --------------
    bins = [(120, 180), (180, 225), (225, 270), (270, 330), (330, 420), (420, 600)]
    hist_rows = []
    for era_lab in ["1990s", "2000-04", "2005-09", "2010-14", "2015-19", "2020-26"]:
        sub = df[(df["panel_query"] == "dance") & (df["era"] == era_lab)]
        if len(sub) < 30:
            continue
        for lo, hi in bins:
            hist_rows.append(
                {
                    "era": era_lab,
                    "bin": f"{lo//60}:{lo%60:02d}-{hi//60}:{hi%60:02d}",
                    "share": float(((sub["seconds"] >= lo) & (sub["seconds"] < hi)).mean()),
                    "n": int(len(sub)),
                }
            )
    pd.DataFrame(hist_rows).to_csv(ROOT / "data" / "dance_duration_hist.csv", index=False)
    stats["dance_hist"] = hist_rows

    (ROOT / "data" / "catalog_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(cat[cat["panel_query"] == "dance"].to_string(index=False))
    print(sv[sv["panel"] == "dance"].to_string(index=False))


if __name__ == "__main__":
    main()
