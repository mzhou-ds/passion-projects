#!/usr/bin/env python3
"""Charts for build #68."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(BASE, "charts")
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})

# ---------------------------------------------------------------- fig 1: quotation
# sentences carrying a verbatim 6-word run (genuine quotations after audit:
# Vishnu 8 raw sentences -> 2 genuine quoted sentences; Upanishads/Analects hits are generic phrases)
labels = ["Walden", "Emerson\nEssays I", "Emerson\nNature"]
kjv = [18, 17, 6]
east_real = [2, 0, 0]     # genuine Eastern quotations (both Vishnu Purana, Walden)
gita = [0, 0, 0]
x = np.arange(len(labels)); w = 0.24
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.bar(x - w, kjv, w, label="King James Bible", color="#3b5b7a")
ax.bar(x, east_real, w, label="Eastern scripture (genuine quotes)", color="#b3541e")
ax.bar(x + w, gita, w, label="Bhagavad Gita (Arnold)", color="#8a8a8a")
for i, v in enumerate(kjv):
    ax.text(i - w, v + 0.5, str(v), ha="center", fontsize=11, fontweight="bold")
for i, v in enumerate(east_real):
    if v: ax.text(i, v + 0.5, str(v), ha="center", fontsize=11, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("Sentences carrying a verbatim 6-word run")
ax.set_title("Who gets quoted? The Bible, 41 sentences. The Gita, none.", fontsize=13, pad=12)
ax.legend(frameon=False, fontsize=10, loc="upper right")
ax.set_ylim(0, 21)
fig.tight_layout(); fig.savefig(os.path.join(CH, "fig1_quotation.png"), dpi=160); plt.close(fig)

# ---------------------------------------------------------------- fig 2: mentions
mentions = json.load(open(os.path.join(BASE, "data", "mentions.json")))
fig, ax = plt.subplots(figsize=(8.2, 4.6))
names = ["Walden", "Emerson Essays I", "Emerson Nature"]
east = [10000 * mentions[t]["east_total"] / mentions[t]["words"] for t in
        ["walden", "emerson_essays1", "emerson_nature"]]
west = [10000 * mentions[t]["west_total"] / mentions[t]["words"] for t in
        ["walden", "emerson_essays1", "emerson_nature"]]
x = np.arange(3); w = 0.34
b1 = ax.bar(x - w / 2, east, w, label="Eastern names (Gita, Veda, Brahma, Confucius...)", color="#b3541e")
b2 = ax.bar(x + w / 2, west, w, label="Western names (Bible, Jesus, Christ, church...)", color="#3b5b7a")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.12, f"{b.get_height():.2f}",
            ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(names)
ax.set_ylabel("Named mentions per 10,000 words")
ax.set_title("Who gets named? Thoreau: a dead heat. Emerson: the West, 8 to 1.", fontsize=13, pad=12)
ax.legend(frameon=False, fontsize=10, loc="upper right")
ax.set_ylim(0, 5.8)
fig.tight_layout(); fig.savefig(os.path.join(CH, "fig2_mentions.png"), dpi=160); plt.close(fig)

# ---------------------------------------------------------------- fig 3: Walden chapters TF-IDF
tfidf = json.load(open(os.path.join(BASE, "data", "walden_tfidf.json")))
# NOTE: walden_tfidf.json came from the untruncated run; values are chapter-level and stable.
chapters = [d["chapter"] for d in tfidf]
g = [d["gita_arnold"] for d in tfidf]
k = [d["kjv"] for d in tfidf]
s = [d["sartor"] for d in tfidf]
short = [c.replace("Where I Lived, and What I Lived For", "Where I Lived")
         .replace("Former Inhabitants; and Winter Visitors", "Former Inhabitants")
         for c in chapters]
fig, ax = plt.subplots(figsize=(9.4, 5.2))
x = np.arange(len(chapters)); w = 0.26
ax.bar(x - w, g, w, label="Bhagavad Gita", color="#b3541e")
ax.bar(x, k, w, label="King James Bible", color="#3b5b7a")
ax.bar(x + w, s, w, label="Carlyle, Sartor Resartus", color="#6a8f6a")
ax.set_xticks(x); ax.set_xticklabels(short, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("TF-IDF cosine similarity (chapter vs whole book)")
ax.set_title("Every Walden chapter leans Gita over Bible — and Carlyle over both",
             fontsize=13, pad=12)
ax.legend(frameon=False, fontsize=10, loc="upper right")
fig.tight_layout(); fig.savefig(os.path.join(CH, "fig3_chapters_tfidf.png"), dpi=160); plt.close(fig)

# ---------------------------------------------------------------- fig 4: Emerson essays fingerprint
res = json.load(open(os.path.join(BASE, "data", "results.json")))
em = res["emerson_essay_fingerprints"]
essays = list(em.keys())
gv = [em[e]["gita_arnold"] for e in essays]
kv = [em[e]["kjv"] for e in essays]
sv = [em[e]["sartor"] for e in essays]
fig, ax = plt.subplots(figsize=(9.0, 5.0))
x = np.arange(len(essays)); w = 0.26
ax.bar(x - w, gv, w, label="Gita fingerprint", color="#b3541e")
ax.bar(x, kv, w, label="Bible fingerprint", color="#3b5b7a")
ax.bar(x + w, sv, w, label="Sartor fingerprint", color="#6a8f6a")
ax.set_xticks(x); ax.set_xticklabels(essays, rotation=40, ha="right", fontsize=9)
ax.set_ylabel("% of words in source's 150 most distinctive words")
ax.set_title("Emerson's essays: Gita vocabulary beats Bible vocabulary in all 12",
             fontsize=13, pad=12)
ax.legend(frameon=False, fontsize=10, loc="upper right")
fig.tight_layout(); fig.savefig(os.path.join(CH, "fig4_emerson_fingerprint.png"), dpi=160); plt.close(fig)

print("charts done:", sorted(os.listdir(CH)))
