"""Charts for The Wisdom Books Are Bossy."""
import json, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0, "src")
import analyze as az

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#666666", "axes.labelcolor": "#222222",
    "xtick.color": "#444444", "ytick.color": "#222222",
    "figure.facecolor": "white", "axes.facecolor": "white",
})
EAST, WEST = "#2E7D6B", "#C07A2A"
rows = json.load(open("data/processed/analysis_results.json"))
detail = json.load(open("data/processed/detail.json"))

# ---- fig 1: imperative share, sorted -------------------------------------
order = sorted(rows, key=lambda r: r["imperative_share"])
fig, ax = plt.subplots(figsize=(9, 6.2))
colors = [EAST if r["tradition"] == "East" else WEST for r in order]
ax.barh([r["title"] for r in order], [r["imperative_share"] for r in order], color=colors, height=0.62)
for i, r in enumerate(order):
    ax.text(r["imperative_share"] + 0.25, i, f"{r['imperative_share']:.1f}%", va="center", fontsize=10.5)
ax.set_xlim(0, 13)
ax.set_xlabel("Share of sentences that are commands (%)")
ax.set_title("How bossy is each wisdom book?", fontsize=13, loc="left", pad=12)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=EAST, label="East"), Patch(color=WEST, label="West")],
          loc="lower right", frameon=False)
fig.tight_layout(); fig.savefig("charts/fig1_imperative.png", dpi=150); plt.close(fig)

# ---- fig 2: wisdom map: negation vs imperative ----------------------------
fig, ax = plt.subplots(figsize=(9, 6.2))
for r in rows:
    c = EAST if r["tradition"] == "East" else WEST
    ax.scatter(r["negation_per_1000"], r["imperative_share"], s=110, color=c,
               edgecolor="white", linewidth=1.2, zorder=3)
    ax.annotate(r["title"], (r["negation_per_1000"], r["imperative_share"]),
                textcoords="offset points", xytext=(7, 5), fontsize=9.5)
ax.set_xlabel("Negations per 1,000 words  (not / no / never / without / nothing ...)")
ax.set_ylabel("Commands (% of sentences)")
ax.set_title("The wisdom map: negation vs command", fontsize=13, loc="left", pad=12)
ax.legend(handles=[Patch(color=EAST, label="East"), Patch(color=WEST, label="West")],
          loc="upper right", frameon=False)
fig.tight_layout(); fig.savefig("charts/fig2_wisdom_map.png", dpi=150); plt.close(fig)

# ---- fig 3: who is being told? second person vs imperative ----------------
fig, ax = plt.subplots(figsize=(9, 6.2))
OFFSETS3 = {"Tao Te Ching": (-8, -14), "Walden": (4, -15), "Analects": (8, -14),
            "Upanishads": (-52, 6), "Dhammapada": (8, 6), "Zhuangzi": (8, -4),
            "Emerson, Essays I": (8, 2)}
for r in rows:
    c = EAST if r["tradition"] == "East" else WEST
    ax.scatter(r["second_person_per_1000"], r["imperative_share"], s=110, color=c,
               edgecolor="white", linewidth=1.2, zorder=3)
    ax.annotate(r["title"], (r["second_person_per_1000"], r["imperative_share"]),
                textcoords="offset points", xytext=OFFSETS3.get(r["title"], (7, 5)), fontsize=9.5)
ax.set_xlabel("Second-person words per 1,000 words  (you / your / thou / thy ...)")
ax.set_ylabel("Commands (% of sentences)")
ax.set_title("Commands go to someone: the more 'you', the more orders", fontsize=13, loc="left", pad=12)
ax.legend(handles=[Patch(color=EAST, label="East"), Patch(color=WEST, label="West")],
          loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig("charts/fig3_address.png", dpi=150); plt.close(fig)

# ---- fig 4: what each text's commands are made of -------------------------
def composition(fname):
    txt = open(f"data/processed/clean/{fname}", encoding="utf-8").read()
    imps = [s for s in az.split_sentences(txt) if az.is_imperative(s)]
    let = sum(1 for s in imps if s.strip().lower().lstrip("\"'“‘([ ").startswith("let"))
    neg = sum(1 for s in imps if not s.strip().lower().lstrip("\"'“‘([ ").startswith("let")
              and re.search(r"\b(not|never|no|nor)\b", s.lower()))
    direct = len(imps) - let - neg
    return let, neg, direct

order2 = sorted(rows, key=lambda r: r["imperative_share"], reverse=True)
fig, ax = plt.subplots(figsize=(9, 6.2))
y = np.arange(len(order2))
lets, negs, directs = [], [], []
for r in order2:
    l, n, d = composition(r["file"])
    tot = max(1, l + n + d)
    lets.append(100*l/tot); negs.append(100*n/tot); directs.append(100*d/tot)
ax.barh(y, lets, color="#7FB069", height=0.62, label="'Let ...' (permission)")
ax.barh(y, negs, left=lets, color="#C0392B", height=0.62, label="Prohibitions (not / never)")
ax.barh(y, directs, left=np.array(lets)+np.array(negs), color="#5B7FA6", height=0.62, label="Direct orders")
ax.set_yticks(y); ax.set_yticklabels([r["title"] for r in order2])
ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_xlabel("Share of that book's commands (%)")
ax.set_title("What each book's commands are made of", fontsize=13, loc="left", pad=12)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False, fontsize=10)
fig.tight_layout(); fig.savefig("charts/fig4_composition.png", dpi=150); plt.close(fig)
print("charts written")
