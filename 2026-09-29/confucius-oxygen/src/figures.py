"""Final figures. Reads data/shelf_test.json + data/adjudication.json + data/modern.tsv."""
import csv, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")
FIG = os.path.join(PROJ, "figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({"font.size": 11, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False})
CHANCE = 248.0

shelf = json.load(open(os.path.join(DATA, "shelf_test.json")))
adj = {v["id"]: v for v in json.load(open(os.path.join(DATA, "adjudication.json")))["verdicts"]}
modern = {r["id"]: r for r in csv.DictReader(open(os.path.join(DATA, "modern.tsv")), delimiter="\t")}
order_ids = [r["id"] for r in csv.DictReader(open(os.path.join(DATA, "modern.tsv")), delimiter="\t")]

# ---- fig1: enrichment test ----
fig, ax = plt.subplots(figsize=(10, 8.6))
items = [s for s in shelf]
ranks = np.array([s["mean_rank_lead"] for s in items])
ps = np.array([s["p"] for s in items])
sig = ps < 0.05
o = np.argsort(ranks)
y = np.arange(len(items))
cols = np.where(sig[o], "#1b7a3d", "#b9b9b9")
ax.barh(y, ranks[o], color=cols, height=0.62)
ax.set_yticks(y)
import textwrap as _tw
ax.set_yticklabels(["%s: %s" % (s["id"], _tw.fill(modern[s["id"]]["label"], 38)) for s in np.array(items)[o]], fontsize=8.5)
ax.axvline(CHANCE, color="#333", ls="--", lw=1.2)
ax.text(CHANCE + 4, len(items) - 1, "chance (248)", fontsize=9, color="#333", va="center")
ax.set_xlabel("mean rank of Confucius's 66 management passages among all 495 Analects passages\n(lower = semantically closer to modern management language)")
ax.set_title("Do modern management ideas live near Confucius's management passages?", loc="left", fontsize=13, fontweight="bold")
ax.text(0.98, 0.02, "green = significant at p<0.05 (permutation test, 2000 reps)\nMiniLM embeddings; all 8 Oxygen behaviors significant; 4/12 Q12 items",
        transform=ax.transAxes, fontsize=8.5, color="#555", va="bottom", ha="right")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_enrichment.png"), bbox_inches="tight"); plt.close(fig)

# ---- fig2: hand-adjudicated coverage ----
VCOL = {"strong": "#1b7a3d", "moderate": "#7bc47f", "weak": "#e8a020", "absent": "#b03a2e"}
VORD = {"strong": 3, "moderate": 2, "weak": 1, "absent": 0}
def panel(ids, title, fname):
    vs = [adj[i]["verdict"] for i in ids]
    labels = [modern[i]["label"] for i in ids]
    o2 = np.argsort([VORD[v] for v in vs])[::-1]
    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.55 * len(ids))))
    y = np.arange(len(ids))
    ax.barh(y, [VORD[vs[i]] + 1 for i in o2], color=[VCOL[vs[i]] for i in o2], height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[i] for i in o2], fontsize=10)
    ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["absent", "weak", "moderate", "strong"])
    ax.set_xlim(0.5, 4.6)
    for i, k in enumerate(o2):
        v = vs[k]
        n = len(adj[ids[k]]["passages"])
        tag = v if v == "absent" else "%s (%d passage%s)" % (v, n, "s" if n > 1 else "")
        ax.text(VORD[v] + 1.12, i, tag, va="center", fontsize=9, color="#444")
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), bbox_inches="tight"); plt.close(fig)

oxy = [i for i in order_ids if i.startswith("oxy")]
q12 = [i for i in order_ids if i.startswith("q")]
panel(oxy, "Project Oxygen's 8 behaviors: did Confucius get there first? (human-verified)",
      "fig2a_oxygen_coverage.png")
panel(q12, "Gallup Q12: did Confucius get there first? (human-verified)",
      "fig2b_q12_coverage.png")

# ---- fig3: verdict counts by shelf ----
fig, ax = plt.subplots(figsize=(8, 4.2))
cats = ["strong", "moderate", "weak", "absent"]
oxy_c = [sum(1 for i in oxy if adj[i]["verdict"] == c) for c in cats]
q_c = [sum(1 for i in q12 if adj[i]["verdict"] == c) for c in cats]
x = np.arange(2); w = 0.18
for k, c in enumerate(cats):
    ax.bar(x + k * w - 1.5 * w, [oxy_c[k], q_c[k]], width=w, color=VCOL[c], label=c)
ax.set_xticks(x); ax.set_xticklabels(["Project Oxygen\n(8 behaviors)", "Gallup Q12\n(12 items)"])
ax.set_ylabel("number of items")
ax.set_title("The rediscovery index: 7/8 Oxygen, 6/12 Q12", loc="left", fontsize=13, fontweight="bold")
ax.legend(frameon=False, fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_rediscovery_index.png"), bbox_inches="tight"); plt.close(fig)
print("figures written:", sorted(os.listdir(FIG)))
