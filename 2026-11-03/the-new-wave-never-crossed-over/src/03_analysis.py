"""Step 3: from raw Deezer album details to per-artist/cohort statistics.

Definitions (see README for why):
- A "release" is one deduplicated album object: same artist, same
  normalized title, same record_type, same release year counts once.
  This removes deluxe/clean/explicit duplicate listings of one single
  without merging genuinely different versions (a remix single carries
  the remixer's name in its title, so it survives).
- Headline output = singles + EPs. Albums are reported separately: on
  Deezer an artist's "album" shelf mixes studio albums with DJ-mix
  compilations, so album counts are not a clean new-music series.
- "recent" = calendar 2023-2025, the last three complete years. 2026 is
  partial and reported separately.
- A release counts as a collaboration when its contributor list names
  more than one distinct artist.
- Genre tags are Deezer's own per-release tags. "Pop" = any tag exactly
  "Pop"; "dance-family" = Dance, Electro, House, Techno, Electronic or
  Trance. A release can carry both.
"""

import json
import re
import unicodedata

import numpy as np
import pandas as pd
from scipy import stats

RAW = "data/deezer_albums_raw.jsonl"
OUT_CLEAN = "data/releases_clean.csv"
OUT_SUMMARY = "data/artist_summary.csv"
OUT_YEAR = "data/cohort_year.csv"
OUT_CURVE = "data/career_curve.csv"
OUT_ERA = "data/era_stats.csv"
OUT_JSON = "data/analysis_summary.json"

KEEP_TYPES = {"single", "ep", "album"}
RECENT = (2023, 2024, 2025)
DANCE_TAGS = {"Dance", "Electro", "House", "Techno", "Electronic", "Trance"}


def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
    return s.decode().strip().casefold()


def norm_title(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]", "", s.decode().casefold())


def year_of(date_str):
    try:
        y = int(str(date_str)[:4])
        return y if 1980 <= y <= 2026 else np.nan
    except (TypeError, ValueError):
        return np.nan


