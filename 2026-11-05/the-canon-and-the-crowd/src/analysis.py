"""Analysis for The Canon and the Crowd.

Reads data/cache/ (see collect.py) and produces:
  - results.json: every metric per figure
  - findings.txt: the headline numbers in plain text
  - charts/*.png: six figures

Measurements:
  CANON  = the field's own structure: PageRank + in-degree inside the
           Wikipedia link graph of the 91-node panel, distance to the
           "Philosophy" article, Louvain-style communities, and a
           cross-tradition bridge score (share of Eastern-Western
           shortest paths running through each node).
  CROWD  = the public's reading: Google Books Ngram name frequency in
           print 1900-2019, and median monthly Wikipedia pageviews
           2023-2026 (median, not mean, so the Laozi bot step of
           March 2023 cannot crown a phantom).
  QUOTABILITY = median sentence length and aphorism share in each
           figure's Gutenberg text, tested against crowd rank.
"""

import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import sys
sys.path.insert(0, str(Path(__file__).parent))
from panel import PHILOSOPHERS, CONCEPTS, DISPLAY_NAMES

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

YEARS = list(range(1900, 2020))
TRAD_COLOR = {"Western": "#2f5d8a", "Eastern": "#c25e3a", "Concept": "#8a8a8a"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 13, "axes.titleweight": "bold",
    "figure.dpi": 150,
})


def load(name):
    return json.loads((CACHE / name).read_text())


# ------------------------------------------------------------------ load
links = load("wikipedia_links.json")
views = load("pageviews.json")
ngrams = load("ngrams.json")
resolved = load("resolved_titles.json")
gmeta = load("gutenberg_meta.json")

phil_titles = [p[0] for p in PHILOSOPHERS]
# Five requested titles redirect to different canonical article titles.
# The links/pageviews caches are keyed by canonical title; ngrams and
# Gutenberg metadata are keyed by the panel (display) title.
CANON = {}
for t in phil_titles + CONCEPTS:
    CANON[t] = t
for canon_title, info in resolved.items():
    if info.get("requested"):
        CANON[info["requested"]] = canon_title
DISPLAY = {c: d for d, c in CANON.items()}
DISPLAY.update(DISPLAY_NAMES)
# ngrams/Gutenberg caches are keyed by panel title, not display name.
PANEL_TITLE = {c: d for d, c in CANON.items()}
meta = {CANON[p[0]]: {"display": p[0], "tradition": p[1], "gender": p[2]}
        for p in PHILOSOPHERS}
nodes = sorted(set(links.keys()))
assert "Philosophy" in nodes, "Philosophy article missing from panel"

# ------------------------------------------------------------------ graph
G = nx.DiGraph()
G.add_nodes_from(nodes)
for a in nodes:
    for b in links.get(a, []):
        if b in G and a != b:
            G.add_edge(a, b)

pr = nx.pagerank(G, alpha=0.85)
in_deg = dict(G.in_degree())
out_deg = dict(G.out_degree())
between = nx.betweenness_centrality(G.to_undirected(), normalized=True)
communities = list(nx.community.greedy_modularity_communities(G.to_undirected()))
comm_of = {}
for i, c in enumerate(communities):
    for n in c:
        comm_of[n] = i

# distance to Philosophy (directed: A -> ... -> Philosophy)
dist_to_phil = {}
for n in nodes:
    try:
        dist_to_phil[n] = nx.shortest_path_length(G, source=n, target="Philosophy")
    except nx.NetworkXNoPath:
        dist_to_phil[n] = None

# cross-tradition bridge score: share of Eastern-Western shortest paths
# (in the undirected panel graph) that run through each node.
UG = G.to_undirected()
eastern = [CANON[t] for t in phil_titles if meta[CANON[t]]["tradition"] == "Eastern"]
western = [CANON[t] for t in phil_titles if meta[CANON[t]]["tradition"] == "Western"]
bridge = defaultdict(float)
pair_total = 0
for e in eastern:
    for w in western:
        try:
            paths = list(nx.all_shortest_paths(UG, e, w))
        except nx.NetworkXNoPath:
            continue
        pair_total += 1
        for p in paths:
            for n in p[1:-1]:
                bridge[n] += 1.0 / len(paths)
