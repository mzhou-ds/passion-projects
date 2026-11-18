"""Charts for The Ghost Job Market. All figures read from data/ (no re-fetching)."""
import json, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.join(os.path.dirname(__file__), "..")
CH = os.path.join(BASE, "charts")
df = pd.read_csv(os.path.join(BASE, "data", "jobs_classified.csv"))
ct = pd.read_csv(os.path.join(BASE, "data", "company_table.csv"), index_col=0)
S = json.load(open(os.path.join(BASE, "data", "summary.json")))

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "axes.edgecolor": "#666666",
    "axes.labelcolor": "#222222", "xtick.color": "#444444", "ytick.color": "#222222",
    "figure.facecolor": "white", "axes.facecolor": "white",
})
TEAL, RUST, SLATE, GOLD = "#1f7a6d", "#c0563a", "#4a5a6a", "#b98a1d"
GREY = "#9aa5ad"

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), dpi=170)
    plt.close(fig)
    print("saved", name)

# 1. What the market is actually hiring for
fs = pd.Series(S["function_share"]).sort_values()
fig, ax = plt.subplots(figsize=(8.5, 5.2))
colors = [RUST if f in ("Sales / BD",) else TEAL if f == "Engineering" else SLATE for f in fs.index]
ax.barh(fs.index, fs.values, color=colors, height=0.62)
for i, (f, v) in enumerate(fs.items()):
    n = int(round(v / 100 * S["n_postings"]))
    ax.text(v + 0.6, i, f"{v:.1f}%  (n={n:,})", va="center", fontsize=10.5)
ax.set_xlim(0, 44)
ax.set_xlabel("Share of all 8,371 open postings (%)")
ax.set_title("What the posted tech market is hiring for, Nov 18 2026", fontsize=13, loc="left", pad=12)
save(fig, "01_function_mix.png")

# 2. The ghost index: share of postings open >90 days, by company
g = ct.sort_values("ghost")
fig, ax = plt.subplots(figsize=(8.5, 6.4))
ax.barh(g.index, g["ghost"], color=[RUST if v >= 50 else TEAL if v < 25 else GOLD for v in g["ghost"]], height=0.62)
ax.axvline(31.0, color="#222222", ls="--", lw=1.2)
ax.text(31.4, len(g) - 0.4, "all boards: 31.0%", fontsize=10, va="center")
for i, (c, v) in enumerate(zip(g.index, g["ghost"])):
    ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9.5)
ax.set_xlim(0, 66)
ax.set_xlabel("Share of postings open more than 90 days (%)")
ax.set_title("The ghost index: half of Databricks' and Scale AI's boards is stale", fontsize=13, loc="left", pad=12)
save(fig, "02_ghost_index.png")

# 3. Age distribution of postings
buckets = ["<30d", "30-90d", "91-180d", ">180d"]
vals = [S["age_buckets"][b] for b in buckets]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
bars = ax.bar(buckets, vals, color=[TEAL, TEAL, RUST, RUST], width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=11)
ax.set_ylim(0, 42)
ax.set_ylabel("Share of postings (%)")
ax.set_title("Posting age: 31% of the market has been open 90+ days (median: 50 days)", fontsize=13, loc="left", pad=12)
save(fig, "03_age_buckets.png")

# 4. Remote is bimodal: company remote share
r = ct.sort_values("remote")
fig, ax = plt.subplots(figsize=(8.5, 6.4))
ax.barh(r.index, r["remote"], color=[TEAL if v > 80 else RUST if v < 5 else GOLD for v in r["remote"]], height=0.62)
ax.axvline(19.5, color="#222222", ls="--", lw=1.2)
ax.text(20.2, len(r) - 0.4, "all boards: 19.5%", fontsize=10, va="center")
for i, (c, v) in enumerate(zip(r.index, r["remote"])):
    ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9.5)
ax.set_xlim(0, 112)
ax.set_xlabel("Share of postings listed as remote (%)")
ax.set_title("Remote didn't die. It consolidated: 8 boards are 82-100% remote,\n18 are under 5%", fontsize=13, loc="left", pad=12)
save(fig, "04_remote_bimodal.png")