def main():
    df = pd.DataFrame([json.loads(line) for line in open(RAW)])
    print(f"raw album details: {len(df)}")
    print("record_type distribution:",
          df["record_type"].value_counts(dropna=False).to_dict())
    # main-artist sanity check
    df["main_match"] = [norm_name(m) == norm_name(p) for m, p in
                        zip(df["main_artist"], df["_panel_artist"])]
    print(f"main-artist mismatch share: {(~df['main_match']).mean():.4f}")
    mism = df[~df["main_match"]]
    if len(mism):
        print("mismatched main artists:",
              mism.groupby(["_panel_artist", "main_artist"]).size().to_dict())
    df = df[df["main_match"]].copy()
    df["year"] = df["release_date"].apply(year_of)
    df["dated"] = df["year"].notna()
    df = df[df["record_type"].isin(KEEP_TYPES)].copy()
    # dedupe: same artist + normalized title + type + year
    df["title_key"] = df["title"].apply(norm_title)
    df = df.sort_values("fans", ascending=False)
    before = len(df)
    df = df.drop_duplicates(
        subset=["_panel_artist", "title_key", "record_type", "year"],
        keep="first")
    print(f"deduped {before} -> {len(df)} releases")
    df["is_single_ep"] = df["record_type"].isin({"single", "ep"})
    df["is_collab"] = df["contributors"].apply(
        lambda c: len({norm_name(x) for x in (c or [])}) > 1)
    df["is_pop"] = df["genres"].apply(lambda g: "Pop" in (g or []))
    df["is_dance"] = df["genres"].apply(
        lambda g: bool(set(g or []) & DANCE_TAGS))
    df["single_duration"] = df.apply(
        lambda r: (np.mean([d for d in (r["track_durations"] or [])
                            if d]) if r["record_type"] == "single"
                   and r["track_durations"] else np.nan), axis=1)
    df.to_csv(OUT_CLEAN, index=False)

    se = df[df["is_single_ep"]].copy()
    print(f"singles+EPs: {len(se)}; dated share: {se['dated'].mean():.4f}")

    # ---- catalog revisits: a recent single/EP whose base title the same
    # artist already released in an earlier year (re-release, remix pack,
    # anniversary version). Base title = title with parenthetical and
    # bracket content stripped, then normalized. ----
    def base_title(t):
        t = re.sub(r"\([^)]*\)", "", str(t))
        t = re.sub(r"\[[^\]]*\]", "", t)
        return norm_title(t)

    df["base_title"] = df["title"].apply(base_title)
    se = se.assign(base_title=se["title"].apply(base_title))
    first_seen = {}
    for _, r in df[df["dated"]].sort_values("year").iterrows():
        key = (r["_panel_artist"], r["base_title"])
        if key not in first_seen:
            first_seen[key] = r["year"]
    se = se.assign(
        is_revisit=se.apply(
            lambda r: (r["dated"] and
                       first_seen.get((r["_panel_artist"], r["base_title"]),
                                      r["year"]) < r["year"]),
            axis=1))
    print(f"revisit share of singles+EPs: {se['is_revisit'].mean():.3f}")
    df = df.merge(se[["album_id", "base_title", "is_revisit"]],
                  on=["album_id", "base_title"], how="left")
    df.to_csv(OUT_CLEAN, index=False)

    summaries = []
    for (artist, cohort), g in se.groupby(["_panel_artist", "_panel_cohort"]):
        dated = g[g["dated"]]
        first_year = int(dated["year"].min()) if len(dated) else np.nan
        recent = dated[dated["year"].isin(RECENT)]
        y2026 = dated[dated["year"] == 2026]
        by_year = dated.groupby("year").size()
        all_g = df[df["_panel_artist"] == artist]
        summaries.append({
            "artist": artist, "cohort": cohort,
            "lifetime_single_ep": len(g),
            "lifetime_all": len(all_g),
            "first_year": first_year,
            "career_age_2025": (2025 - first_year)
            if pd.notna(first_year) else np.nan,
            "median_year": float(dated["year"].median()) if len(dated) else np.nan,
            "recent3": len(recent),
            "recent_rate": len(recent) / 3.0,
            "y2026": len(y2026),
            "revisit_share_recent": float(recent["is_revisit"].mean())
            if len(recent) else np.nan,
            "new_title_recent_rate": (len(recent) / 3.0) * (
                1 - float(recent["is_revisit"].mean())) if len(recent) else 0.0,
            "peak_year_output": int(by_year.max()) if len(by_year) else 0,
            "peak_year": int(by_year.idxmax()) if len(by_year) else np.nan,
            "single_share": float((g["record_type"] == "single").mean()),
            "album_share_all": float((all_g["record_type"] == "album").mean())
            if len(all_g) else np.nan,
            "collab_share": float(g["is_collab"].mean()),
            "pop_share": float(g["is_pop"].mean()),
            "dance_share": float(g["is_dance"].mean()),
            "mean_single_duration": float(dated["single_duration"].mean())
            if dated["single_duration"].notna().any() else np.nan,
            "undated_share": float((~g["dated"]).mean()),
        })
    s = pd.DataFrame(summaries).sort_values(["cohort", "artist"])
    s.to_csv(OUT_SUMMARY, index=False)

    # cohort x calendar year: singles+EPs per active artist
    dated_se = se[se["dated"]]
    first_map = s.set_index("artist")["first_year"].to_dict()
    year_rows = []
    for cohort, artists in s.groupby("cohort")["artist"]:
        artists = list(artists)
        for year in range(2005, 2026):
            active = [a for a in artists if first_map[a] <= year]
            n = len(dated_se[(dated_se["_panel_artist"].isin(active))
                             & (dated_se["year"] == year)])
            year_rows.append({"cohort": cohort, "year": year,
                              "active_artists": len(active), "releases": n,
                              "per_artist": n / len(active) if active else np.nan})
    pd.DataFrame(year_rows).to_csv(OUT_YEAR, index=False)

    # career-age curve
    curve_rows = []
    for _, r in s.iterrows():
        g = dated_se[dated_se["_panel_artist"] == r["artist"]]
        for year, n in g.groupby("year").size().items():
            curve_rows.append({"artist": r["artist"], "cohort": r["cohort"],
                               "career_year": int(year - r["first_year"]),
                               "n": int(n)})
    cc = pd.DataFrame(curve_rows)
    bucket_rows = []
    for lo, hi, label in [(0, 2, "0-2"), (3, 5, "3-5"), (6, 9, "6-9"),
                          (10, 14, "10-14"), (15, 99, "15+")]:
        sub = cc[(cc["career_year"] >= lo) & (cc["career_year"] <= hi)]
        denom = 0
        for _, r in s.iterrows():
            span_hi = min(hi, 2025 - r["first_year"])
            if span_hi >= lo:
                denom += span_hi - lo + 1
        bucket_rows.append({"bucket": label, "total": int(sub["n"].sum()),
                            "artist_years": denom,
                            "per_artist_year": sub["n"].sum() / denom
                            if denom else np.nan})
    pd.DataFrame(bucket_rows).to_csv(OUT_CURVE, index=False)

    # era stats
    def era(y):
        if y <= 2012:
            return "2005-2012"
        if y <= 2018:
            return "2013-2018"
        return "2019-2025"
    dated_se = dated_se.assign(era=dated_se["year"].apply(era))
    era_rows = []
    for e, g in dated_se.groupby("era"):
        era_rows.append({"era": e, "n": len(g),
                         "collab_share": float(g["is_collab"].mean()),
                         "pop_share": float(g["is_pop"].mean()),
                         "dance_share": float(g["is_dance"].mean()),
                         "mean_single_duration_sec": float(
                             g["single_duration"].mean())})
    pd.DataFrame(era_rows).to_csv(OUT_ERA, index=False)

    def cohort_stats(cohort):
        sub = s[s["cohort"] == cohort]
        return {"n_artists": len(sub),
                "mean_lifetime_single_ep": float(sub["lifetime_single_ep"].mean()),
                "mean_recent_rate": float(sub["recent_rate"].mean()),
                "median_recent_rate": float(sub["recent_rate"].median()),
                "mean_median_year": float(sub["median_year"].mean()),
                "mean_single_share": float(sub["single_share"].mean()),
                "mean_collab_share": float(sub["collab_share"].mean()),
                "mean_pop_share": float(sub["pop_share"].mean()),
                "mean_dance_share": float(sub["dance_share"].mean()),
                "mean_career_age": float(sub["career_age_2025"].mean())}
    cohorts = {c: cohort_stats(c) for c in ["pioneer", "peak-edm", "new-wave"]}
    # revisit aggregates + new-title rates
    for c in cohorts:
        sub = s[s["cohort"] == c]
        cohorts[c]["mean_revisit_share_recent"] = float(
            sub["revisit_share_recent"].mean())
        cohorts[c]["mean_new_title_recent_rate"] = float(
            sub["new_title_recent_rate"].mean())
        cohorts[c]["median_new_title_recent_rate"] = float(
            sub["new_title_recent_rate"].median())
    mw = stats.mannwhitneyu(
        s[s["cohort"] == "pioneer"]["recent_rate"],
        s[s["cohort"] == "new-wave"]["recent_rate"], alternative="two-sided")
    mw2 = stats.mannwhitneyu(
        s[s["cohort"] == "peak-edm"]["recent_rate"],
        s[s["cohort"] == "new-wave"]["recent_rate"], alternative="two-sided")
    mw3 = stats.mannwhitneyu(
        s[s["cohort"] == "pioneer"]["new_title_recent_rate"],
        s[s["cohort"] == "new-wave"]["new_title_recent_rate"],
        alternative="two-sided")
    panel = pd.read_csv("data/artists.csv")
    excluded = [a for a in panel["name"] if a not in set(s["artist"])]
    summary = {
        "raw_album_details": int(len(pd.DataFrame(
            [json.loads(line) for line in open(RAW)]))),
        "deduped_releases": len(df),
        "singles_eps": len(se),
        "dated_share_single_ep": float(se["dated"].mean()),
        "excluded_artists": {
            a: ("Deezer's artist-albums endpoint returns only album-type "
                "items (424, mostly radio episodes and compilations) for "
                "this artist; his singles exist on Deezer but are not "
                "returned, so singles+EPs cannot be measured consistently "
                "with the rest of the panel.")
            for a in excluded},
        "cohorts": cohorts,
        "mannwhitney_pioneer_vs_newwave_recent_rate": {
            "U": float(mw.statistic), "p": float(mw.pvalue)},
        "mannwhitney_peak_vs_newwave_recent_rate": {
            "U": float(mw2.statistic), "p": float(mw2.pvalue)},
        "mannwhitney_pioneer_vs_newwave_newtitle_rate": {
            "U": float(mw3.statistic), "p": float(mw3.pvalue)},
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
