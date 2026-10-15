"""Analysis for 'Your Genre Tag Is Your Ceiling'.

Parts:
  1. The partition test — do tracks ever appear on two genre charts?
  2. Shelf ceilings — per-genre conversion into the overall Top 100,
     freshness economies, label concentration.
  3. The artist bridge network — co-credit graph, cross-genre artists,
     genre pairs linked by shared artists, communities.
  4. The remix economy — how often charting tracks carry remixers, and
     whether a remixer who out-charts the original artist helps.

Writes data/tracks.csv, data/appearances.csv, data/genre_stats.csv,
data/artist_stats.csv and data/findings.json (every number the README uses).
"""
import json, gzip, os, itertools
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SNAPSHOT_DATE = pd.Timestamp("2026-10-15")


# ---------------------------------------------------------------- load / tidy
def load():
    with gzip.open(os.path.join(DATA, "raw", "charts_raw.json.gz"), "rt") as f:
        raw = json.load(f)
    apps, tracks = [], {}
    for chart, payload in raw.items():
        for i, t in enumerate(payload["results"]):
            apps.append({"chart": chart, "rank": i + 1, "track_id": t["id"]})
            if t["id"] in tracks:
                continue
            key = t.get("key") or {}
            tracks[t["id"]] = {
                "track_id": t["id"],
                "name": t["name"],
                "mix": t.get("mix_name") or "",
                "artists": "; ".join(a["name"] for a in t.get("artists", [])),
                "artist_names": [a["name"] for a in t.get("artists", [])],
                "remixer_names": [a["name"] for a in t.get("remixers", [])],
                "genre": (t.get("genre") or {}).get("name"),
                "genre_slug": (t.get("genre") or {}).get("slug"),
                "sub_genre": (t.get("sub_genre") or {}).get("name")
                             if t.get("sub_genre") else None,
                "bpm": t.get("bpm"),
                "key_name": key.get("name"),
                "key_mode": (key.get("chord_type") or {}).get("name"),
                "length_ms": t.get("length_ms"),
                "label": t["release"]["label"]["name"],
                "release_date": t.get("new_release_date") or t.get("publish_date"),
                "price_usd": (t.get("price") or {}).get("value"),
                "explicit": bool(t.get("is_explicit")),
                "exclusive": bool(t.get("exclusive")),
            }
    A = pd.DataFrame(apps)
    T = pd.DataFrame(list(tracks.values()))
    genre_charts = [c for c in raw if c != "main"]
    main_ids = set(A.loc[A.chart == "main", "track_id"])
    T["in_main"] = T.track_id.isin(main_ids)
    T["release_date"] = pd.to_datetime(T["release_date"])
    T["age_days"] = (SNAPSHOT_DATE - T["release_date"]).dt.days
    T["len_min"] = T.length_ms / 60000
    T["n_artists"] = T.artist_names.apply(len)
    T["has_remixer"] = T.remixer_names.apply(len) > 0
    T["extended"] = T.mix.str.contains("Extended", case=False)
    return raw, A, T, genre_charts