# 5. The seniority ladder: almost no bottom rung
sen = pd.Series(S["seniority_share"])
order = ["Intern", "New grad", "Junior", "Mid / unmarked", "Senior", "Staff", "Principal+"]
sen = sen.reindex(order)
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(sen.index, sen.values, color=[RUST if s in ("Junior", "New grad", "Intern") else TEAL for s in sen.index], width=0.6)
for i, v in enumerate(sen.values):
    ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=11)
ax.set_ylim(0, 66)
ax.set_ylabel("Share of postings (%)")
ax.set_title("The ladder's bottom rung is gone: junior + new-grad + intern = 4.8%", fontsize=13, loc="left", pad=12)
save(fig, "05_seniority_ladder.png")

# 6. AI roles: strict (title/dept) vs broad (description mentions AI work)
top_ai = ct.sort_values("ai", ascending=False).head(10)
broad = {}
for c in top_ai.index:
    broad[c] = round(df[df.company == c]["is_ai_broad"].mean() * 100, 1)
fig, ax = plt.subplots(figsize=(8.5, 5.4))
y = np.arange(len(top_ai))
ax.barh(y + 0.2, top_ai["ai"].values, height=0.4, color=TEAL, label="AI-titled role (title/dept)")
ax.barh(y - 0.2, [broad[c] for c in top_ai.index], height=0.4, color=GREY, label="Description mentions AI work")
ax.set_yticks(y, top_ai.index)
ax.invert_yaxis()
for i, c in enumerate(top_ai.index):
    ax.text(top_ai["ai"].iloc[i] + 0.6, i + 0.2, f"{top_ai['ai'].iloc[i]:.1f}%", va="center", fontsize=9.5)
    ax.text(broad[c] + 0.6, i - 0.2, f"{broad[c]:.1f}%", va="center", fontsize=9.5)
ax.set_xlim(0, 40)
ax.set_xlabel("Share of the company's postings (%)")
ax.set_title("AI is a skill sprinkled into jobs, not a job family", fontsize=13, loc="left", pad=12)
ax.legend(frameon=False, loc="lower right")
save(fig, "06_ai_strict_vs_broad.png")

# 7. Manager seats per 100 IC postings, by function
funcs = ["Engineering", "Data / AI", "Design", "Sales / BD", "Product"]
mgr = pd.Series(S["manager_by_function"]).reindex(funcs)
one_per = {"Engineering": 6.5, "Data / AI": 7.7, "Design": 8.6, "Sales / BD": 4.4, "Product": 38.8}
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.barh(funcs, mgr.values, color=[RUST if f == "Product" else TEAL for f in funcs], height=0.6)
for i, f in enumerate(funcs):
    ax.text(mgr[f] + 0.4, i, f"{mgr[f]:.1f}%  — 1 manager seat per {one_per[f]:.0f} IC postings", va="center", fontsize=10.5)
ax.set_xlim(0, 22)
ax.set_xlabel("Share of the function's postings that are people-manager seats (%)")
ax.set_title("Manager seats exist in eng and data. In product, they barely exist.", fontsize=13, loc="left", pad=12)
save(fig, "07_manager_ladder.png")

# 8. Top hiring metros (fractional split of multi-hub postings)
metros = pd.Series(S["top_metros"]).head(10).sort_values()
fig, ax = plt.subplots(figsize=(8.5, 5.0))
ax.barh(metros.index, metros.values, color=TEAL, height=0.62)
for i, v in enumerate(metros.values):
    ax.text(v + 25, i, f"{v:,.0f}", va="center", fontsize=10.5)
ax.set_xlim(0, 1200)
ax.set_xlabel("Postings (fractional split across listed hubs)")
ax.set_title("San Francisco is still the #1 hiring hub in this census", fontsize=13, loc="left", pad=12)
save(fig, "08_top_metros.png")
print("all charts done")