bridge_score = {n: bridge[n] / pair_total if pair_total else 0.0 for n in nodes}

# ------------------------------------------------------------- crowd data
def ngram_stats(canonical_title):
    s = ngrams.get(PANEL_TITLE[canonical_title])
    if not s:
        return {}
    arr = np.array(s, dtype=float)
    return {
        "ngram_mean_2000_19": float(arr[100:].mean()),
        "ngram_1900": float(arr[0]),
        "ngram_1950": float(arr[50]),
        "ngram_2019": float(arr[-1]),
        "ngram_peak_year": int(YEARS[int(arr.argmax())]),
        "ngram_growth_1900_2019": float(arr[-1] / arr[0]) if arr[0] > 0 else None,
        "ngram_series": [float(v) for v in arr],
    }


def pv_stats(title):
    m = views.get(title, {})
    vals = [v for k, v in m.items() if k >= "202301"]
    if not vals:
        return {}
    return {
        "pv_median_2023_26": float(np.median(vals)),
        "pv_mean_2023_26": float(np.mean(vals)),
        "pv_months": len(vals),
    }


# ------------------------------------------------------- Gutenberg sentences
def clean_gutenberg(text):
    start = re.search(r"\*\*\* START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
                      text, re.S)
    if start:
        text = text[start.end():]
    end = re.search(r"\*\*\* END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
                    text, re.S)
    if end:
        text = text[:end.start()]
    text = re.sub(r"\[[0-9]+\]", " ", text)          # footnote markers
    text = re.sub(r"\s+", " ", text)
    return text


def sentence_stats(text):
    text = clean_gutenberg(text)
    # split on sentence-ending punctuation followed by a capital or the end
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\(\[])|\n+", text)
    lens = []
    for p in parts:
        words = re.findall(r"[A-Za-zÀ-ÿ']+", p)
        if 2 <= len(words) <= 120:
            lens.append(len(words))
    if len(lens) < 50:
        return {}
    return {
        "sentences": len(lens),
        "median_sentence_words": float(np.median(lens)),
        "mean_sentence_words": float(np.mean(lens)),
        "aphorism_share": float(np.mean([l < 10 for l in lens])),
        "long_sentence_share": float(np.mean([l >= 40 for l in lens])),
    }


gutenberg_stats = {}
for figure, info in gmeta.items():
    text = (CACHE / info["file"]).read_text(errors="replace")
    st = sentence_stats(text)
    gutenberg_stats[CANON[figure]] = st
    print(f"  gutenberg {figure}: {st}")

# ------------------------------------------------------------------ table
rows = []
for t in phil_titles:
    c = CANON[t]
    r = {"figure": DISPLAY[c], "tradition": meta[c]["tradition"], "gender": meta[c]["gender"],
         "pagerank": pr[c], "in_degree": in_deg[c], "out_degree": out_deg[c],
         "betweenness": between[c], "community": comm_of[c],
         "dist_to_philosophy": dist_to_phil[c],
         "bridge_score": bridge_score[c]}
    r.update(ngram_stats(c))
    r.update(pv_stats(c))
    gs = gutenberg_stats.get(c, {})
    for k in ("median_sentence_words", "mean_sentence_words",
              "aphorism_share", "long_sentence_share", "sentences"):
        if k in gs:
            r[k] = gs[k]
    rows.append(r)

df = pd.DataFrame(rows)
df["canon_rank"] = df["pagerank"].rank(ascending=False, method="min").astype(int)
df["crowd_rank_ngram"] = df["ngram_mean_2000_19"].rank(ascending=False, method="min").astype(int)
df["crowd_rank_pv"] = df["pv_median_2023_26"].rank(ascending=False, method="min").astype(int)
df["rank_gap_ngram"] = df["canon_rank"] - df["crowd_rank_ngram"]
df = df.sort_values("canon_rank")