# ---------------------------------------------------------------- part 1 + 2
def shelf_stats(A, T, genre_charts):
    per_chart = A[A.chart.isin(genre_charts)].groupby("track_id").size()
    partition = {
        "chart_slots": int(len(A)),
        "genre_chart_slots": int((A.chart != "main").sum()),
        "unique_tracks": int(T.track_id.nunique()),
        "tracks_on_2plus_genre_charts": int((per_chart > 1).sum()),
        "main_tracks_sourced_from_genre_charts": int(T.in_main.sum()),
    }
    rows = []
    for g in genre_charts:
        sub = T[T.genre_slug == g]
        ages = sub.age_days
        vc = sub.label.value_counts(normalize=True)
        rows.append({
            "genre_slug": g,
            "genre": sub.genre.iloc[0],
            "tracks": len(sub),
            "in_main": int(sub.in_main.sum()),
            "main_rate": round(float(sub.in_main.mean()), 3),
            "median_age_days": float(ages.median()),
            "share_le_14d": round(float((ages <= 14).mean()), 3),
            "share_gt_365d": round(float((ages > 365).mean()), 3),
            "median_bpm": float(sub.bpm.median()),
            "median_len_min": round(float(sub.len_min.median()), 2),
            "extended_share": round(float(sub.extended.mean()), 3),
            "collab_share": round(float((sub.n_artists > 1).mean()), 3),
            "remixer_share": round(float(sub.has_remixer.mean()), 3),
            "unique_labels": int(sub.label.nunique()),
            "label_hhi": round(float((vc ** 2).sum() * 10000), 0),
            "top_label": sub.label.value_counts().index[0],
            "top_label_tracks": int(sub.label.value_counts().iloc[0]),
            "median_price_usd": float(sub.price_usd.median()),
        })
    G = pd.DataFrame(rows).sort_values("main_rate", ascending=False)
    main = A[A.chart == "main"].merge(T[["track_id", "genre_slug", "age_days"]],
                                      on="track_id")
    main_block = {
        "composition": {k: int(v) for k, v in
                        main.genre_slug.value_counts().items()},
        "house_family_share": round(float(main.genre_slug.isin(
            ["house", "tech-house"]).mean()), 3),
        "median_age_main": float(main.age_days.median()),
        "median_age_nonmain": float(T.loc[~T.in_main, "age_days"].median()),
        "median_main_rank_by_genre": {k: float(v) for k, v in
                                      main.groupby("genre_slug")["rank"]
                                      .median().items()},
        "genres_with_exactly_1_main_track": int(
            (main.genre_slug.value_counts() == 1).sum()),
    }
    return partition, G, main_block


# ---------------------------------------------------------------- part 3
def artist_network(A, T, genre_charts):
    ae = (A[A.chart.isin(genre_charts)]
          .merge(T[["track_id", "genre_slug"]], on="track_id")
          .merge(T[["track_id", "artist_names"]], on="track_id")
          .explode("artist_names"))
    stats = ae.groupby("artist_names").agg(
        tracks=("track_id", "nunique"), genres=("genre_slug", "nunique"))
    pair_counts = Counter()
    for gs in ae.groupby("artist_names").genre_slug.apply(lambda s: sorted(set(s))):
        for a, b in itertools.combinations(gs, 2):
            pair_counts[(a, b)] += 1

    # co-credit graph: nodes are artists, edges are shared track credits
    G = nx.Graph()
    for names in T.artist_names:
        for a in names:
            G.add_node(a)
        for a, b in itertools.combinations(sorted(set(names)), 2):
            if G.has_edge(a, b):
                G[a][b]["weight"] += 1
            else:
                G.add_edge(a, b, weight=1)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    largest = G.subgraph(comps[0]).copy()
    pagerank = nx.pagerank(largest, weight="weight")
    between = nx.betweenness_centrality(largest, k=150, seed=7, weight="weight")
    comms = nx.community.louvain_communities(largest, weight="weight", seed=7)
    stats = stats.reset_index().rename(columns={"artist_names": "artist"})
    deg = dict(G.degree())
    stats["degree"] = stats.artist.map(deg).fillna(0).astype(int)
    stats["pagerank_largest"] = stats.artist.map(pagerank)
    stats["betweenness_largest"] = stats.artist.map(between)
    comm_id = {}
    for i, c in enumerate(sorted(comms, key=len, reverse=True)):
        for a in c:
            comm_id[a] = i
    stats["community"] = stats.artist.map(comm_id)

    # what genre does each big community live in?
    primary = (ae.groupby("artist_names").genre_slug
               .agg(lambda s: s.value_counts().index[0]))
    comm_genre = {}
    for cid, members in enumerate(sorted(comms, key=len, reverse=True)[:6]):
        mix = Counter(primary.get(m) for m in members)
        comm_genre[f"community_{cid}"] = {
            "size": len(members),
            "top_genres": {k: int(v) for k, v in mix.most_common(3)},
        }
    net = {
        "artists": int(len(stats)),
        "artists_2plus_genres": int((stats.genres >= 2).sum()),
        "share_artists_2plus_genres": round(float((stats.genres >= 2).mean()), 3),
        "artists_3plus_genres": int((stats.genres >= 3).sum()),
        "max_genres": int(stats.genres.max()),
        "top_crossers": stats.sort_values(["genres", "tracks"],
                                          ascending=False)
                             .head(10)[["artist", "tracks", "genres"]]
                             .to_dict("records"),
        "top_by_tracks": stats.sort_values("tracks", ascending=False)
                          .head(10)[["artist", "tracks", "genres"]]
                          .to_dict("records"),
        "genre_pairs_shared_artists_top": [
            {"pair": list(k), "shared_artists": v}
            for k, v in pair_counts.most_common(10)],
        "genre_pairs_total_with_sharing": int(len(pair_counts)),
        "graph": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                  "components": len(comps), "largest_component": len(comps[0]),
                  "isolated_artists": int(sum(1 for c in comps if len(c) == 1))},
        "top_degree": sorted(deg.items(), key=lambda kv: -kv[1])[:10],
        "communities": comm_genre,
    }
    return stats, net


