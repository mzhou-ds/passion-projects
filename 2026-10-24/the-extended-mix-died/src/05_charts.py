#!/usr/bin/env python3
"""
05_charts.py — Charts for the README.

1. dance_hist.png     duration distribution of dance tracks by era (the
                      bimodal radio/club shape flattening)
2. version_spread.png multi-version share + median spread by era,
                      dance vs pop/hip-hop/rock controls
3. intro.png          preview-audio intro metrics by era (t90, head share)
4. shap.png           SHAP bars for both models
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "charts"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
ERA_ORDER = ["1990s", "2000-04", "2005-09", "2010-14", "2015-19", "2020-26"]
COLORS = {"dance": "#7b2ff7", "pop": "#f7a02f", "hiphop": "#2f9ef7", "rock": "#37b24d"}

# ------------------------------------------------------------------ 1: histogram
h = pd.read_csv(ROOT / "data" / "dance_duration_hist.csv")
piv = h.pivot(index="bin", columns="era", values="share").reindex(
    columns=[e for e in ERA_ORDER if e in h["era"].unique()]
)
x = np.arange(len(piv))
fig, ax = plt.subplots(figsize=(9, 4.6))
w = 0.8 / max(len(piv.columns), 1)
for i, era in enumerate(piv.columns):
    ax.bar(x + i * w, piv[era] * 100, width=w, label=era)
ax.set_xticks(x + 0.4 - w / 2)
ax.set_xticklabels(piv.index, rotation=25, ha="left")
ax.set_ylabel("% of dance tracks")
ax.set_title("Dance-track duration distribution by era — the two humps flatten")
ax.legend(title="Release era", ncols=3, frameon=False)
fig.tight_layout()
fig.savefig(CH / "dance_hist.png", dpi=160)
plt.close(fig)

# ------------------------------------------------------------------ 2: versioning
sv = pd.read_csv(ROOT / "data" / "stems_by_era.csv")
sv = sv[sv["era"].isin(ERA_ORDER)]
sv["era"] = pd.Categorical(sv["era"], ERA_ORDER, ordered=True)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharex=True)
for panel, g in sv.groupby("panel"):
    g = g.sort_values("era")
    axes[0].plot(g["era"], g["share_true_versioned"] * 100, marker="o",
                 color=COLORS.get(panel, "gray"), label=panel)
    axes[1].plot(g["era"], g["median_spread_s"], marker="o",
                 color=COLORS.get(panel, "gray"), label=panel)
axes[0].set_ylabel("% of songs with ≥60s between shortest/longest cut")
axes[0].set_title("True versioning (≥60s spread) — a dance-only institution")
axes[1].set_ylabel("Median max−min spread (sec)")
axes[1].set_title("Spread among multi-version songs")
for ax in axes:
    ax.tick_params(axis="x", rotation=30)
    ax.legend(frameon=False)
fig.suptitle("The version ecosystem by song's first-release era", y=1.02)
fig.tight_layout()
fig.savefig(CH / "version_spread.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ 3: intro audio
pf = pd.read_csv(ROOT / "data" / "preview_features.csv")
d = pf[pf["panel_query"] == "dance"]
order = ["pre2010", "2010s", "2020s"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
# left: share of tracks whose opening is spectrally dark (centroid < 1500 Hz)
groups, shares, cols = [], [], []
for coarse in order:
    for bucket, color, lab in [("long", "#7b2ff7", "long"), ("short", "#f76b2f", "short")]:
        sub = d[(d["coarse"] == coarse) & (d["bucket"] == bucket)]["cent_first3"].dropna()
        if len(sub) == 0:
            continue
        groups.append(f"{coarse}\n{lab}")
        shares.append((sub < 1500).mean() * 100)
        cols.append(color)
pop = pf[pf["panel_query"] == "pop"]
for coarse in ["pre2010", "2020s"]:
    sub = pop[pop["coarse"] == coarse]["cent_first3"].dropna()
    groups.append(f"pop\n{coarse}")
    shares.append((sub < 1500).mean() * 100)
    cols.append("#f7a02f")
axes[0].bar(range(len(groups)), shares, color=cols, alpha=0.85)
axes[0].set_xticks(range(len(groups)))
axes[0].set_xticklabels(groups, fontsize=8)
axes[0].set_ylabel("% of tracks opening dark (centroid < 1.5 kHz)")
axes[0].set_title("Dark openings were always a minority sport")
# right: opening brightness distributions, dance long vs short
ax = axes[1]
pos = 0
ticks, labs = [], []
for coarse in order:
    for bucket, color, lab in [("long", "#7b2ff7", "long ≥5:30"), ("short", "#f76b2f", "short ≤3:45")]:
        sub = d[(d["coarse"] == coarse) & (d["bucket"] == bucket)]["cent_first3"].dropna()
        if len(sub) == 0:
            continue
        pos += 1
        ax.boxplot(sub, positions=[pos], patch_artist=True,
                   boxprops=dict(alpha=0.4, color=color),
                   medianprops=dict(color=color, linewidth=2))
        ticks.append(pos)
        labs.append(f"{coarse}\n{lab}")
ax.set_xticks(ticks)
ax.set_xticklabels(labs, fontsize=8)
ax.set_ylabel("Spectral centroid of first 3s (Hz)")
ax.set_title("How bright frame one already is")
fig.suptitle("The intro, measured spectrally: dance previews by era and length", y=1.02)
fig.tight_layout()
fig.savefig(CH / "intro.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ 4: SHAP
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, fname, title in [
    (axes[0], "shap_audio_era.csv", "Dating a dance track from audio alone"),
    (axes[1], "shap_long_cut.csv", "Predicting a ≥5:30 long cut (all panels)"),
]:
    t = pd.read_csv(ROOT / "data" / fname).head(8).iloc[::-1]
    ax.barh(t["feature"], t["mean_abs_shap"], color="#7b2ff7", alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel("Mean |SHAP|")
fig.tight_layout()
fig.savefig(CH / "shap.png", dpi=160)
plt.close(fig)

print("charts written:", sorted(p.name for p in CH.glob("*.png")))