# concept rows for the network chart
concept_rows = []
for t in CONCEPTS:
    c = CANON[t]
    concept_rows.append({"figure": DISPLAY[c], "tradition": "Concept", "pagerank": pr[c],
                         "in_degree": in_deg[c], "community": comm_of[c],
                         "betweenness": between[c],
                         "dist_to_philosophy": dist_to_phil[c],
                         "bridge_score": bridge_score[c]})
cdf = pd.DataFrame(concept_rows)

# ------------------------------------------------------------- correlations
def spear(a, b, frame):
    sub = frame.dropna(subset=[a, b])
    rho, p = spearmanr(sub[a], sub[b])
    return float(rho), float(p), len(sub)

corr_all_ng, p_all_ng, n_all = spear("pagerank", "ngram_mean_2000_19", df)
corr_all_pv, p_all_pv, _ = spear("pagerank", "pv_median_2023_26", df)
corr_w_ng, p_w_ng, _ = spear("pagerank", "ngram_mean_2000_19",
                            df[df["tradition"] == "Western"])
corr_e_ng, p_e_ng, _ = spear("pagerank", "ngram_mean_2000_19",
                            df[df["tradition"] == "Eastern"])
corr_ng_pv, p_ng_pv, _ = spear("ngram_mean_2000_19", "pv_median_2023_26", df)
corr_sent_ng, p_sent_ng, n_sent = spear("median_sentence_words",
                                        "ngram_mean_2000_19", df)
corr_sent_pv, p_sent_pv, _ = spear("median_sentence_words",
                                   "pv_median_2023_26", df)
corr_aphor_ng, p_aphor_ng, _ = spear("aphorism_share", "ngram_mean_2000_19", df)
corr_aphor_pv, p_aphor_pv, _ = spear("aphorism_share", "pv_median_2023_26", df)
corr_sent_canon, p_sent_canon, _ = spear("median_sentence_words", "pagerank", df)

# tradition medians
med = df.groupby("tradition").agg(
    pagerank_med=("pagerank", "median"),
    dist_med=("dist_to_philosophy", "median"),
    dist_mean=("dist_to_philosophy", "mean"),
    ngram_med=("ngram_mean_2000_19", "median"),
    pv_med=("pv_median_2023_26", "median"),
    n=("figure", "count"),
)
gender_med = df.groupby("gender").agg(
    pagerank_med=("pagerank", "median"), ngram_med=("ngram_mean_2000_19", "median"),
    pv_med=("pv_median_2023_26", "median"), n=("figure", "count"))

# communities: composition
comm_summary = []
for i, c in enumerate(communities):
    members = [n for n in c if n in meta]
    trads = pd.Series([meta[n]["tradition"] for n in members]).value_counts().to_dict()
    concepts = [n for n in c if n in CONCEPTS]
    comm_summary.append({"community": i, "size": len(c), "philosophers": len(members),
                         "traditions": trads, "concepts": concepts,
                         "members": sorted(DISPLAY.get(n, n) for n in c)})

# edges between traditions (undirected, philosopher-philosopher only)
cross = within_w = within_e = 0
for a, b in UG.edges():
    if a in meta and b in meta:
        ta, tb = meta[a]["tradition"], meta[b]["tradition"]
        if ta != tb:
            cross += 1
        elif ta == "Western":
            within_w += 1
        else:
            within_e += 1

# edge densities (undirected pairs, philosopher-philosopher only)
n_e, n_w = len(eastern), len(western)
dens = {"cross": cross / (n_e * n_w),
        "within_western": within_w / (n_w * (n_w - 1) / 2),
        "within_eastern": within_e / (n_e * (n_e - 1) / 2) if n_e > 1 else None}
