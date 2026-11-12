"""03_analysis.py — Compute every number the README reports.

Eras used throughout (chosen from the data, not imposed on it):
  boom      2011-2014  the EDM crossover: solo-billed hits still possible
  toll      2015-2017  the featuring-credit era: EDM share peaks, solo billing vanishes
  fade      2018-2020  EDM share halves, then halves again
  remnant   2021-2026  a handful of incumbents, zero solo top-40s
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

ERAS = [(2011, 2014, "boom"), (2015, 2017, "toll"),
        (2018, 2020, "fade"), (2021, 2026, "remnant")]


def era_of(y):
    for lo, hi, name in ERAS:
        if lo <= y <= hi:
            return name
    return "pre"


def main():
    songs = pd.read_csv(DATA / "edm_songs.csv", parse_dates=["debut"])
    entries = pd.read_csv(DATA / "edm_entries.csv", parse_dates=["week"])
    yearly = pd.read_csv(DATA / "yearly.csv", index_col=0)
    songs["era"] = songs["debut_year"].apply(era_of)
    songs["is_solo"] = (songs["edm_type"] == "solo").astype(int)
    songs["is_collab"] = 1 - songs["is_solo"]
    f = {}

    # ---- headline: the extinction table ----
    solo = songs[songs["edm_type"] == "solo"].sort_values("debut")
    f["n_edm_songs"] = int(len(songs))
    f["n_solo_songs"] = int(len(solo))
    f["last_solo_top40"] = solo[solo["top40"] == 1].sort_values("debut").iloc[-1][
        ["title", "lead_artist", "debut_year", "peak"]].to_dict()
    f["last_solo_top10"] = solo[solo["top10"] == 1].sort_values("debut").iloc[-1][
        ["title", "lead_artist", "debut_year", "peak"]].to_dict()
    f["last_solo_song"] = solo.sort_values("debut").iloc[-1][
        ["title", "lead_artist", "debut_year", "peak"]].to_dict()
    f["solo_debuts_by_year"] = {int(k): int(v) for k, v in
                                solo.groupby("debut_year").size().items()}
    f["years_with_zero_solo_debuts"] = sorted(
        int(y) for y in range(2010, 2027)
        if y not in set(solo["debut_year"]) and y >= 2011)
    f["solo_songs_since_2018"] = solo[solo["debut_year"] >= 2018][
        ["title", "lead_artist", "debut_year", "peak", "weeks"]].to_dict("records")

    # ---- share: EDM's slice of the Hot 100 ----
    f["edm_share_peak"] = {"year": int(yearly["edm_share"].idxmax()),
                           "share": float(yearly["edm_share"].max())}
    f["edm_share_2025"] = float(yearly.loc[2025, "edm_share"])
    f["edm_share_2017"] = float(yearly.loc[2017, "edm_share"])
    f["edm_slots_by_year"] = {int(k): int(v) for k, v in yearly["edm_slots"].items()}
    f["edm_songs_debut_by_year"] = {int(k): int(v) for k, v in
                                    yearly["edm_songs_debut"].items()}

    # ---- the toll: collab share, EDM vs the whole chart ----
    y = yearly[(yearly.index >= 2011) & (yearly.index <= 2024)]
    f["collab_gap"] = {int(k): round(float(r["edm_collab_share"] - r["collab_share_all"]), 3)
                       for k, r in y.iterrows()}
    f["edm_collab_share_2012"] = float(yearly.loc[2012, "edm_collab_share"])
    f["edm_collab_share_2015"] = float(yearly.loc[2015, "edm_collab_share"])
    f["edm_collab_share_2019"] = float(yearly.loc[2019, "edm_collab_share"])
    f["chart_collab_share_2012"] = float(yearly.loc[2012, "collab_share_all"])
    f["chart_collab_share_2019"] = float(yearly.loc[2019, "collab_share_all"])

    # ---- billing mix by era (share of EDM slots) ----
    entries["era"] = entries["year"].apply(era_of)
    mix = (entries[entries["era"] != "pre"].groupby(["era", "edm_type"]).size()
           .unstack(fill_value=0))
    mix = mix.div(mix.sum(axis=1), axis=0).round(3)
    f["billing_mix_by_era"] = {e: {t: float(v) for t, v in row.items()}
                               for e, row in mix.iterrows()}
    f["billing_counts_by_era"] = {
        e: {t: int(v) for t, v in row.items()}
        for e, row in (entries[entries["era"] != "pre"]
                       .groupby(["era", "edm_type"]).size().unstack(fill_value=0)).iterrows()}

    # ---- hit rates: P(top 40) and P(top 10) by era x solo/collab ----
    hr = songs.groupby(["era", "is_solo"]).agg(
        n=("title", "size"), top40_rate=("top40", "mean"),
        top10_rate=("top10", "mean"), median_peak=("peak", "median"),
        median_weeks=("weeks", "median")).round(3)
    f["hit_rates"] = {f"{e}|{'solo' if s else 'collab'}": {k: (float(v) if isinstance(v, float) else int(v))
                      for k, v in row.items()} for (e, s), row in hr.iterrows()}

    # ---- longevity: median weeks on chart by era (completed runs only: debut <= 2024) ----
    done = songs[songs["debut_year"] <= 2024]
    lon = done.groupby("era")["weeks"].agg(["median", "mean", "count"]).round(2)
    f["longevity_by_era"] = {e: {k: float(v) for k, v in row.items()}
                             for e, row in lon.iterrows()}
    lon2 = done.groupby(["era", "is_solo"])["weeks"].median().round(1)
    f["longevity_by_era_solo"] = {f"{e}|{'solo' if s else 'collab'}": float(v)
                                  for (e, s), v in lon2.items()}

    # ---- survival: share of songs still on the chart at week k, by era ----
    surv = {}
    for e, g in done.groupby("era"):
        surv[e] = {k: round(float((g["weeks"] >= k).mean()), 3)
                   for k in [1, 4, 8, 12, 20, 30, 40]}
    f["survival_by_era"] = surv

    # ---- concentration: who is left ----
    conc = []
    for yr, g in entries.groupby("year"):
        leads = g["lead_artist"].value_counts()
        top3 = leads.head(3).sum() / len(g)
        conc.append({"year": int(yr), "distinct_lead_artists": int(g["lead_artist"].nunique()),
                     "top3_slot_share": round(float(top3), 3),
                     "top_artist": leads.index[0], "top_artist_slots": int(leads.iloc[0])})
    f["concentration_by_year"] = conc
    rem = entries[entries["year"] >= 2021]
    f["remnant_top_artists"] = (rem["lead_artist"].value_counts().head(8).to_dict())
    f["remnant_slots"] = int(len(rem))
    f["remnant_distinct_artists"] = int(rem["lead_artist"].nunique())

    # ---- the hired-gun era: EDM as featured act on someone else's record ----
    feat = songs[songs["edm_type"] == "edm_featured"]
    f["featured_by_era"] = {e: int(n) for e, n in feat.groupby("era").size().items()}
    f["featured_top10s"] = feat[feat["top10"] == 1][
        ["title", "lead_artist", "debut_year", "peak"]].to_dict("records")

    # ---- 2015: the year the toll arrived (zero solo rows, 13 debuts) ----
    y15 = songs[songs["debut_year"] == 2015][
        ["title", "lead_artist", "performer_debut", "peak", "weeks"]].sort_values("peak")
    f["songs_2015"] = y15.to_dict("records")

    # ---- solo songs' chart runs: the boom-era solo hits were real hits ----
    f["solo_top10s_all"] = solo[solo["top10"] == 1][
        ["title", "lead_artist", "debut_year", "peak", "weeks"]].to_dict("records")
    f["solo_median_weeks_boom"] = float(
        solo[solo["debut_year"] <= 2014]["weeks"].median())
    f["solo_median_weeks_since2018"] = float(
        solo[solo["debut_year"] >= 2018]["weeks"].median())

    (DATA / "findings.json").write_text(json.dumps(f, indent=1, default=str))
    print(json.dumps({k: f[k] for k in
                      ["n_edm_songs", "n_solo_songs", "last_solo_top40",
                       "last_solo_top10", "edm_share_peak", "edm_share_2025",
                       "hit_rates", "longevity_by_era", "remnant_top_artists"]},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
