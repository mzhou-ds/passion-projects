"""Charts for 'Your Genre Tag Is Your Ceiling' — reads data/*.csv|json only."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CH = os.path.join(HERE, "..", "charts")
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})

G = pd.read_csv(os.path.join(DATA, "genre_stats.csv"))
T = pd.read_csv(os.path.join(DATA, "tracks.csv"))
F = json.load(open(os.path.join(DATA, "findings.json")))
M = json.load(open(os.path.join(DATA, "model.json")))

# 1 — shelf ceilings: conversion of each genre chart into the overall Top 100
g = G.sort_values("main_rate")
fig, ax = plt.subplots(figsize=(8.5, 6))
colors = ["#c0392b" if v <= 0.01 else "#e67e22" if v <= 0.09 else "#2471a3"
          for v in g.main_rate]
ax.barh(g.genre, g.main_rate * 100, color=colors)
for _, r in g.iterrows():
    ax.text(r.main_rate * 100 + 0.6, r.genre,
            f"{int(r.in_main)} of 100", va="center", fontsize=9)
ax.set_xlabel("Tracks from this genre chart that also sit in the overall Top 100 (%)")
ax.set_title("The shelf ceiling: same chart size, wildly different exits\n"
             "Beatport overall Top 100 by source genre, 2026-10-15", loc="left")
ax.set_xlim(0, 36)
fig.tight_layout(); fig.savefig(f"{CH}/shelf_ceiling.png", dpi=150); plt.close(fig)

# 2 — freshness economies: median release age by genre
g2 = G.sort_values("median_age_days")
fig, ax = plt.subplots(figsize=(8.5, 6))
ax.barh(g2.genre, g2.median_age_days, color="#2471a3")
for _, r in g2.iterrows():
    ax.text(r.median_age_days + 6, r.genre,
            f"median {int(r.median_age_days)}d · {r.share_gt_365d*100:.0f}% over a year old",
            va="center", fontsize=9)
ax.set_xlabel("Median age of a charting track (days since release)")
ax.set_title("Some shelves sell this month's records. Some sell last year's.\n"
             "Release-age profile by genre chart", loc="left")
ax.set_xlim(0, 440)
fig.tight_layout(); fig.savefig(f"{CH}/freshness.png", dpi=150); plt.close(fig)

# 3 — artist bridges: shared-artist counts between genre pairs (matrix)
ae = pd.read_csv(os.path.join(DATA, "appearances.csv"))
tt = T[["track_id", "genre_slug", "artists"]]
ae = ae[ae.chart != "main"].merge(tt, on="track_id")
ae["artist"] = ae.artists.str.split("; ")
ae = ae.explode("artist")
genres = sorted(G.genre_slug)
ag = ae.groupby("artist").genre_slug.apply(lambda s: sorted(set(s)))
mat = pd.DataFrame(0, index=genres, columns=genres)
for gs in ag:
    for a in gs:
        for b in gs:
            if a != b:
                mat.loc[a, b] += 1
fig, ax = plt.subplots(figsize=(9, 7.5))
im = ax.imshow(mat.values, cmap="Blues")
ax.set_xticks(range(len(genres)), genres, fontsize=7, rotation=45, ha="left")
ax.set_yticks(range(len(genres)), genres, fontsize=8)
for i in range(len(genres)):
    for j in range(len(genres)):
        v = mat.values[i, j]
        if v >= 8:
            ax.text(j, i, v, ha="center", va="center", fontsize=7,
                    color="white" if v > 14 else "black")
ax.set_title("Tracks never cross shelves. Artists do.\n"
             "Number of charting artists appearing in both genres", loc="left")
fig.colorbar(im, shrink=0.8)
fig.tight_layout(); fig.savefig(f"{CH}/artist_bridges.png", dpi=150); plt.close(fig)

# 4 — main-chart composition vs equal shares
comp = pd.Series(F["main_chart"]["composition"]).reindex(genres).fillna(0)
fig, ax = plt.subplots(figsize=(8.5, 6))
y = np.arange(len(genres))
ax.barh(y, comp.values, color="#2471a3", label="Actual tracks in overall Top 100")
ax.plot([100 / 17] * 2, [-0.6, len(genres) - 0.4], color="#c0392b", lw=2,
        label="Equal share across 17 genres (5.9)")
ax.set_yticks(y, [G.set_index("genre_slug").genre.get(s, s) for s in genres])
ax.set_xlabel("Tracks in the overall Top 100")
ax.set_title("The 'overall' chart is a house chart with guests", loc="left")
ax.legend(frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(f"{CH}/main_composition.png", dpi=150); plt.close(fig)

# 5 — SHAP importances for the full model
imp = pd.read_csv(os.path.join(DATA, "shap_importance.csv"),
                  index_col=0)["mean_abs_shap"].head(10)[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.barh(imp.index, imp.values, color="#2471a3")
ax.set_xlabel("Mean |SHAP| — contribution to predicted Top-100 entry")
ax.set_title(f"What actually predicts crossing over (full model AUC "
             f"{M['full_auc']:.2f}; track features alone {M['track_only_auc']:.2f})",
             loc="left")
fig.tight_layout(); fig.savefig(f"{CH}/shap.png", dpi=150); plt.close(fig)

print("charts written:", sorted(os.listdir(CH)))