# Schopenhauer's bridge rank (the textbook bridge candidate)
bridge_ranked = sorted(bridge_score.items(), key=lambda kv: -kv[1])
schop_rank = [DISPLAY.get(k, k) for k, _ in bridge_ranked].index("Arthur Schopenhauer") + 1
schop_score = bridge_score[CANON["Arthur Schopenhauer"]]

# bridge top 10
bridge_top = sorted(bridge_score.items(), key=lambda kv: -kv[1])[:10]
# which nodes do Eastern figures link to directly?
east_out = defaultdict(int)
for e in eastern:
    for b in G.successors(e):
        if b in meta and meta[b]["tradition"] == "Western":
            east_out[b] += 1
west_in_from_east = sorted(east_out.items(), key=lambda kv: -kv[1])

# Ngram rank movement: 1900 vs 2019
df["ngram_rank_1900"] = df["ngram_series"].apply(lambda s: s[0]).rank(
    ascending=False, method="min").astype(int)
df["ngram_rank_2019"] = df["ngram_series"].apply(lambda s: s[-1]).rank(
    ascending=False, method="min").astype(int)
df["ngram_rank_move"] = df["ngram_rank_1900"] - df["ngram_rank_2019"]

# ------------------------------------------------------------------ save
out = {
    "panel_n_philosophers": len(phil_titles),
    "panel_n_concepts": len(CONCEPTS),
    "graph_edges": G.number_of_edges(),
    "graph_nodes": G.number_of_nodes(),
    "correlations": {
        "canon_vs_crowd_ngram": {"rho": corr_all_ng, "p": p_all_ng, "n": n_all},
        "canon_vs_crowd_pageviews": {"rho": corr_all_pv, "p": p_all_pv},
        "canon_vs_crowd_ngram_western": {"rho": corr_w_ng, "p": p_w_ng},
        "canon_vs_crowd_ngram_eastern": {"rho": corr_e_ng, "p": p_e_ng},
        "ngram_vs_pageviews": {"rho": corr_ng_pv, "p": p_ng_pv},
        "sentence_length_vs_crowd_ngram": {"rho": corr_sent_ng, "p": p_sent_ng, "n": n_sent},
        "sentence_length_vs_crowd_pv": {"rho": corr_sent_pv, "p": p_sent_pv},
        "aphorism_share_vs_crowd_ngram": {"rho": corr_aphor_ng, "p": p_aphor_ng},
        "aphorism_share_vs_crowd_pv": {"rho": corr_aphor_pv, "p": p_aphor_pv},
        "sentence_length_vs_canon": {"rho": corr_sent_canon, "p": p_sent_canon},
    },
    "edge_densities": dens,
    "schopenhauer_bridge": {"rank": schop_rank, "score": schop_score,
                            "n_nodes": len(bridge_ranked)},
    "tradition_medians": med.to_dict(orient="index"),
    "gender_medians": gender_med.to_dict(orient="index"),
    "communities": comm_summary,
    "philosopher_edges": {"cross_tradition": cross, "within_western": within_w,
                          "within_eastern": within_e},
    "bridge_top10": [{"figure": DISPLAY.get(k, k), "bridge_score": v} for k, v in bridge_top],
    "western_figures_most_linked_from_east": [
        {"figure": DISPLAY.get(k, k), "n_eastern_linkers": v} for k, v in west_in_from_east[:10]],
    "figures": df.drop(columns=["ngram_series"]).to_dict(orient="records"),
    "concepts": cdf.to_dict(orient="records"),
    "ngram_series": {t: ngrams[t] for t in phil_titles if ngrams.get(t)},
}
(ROOT / "results.json").write_text(json.dumps(out, indent=2))

# ------------------------------------------------------------------ charts
# 1. Canon rank vs crowd rank
fig, ax = plt.subplots(figsize=(9, 7))
for trad, sub in df.groupby("tradition"):
    ax.scatter(sub["canon_rank"], sub["crowd_rank_ngram"], s=70,
               color=TRAD_COLOR[trad], alpha=0.8, label=trad, edgecolor="white")
