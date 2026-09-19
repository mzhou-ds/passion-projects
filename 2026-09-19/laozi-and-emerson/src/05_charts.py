"""Charts for Laozi-and-Emerson.

fig1_umap.png      - UMAP map of all sentences, colored by tradition
fig2_kinship.png   - % of each work's sentences whose nearest neighbor is
                     from the other tradition ("kinship index")
fig3_crosssim.png  - 4x4 mean cross-work cosine similarity heatmap
fig4_affinity.png  - which Emerson essay is most Taoist / which Walden
                     chapter most Buddhist
fig5_themes.png    - shared theme clusters: size + tradition mix, labeled
                     by top terms
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False})
EAST_C, WEST_C = "#2f6f9f", "#c26a2b"
WORK_C = {"Tao Te Ching": "#1f5f8b", "Dhammapada": "#5aa9c9",
          "Essays, First Series": "#c26a2b", "Walden": "#e0a458"}


def fig1_umap(df):
    fig, ax = plt.subplots(figsize=(9, 7))
    for trad, c in [("East", EAST_C), ("West", WEST_C)]:
        g = df[df["tradition"] == trad]
        ax.scatter(g["umap_x"], g["umap_y"], s=6, alpha=0.45, c=c, label=trad,
                   rasterized=True)
    ax.legend(frameon=False, fontsize=12)
    ax.set_title("Every sentence of Laozi, the Buddha, Emerson, and Thoreau,\n"
                 "mapped by meaning (UMAP of sentence embeddings)", fontsize=13)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(FIG / "fig1_umap.png", dpi=150); plt.close(fig)


def fig2_kinship(results):
    kin = results["kinship"]
    works = list(kin.keys())
    vals = [kin[w]["pct_nn_other_tradition"] for w in works]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.barh(works, vals, color=[WORK_C[w] for w in works], height=0.55)
    ax.bar_label(bars, fmt="%.1f%%")
    ax.set_xlim(0, max(vals) * 1.25)
    ax.set_xlabel("% of sentences whose nearest neighbor is from the other tradition")
    ax.set_title("The kinship index: how often a sentence's closest match\n"
                 "comes from the other side of the world", fontsize=13)
    fig.tight_layout(); fig.savefig(FIG / "fig2_kinship.png", dpi=150); plt.close(fig)


def fig3_crosssim(df, emb):
    works = ["Tao Te Ching", "Dhammapada", "Essays, First Series", "Walden"]
    idx = {w: df.index[df["work"] == w].to_numpy() for w in works}
    M = np.zeros((4, 4))
    for a, wa in enumerate(works):
        for b, wb in enumerate(works):
            M[a, b] = (emb[idx[wa]] @ emb[idx[wb]].T).mean()
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(M, cmap="YlGnBu", vmin=M.min(), vmax=M.max())
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    short = ["Tao Te Ching", "Dhammapada", "Emerson", "Thoreau"]
    ax.set_xticklabels(short, rotation=25, ha="right")
    ax.set_yticklabels(short)
    for a in range(4):
        for b in range(4):
            ax.text(b, a, f"{M[a, b]:.3f}", ha="center", va="center",
                    color="white" if M[a, b] > M.mean() else "black", fontsize=11)
    ax.set_title("Mean sentence-to-sentence similarity between works", fontsize=13)
    fig.colorbar(im, ax=ax, shrink=0.8, label="mean cosine similarity")
    fig.tight_layout(); fig.savefig(FIG / "fig3_crosssim.png", dpi=150); plt.close(fig)


def fig4_affinity():
    aff = pd.read_csv(DATA / "section_affinity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=False)
    em = aff[aff["work"] == "Essays, First Series"].sort_values("tao_affinity")
    wa = aff[aff["work"] == "Walden"].sort_values("dhammapada_affinity")
    axes[0].barh(em["section"], em["tao_affinity"], color="#c26a2b", height=0.6)
    axes[0].set_title("Most Taoist Emerson essays", fontsize=12)
    axes[0].set_xlabel("mean cosine similarity to Tao sentences")
    axes[1].barh(wa["section"], wa["dhammapada_affinity"], color="#2f6f9f", height=0.6)
    axes[1].set_title("Most Buddhist Walden chapters", fontsize=12)
    axes[1].set_xlabel("mean cosine similarity to Dhammapada verses")
    for ax in axes:
        ax.tick_params(labelsize=10)
    fig.tight_layout(); fig.savefig(FIG / "fig4_affinity.png", dpi=150); plt.close(fig)


def fig5_themes(results):
    shared = [c for c in results["clusters"] if c["shared"]]
    shared = sorted(shared, key=lambda c: -c["size"])[:12]
    labels = ["\n".join([", ".join(c["top_terms"][:4])]) for c in shared]
    east = [c["east_share"] * c["size"] for c in shared]
    west = [c["west_share"] * c["size"] for c in shared]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    y = np.arange(len(shared))
    ax.barh(y, east, color=EAST_C, height=0.6, label="East (Tao / Dhammapada)")
    ax.barh(y, west, left=east, color=WEST_C, height=0.6, label="West (Emerson / Thoreau)")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlabel("sentences in cluster")
    ax.set_title("Shared themes: topic clusters where both traditions show up\n"
                 "(KMeans over sentence embeddings; ≥15% of each tradition)", fontsize=13)
    fig.tight_layout(); fig.savefig(FIG / "fig5_themes.png", dpi=150); plt.close(fig)


def main():
    df = pd.read_csv(DATA / "units.csv")
    cl = pd.read_csv(DATA / "clusters.csv")
    df = df.merge(cl, on="unit_id")
    z = np.load(DATA / "embeddings.npz")
    emb = z["embeddings"].astype(np.float64)
    results = json.loads((DATA / "results.json").read_text())
    fig1_umap(df); fig2_kinship(results); fig3_crosssim(df, emb)
    fig4_affinity(); fig5_themes(results)
    print("wrote figures/")


if __name__ == "__main__":
    main()
