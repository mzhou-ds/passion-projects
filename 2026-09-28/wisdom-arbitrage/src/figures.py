"""Figures for the wisdom-arbitrage build. Run after analyze.py."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")
FIG = os.path.join(PROJ, "figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

GROUP_COLORS = {"canon": "#2a6f6f", "philosophy": "#b07a2a", "selfhelp": "#a03a3a"}
GROUP_LABELS = {"canon": "Ancient canon", "philosophy": "Transcendentalists", "selfhelp": "Self-help classics"}

# ---- fig1: UMAP map of the wisdom corpus ----
z = np.load(os.path.join(DATA, "umap2d.npz"))["xy"]
df = pd.read_csv(os.path.join(DATA, "corpus.csv"))
fig, ax = plt.subplots(figsize=(10, 7))
for g, sub in df.groupby("group"):
    idx = sub.index.to_numpy()
    ax.scatter(z[idx, 0], z[idx, 1], s=6, alpha=0.45, c=GROUP_COLORS[g], label=GROUP_LABELS[g], rasterized=True)
ax.legend(markerscale=4, frameon=False, loc="best")
ax.set_title(f"{len(df):,} passages of wisdom, mapped by meaning", fontsize=14, pad=12)
ax.set_xlabel("UMAP 1"); ax.set_ylabel("UMAP 2")
ax.text(0.01, 0.01, "Each dot = one passage. Distance = semantic similarity (MiniLM embeddings).",
        transform=ax.transAxes, fontsize=9, color="#555")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_umap.png"), dpi=150)
print("fig1 done")

# ---- fig2: repackaging index ----
res = json.load(open(os.path.join(DATA, "results.json")))
rep = res["repackaging"]
order = ["smiles-self-help", "barnum-money", "allen-thinketh", "wattles-rich", "conwell-acres"]
labels = [f"{rep[b]['title']}\n({rep[b]['year']})" for b in order]
par = [rep[b]["paraphrase_rate_060"] * 100 for b in order]
dup = [rep[b]["quotation_rate_070"] * 100 for b in order]
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(order))
ax.bar(x, par, color="#a03a3a", alpha=0.85, label="Paraphrase (sim ≥ 0.60)")
ax.bar(x, dup, color="#5a1f1f", alpha=0.95, label="Near-duplicate / quotation (sim ≥ 0.70)")
for i, v in enumerate(par):
    ax.text(i, v + 0.4, f"{v:.0f}%", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylabel("% of the book's passages")
ax.set_title("The repackaging index: how much of each self-help classic\nis a paraphrase of something written 2,000+ years earlier", fontsize=13, pad=12)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_repackaging.png"), dpi=150)
print("fig2 done")

# ---- fig3: cluster composition — universal vs whitespace vs industry ----
clusters = json.load(open(os.path.join(DATA, "clusters.json")))
sel = []
for c in clusters:
    g = c["groups"]
    tot = sum(g.values())
    sel.append({"label": ", ".join(c["top_terms"][:4]), "size": c["size"],
                "canon": g.get("canon", 0) / tot, "phil": g.get("philosophy", 0) / tot,
                "self": g.get("selfhelp", 0) / tot,
                "kind": ("whitespace" if c["canon_share"] >= 0.65 and c["selfhelp_share"] <= 0.05
                         else "industry" if c["selfhelp_share"] >= 0.65
                         else "universal" if c["n_traditions"] >= 6 else "mixed")})
sel = [s for s in sel if s["kind"] in ("whitespace", "industry", "universal") and s["size"] >= 60]
sel.sort(key=lambda s: ({"whitespace": 0, "universal": 1, "industry": 2}[s["kind"]], -s["size"]))
fig, ax = plt.subplots(figsize=(10, max(4, 0.42 * len(sel))))
y = np.arange(len(sel))
ax.barh(y, [s["canon"] for s in sel], color="#2a6f6f", label="Ancient canon")
ax.barh(y, [s["phil"] for s in sel], left=[s["canon"] for s in sel], color="#b07a2a", label="Transcendentalists")
ax.barh(y, [s["self"] for s in sel],
        left=[s["canon"] + s["phil"] for s in sel], color="#a03a3a", label="Self-help")
ax.set_yticks(y); ax.set_yticklabels([s["label"] for s in sel], fontsize=9)
kinds = {"whitespace": "WHITE SPACE", "universal": "UNIVERSAL", "industry": "INDUSTRY-ONLY"}
for i, s in enumerate(sel):
    ax.text(1.01, i, kinds[s["kind"]], va="center", fontsize=8, color="#555")
ax.set_xlim(0, 1.22); ax.set_xlabel("share of cluster")
ax.set_title("What the canon and the industry each talk about", fontsize=13, pad=12)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, -0.04), ncol=3)
fig.subplots_adjust(bottom=0.10)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_clusters.png"), dpi=150)
print("fig3 done")