ax.plot([1, 70], [1, 70], "k--", lw=1, alpha=0.5)
ax.invert_xaxis(); ax.invert_yaxis()
ax.set_xlabel("Canon rank (Wikipedia link PageRank, 1 = most central)")
ax.set_ylabel("Crowd rank (name frequency in books 2000-2019, 1 = most read)")
ax.set_title("The canon and the crowd agree at the top, and diverge everywhere else")
offsets = {"Immanuel Kant": (-72, -16), "Aristotle": (4, 8),
           "Gautama Buddha": (4, 4), "Laozi": (4, 4)}
for _, r in df.iterrows():
    if abs(r["rank_gap_ngram"]) >= 25 or r["figure"] in (
            "Immanuel Kant", "Marcus Aurelius", "Laozi", "Aristotle"):
        dx, dy = offsets.get(r["figure"], (4, 4))
        ax.annotate(r["figure"], (r["canon_rank"], r["crowd_rank_ngram"]),
                    fontsize=9, xytext=(dx, dy), textcoords="offset points")
ax.legend(title="Tradition", loc="lower right")
fig.tight_layout(); fig.savefig(CHARTS / "canon_vs_crowd.png"); plt.close(fig)

# 2. Top 10 canon vs top 10 crowd
fig, axes = plt.subplots(1, 2, figsize=(11, 6), sharey=False)
top_canon = df.nsmallest(10, "canon_rank").iloc[::-1]
top_crowd = df.nsmallest(10, "crowd_rank_ngram").iloc[::-1]
for ax, sub, col, title in [
        (axes[0], top_canon, "pagerank", "Top 10 by canon centrality (PageRank)"),
        (axes[1], top_crowd, "ngram_mean_2000_19", "Top 10 by crowd attention (books, 2000-19)")]:
    colors = [TRAD_COLOR[t] for t in sub["tradition"]]
    ax.barh(sub["figure"], sub[col], color=colors)
    ax.set_title(title, fontsize=11)
    ax.tick_params(labelsize=9)
fig.suptitle("Two different top tens", fontsize=13, fontweight="bold")
fig.tight_layout(); fig.savefig(CHARTS / "top10_both.png"); plt.close(fig)

# 3. Network: communities, sized by PageRank. Layout on the giant
# component only; the three isolates (Zhuangzi, Xunzi, Phenomenology)
# are placed by hand at the foot of the figure, labelled as isolates.
giant = max(nx.connected_components(UG), key=len)
singletons = [n for n in nodes if n not in giant]
pos = nx.kamada_kawai_layout(UG.subgraph(giant))
for i, n in enumerate(singletons):
    pos[n] = np.array([-0.9 + 0.9 * i, -1.25])
fig, ax = plt.subplots(figsize=(12, 9))
cmap = plt.get_cmap("tab10")
for i, c in enumerate(communities):
    members = [n for n in c if n in giant]
    if not members:
        continue
    sizes = [120 + 2600 * pr[n] for n in members]
    nx.draw_networkx_nodes(UG, pos, nodelist=members, node_size=sizes,
                           node_color=[cmap(i % 10)] * len(members),
                           alpha=0.85, ax=ax, edgecolors="white", linewidths=0.5)
nx.draw_networkx_nodes(UG, pos, nodelist=singletons, node_size=160,
                       node_color="#666666", alpha=0.85, ax=ax,
                       edgecolors="white", linewidths=0.5)
nx.draw_networkx_edges(UG, pos, alpha=0.10, ax=ax, width=0.6)
label_nodes = ["Plato", "Aristotle", "Laozi", CANON["Nishida Kitaro"],
               "The Buddha", "Philosophy", "Arthur Schopenhauer",
               "Marcus Aurelius"]