# ---------------------------------------------------------------- part 4
def remix_economy(T, artist_stats):
    presence = artist_stats.set_index("artist")["tracks"].to_dict()
    sub = T[T.has_remixer].copy()

    def remixer_outranks(row):
        orig = max((presence.get(a, 0) for a in row.artist_names), default=0)
        rem = max((presence.get(a, 0) for a in row.remixer_names), default=0)
        return rem > orig

    sub["remixer_outranks"] = sub.apply(remixer_outranks, axis=1)
    rem_counts = Counter(a for ns in T.remixer_names for a in ns)
    return {
        "tracks_with_remixer": int(T.has_remixer.sum()),
        "share": round(float(T.has_remixer.mean()), 3),
        "main_rate_with_remixer": round(float(sub.in_main.mean()), 3),
        "main_rate_without": round(float(T.loc[~T.has_remixer, "in_main"].mean()), 3),
        "share_remixer_outranks_original": round(
            float(sub.remixer_outranks.mean()), 3),
        "main_rate_remixer_outranks": round(
            float(sub.loc[sub.remixer_outranks, "in_main"].mean()), 3)
            if sub.remixer_outranks.any() else None,
        "main_rate_remixer_not_outrank": round(
            float(sub.loc[~sub.remixer_outranks, "in_main"].mean()), 3)
            if (~sub.remixer_outranks).any() else None,
        "top_remixers": rem_counts.most_common(10),
    }


def main():
    raw, A, T, genre_charts = load()
    partition, G, main_block = shelf_stats(A, T, genre_charts)
    artist_stats, net = artist_network(A, T, genre_charts)
    remix = remix_economy(T, artist_stats)

    findings = {
        "snapshot": "2026-10-15",
        "source": "Beatport overall Top 100 + 17 homepage-promoted genre Top 100s",
        "partition": partition,
        "main_chart": main_block,
        "network": net,
        "remix": remix,
        "collab_share_overall": round(float((T.n_artists > 1).mean()), 3),
        "unique_labels_overall": int(T.label.nunique()),
        "subgenre_tagged_share": round(float(T.sub_genre.notna().mean()), 3),
        "minor_key_share": round(float((T.key_mode == "Minor").mean()), 3),
    }
    T_out = T.drop(columns=["artist_names", "remixer_names"]).copy()
    T_out["artists"] = T.artist_names.str.join("; ")
    T_out["remixers"] = T.remixer_names.str.join("; ")
    T_out.to_csv(os.path.join(DATA, "tracks.csv"), index=False)
    A.to_csv(os.path.join(DATA, "appearances.csv"), index=False)
    G.to_csv(os.path.join(DATA, "genre_stats.csv"), index=False)
    artist_stats.to_csv(os.path.join(DATA, "artist_stats.csv"), index=False)
    with open(os.path.join(DATA, "findings.json"), "w") as f:
        json.dump(findings, f, indent=2, default=str)
    print(json.dumps(findings, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