label_offsets = {"Plato": (-8, -14), "Aristotle": (6, 8), "Laozi": (6, 6),
                 CANON["Nishida Kitaro"]: (6, 6), "The Buddha": (6, 4),
                 "Philosophy": (-52, -16), "Arthur Schopenhauer": (6, -14),
                 "Marcus Aurelius": (6, 6)}
for n in label_nodes:
    x, y = pos[n]
    dx, dy = label_offsets[n]
    ax.annotate(DISPLAY.get(n, n), (x, y), fontsize=9,
                xytext=(dx, dy), textcoords="offset points")
for n in singletons:
    x, y = pos[n]
    ax.annotate(f"{DISPLAY.get(n, n)} (isolated)", (x, y), fontsize=9,
                xytext=(0, 10), textcoords="offset points", ha="center")
ax.set_title("The canon sorts by era and role, not by civilization. The East has no island of its own.")
ax.axis("off")
fig.tight_layout(); fig.savefig(CHARTS / "network.png"); plt.close(fig)

# 4. Ngram time series for the headline names
names = ["Marcus Aurelius", "Laozi", "Friedrich Nietzsche", "Immanuel Kant",
         "Confucius", "Aristotle", "David Hume", "Arthur Schopenhauer"]
fig, ax = plt.subplots(figsize=(10, 5.5))
for t in names:
    s = ngrams.get(t)
    if s:
        ax.plot(YEARS, s, label=t, lw=1.8)
ax.set_yscale("log")
ax.set_xlabel("Year"); ax.set_ylabel("Frequency in English books (log scale)")
ax.set_title("In print, the system-builders never lost the top. The Stoics slid.")
ax.legend(fontsize=9, ncol=2, loc="upper left")
fig.tight_layout(); fig.savefig(CHARTS / "ngram_timeseries.png"); plt.close(fig)

# 5. Distance to Philosophy by tradition
fig, ax = plt.subplots(figsize=(8, 5))
d = df.dropna(subset=["dist_to_philosophy"])
med_d = d.groupby("tradition")["dist_to_philosophy"].median()
ax.bar(med_d.index, med_d.values,
       color=[TRAD_COLOR[t] for t in med_d.index])
for i, (t, v) in enumerate(med_d.items()):
    ax.text(i, v + 0.08, f"median {v:.0f}", ha="center", fontsize=11)
ax.set_ylabel("Shortest path (links) to the 'Philosophy' article")
ax.set_title("Distance is not the gap: two clicks for everyone")
ax.set_ylim(0, max(med_d.values) + 0.7)
fig.tight_layout(); fig.savefig(CHARTS / "distance_to_philosophy.png"); plt.close(fig)

# 6. Sentence length vs crowd rank (quotability mechanism)
g = df.dropna(subset=["median_sentence_words", "ngram_mean_2000_19"])
fig, ax = plt.subplots(figsize=(9, 5.5))
sent_offsets = {"Immanuel Kant": (-66, -14), "Aristotle": (4, 8),
                "Laozi": (4, 4), "Epictetus": (4, -14)}
for _, r in g.iterrows():
    ax.scatter(r["median_sentence_words"], r["ngram_mean_2000_19"], s=80,
               color=TRAD_COLOR[r["tradition"]], edgecolor="white", zorder=3)
    dx, dy = sent_offsets.get(r["figure"], (4, 3))
    ax.annotate(r["figure"], (r["median_sentence_words"], r["ngram_mean_2000_19"]),
                fontsize=9, xytext=(dx, dy), textcoords="offset points")
ax.set_yscale("log")
ax.set_xlabel("Median sentence length in the author's own text (words)")
ax.set_ylabel("Name frequency in books 2000-2019 (log scale)")
ax.set_title("In print, long sentences win. On screen, they don't.")
fig.tight_layout(); fig.savefig(CHARTS / "sentence_length.png"); plt.close(fig)

# ---------------------------------------------------------------- findings
top_canon_names = df.nsmallest(5, "canon_rank")["figure"].tolist()
top_crowd_names = df.nsmallest(5, "crowd_rank_ngram")["figure"].tolist()
top_pv_names = df.nsmallest(5, "crowd_rank_pv")["figure"].tolist()
canon_wins = df.nsmallest(5, "rank_gap_ngram")   # canon rank << crowd rank
crowd_wins = df.nlargest(5, "rank_gap_ngram")     # crowd rank << canon rank
findings = f"""
CANON VS CROWD — headline numbers
Panel: {len(phil_titles)} philosophers + {len(CONCEPTS)} concept articles; {G.number_of_edges()} in-panel links.
Spearman canon PageRank vs crowd Ngram: rho={corr_all_ng:.2f} (p={p_all_ng:.3g}, n={n_all})
Spearman canon PageRank vs crowd pageviews: rho={corr_all_pv:.2f} (p={p_all_pv:.3g})
  Western only (Ngram): rho={corr_w_ng:.2f} (p={p_w_ng:.3g})
  Eastern only (Ngram): rho={corr_e_ng:.2f} (p={p_e_ng:.3g})
Ngram vs pageviews (two crowd measures agree): rho={corr_ng_pv:.2f} (p={p_ng_pv:.3g})

Top 5 canon (PageRank): {top_canon_names}
Top 5 crowd, books (Ngram 2000-19): {top_crowd_names}
Top 5 crowd, pageviews (median monthly 2023-26): {top_pv_names}

Tradition medians:
{med.to_string()}
Gender medians:
{gender_med.to_string()}

Communities: {len(communities)} (greedy modularity)
{json.dumps(comm_summary, indent=2)}

Philosopher-philosopher edges: cross-tradition {cross}, within Western {within_w}, within Eastern {within_e}
Edge densities: cross-tradition {dens['cross']:.3f}, within Western {dens['within_western']:.3f}, within Eastern {dens['within_eastern']:.3f}
Bridge top 10 (share of East-West shortest paths): {[(DISPLAY.get(k, k), round(v, 3)) for k, v in bridge_top]}
Schopenhauer (the textbook bridge candidate) ranks #{schop_rank} of {len(bridge_ranked)} on bridge score ({schop_score:.3f})
Western figures most linked-to from Eastern articles: {[(DISPLAY.get(k, k), v) for k, v in west_in_from_east[:10]]}

Quotability mechanism (n={n_sent} Gutenberg texts):
  median sentence length vs crowd Ngram: rho={corr_sent_ng:.2f} (p={p_sent_ng:.3g})
  median sentence length vs crowd pageviews: rho={corr_sent_pv:.2f} (p={p_sent_pv:.3g})
  aphorism share (<10 words) vs crowd Ngram: rho={corr_aphor_ng:.2f} (p={p_aphor_ng:.3g})
  aphorism share (<10 words) vs crowd pageviews: rho={corr_aphor_pv:.2f} (p={p_aphor_pv:.3g})
  median sentence length vs canon PageRank: rho={corr_sent_canon:.2f} (p={p_sent_canon:.3g})

Biggest canon wins (central in the field's graph, rarely named in books):
{canon_wins[['figure','tradition','canon_rank','crowd_rank_ngram','rank_gap_ngram']].to_string(index=False)}
Biggest crowd wins (named in books far more than the graph would predict):
{crowd_wins[['figure','tradition','canon_rank','crowd_rank_ngram','rank_gap_ngram']].to_string(index=False)}

Ngram rank movement 1900 -> 2019 (largest rises):
{df.nlargest(8, 'ngram_rank_move')[['figure','tradition','ngram_rank_1900','ngram_rank_2019','ngram_rank_move']].to_string(index=False)}
Largest falls:
{df.nsmallest(8, 'ngram_rank_move')[['figure','tradition','ngram_rank_1900','ngram_rank_2019','ngram_rank_move']].to_string(index=False)}
"""
(ROOT / "findings.txt").write_text(findings.strip() + "\n")
print(findings)
print("saved results.json, findings.txt, 6 charts")
