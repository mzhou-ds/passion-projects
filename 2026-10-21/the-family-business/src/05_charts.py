"""Charts for the README. All numbers come from data/summary.json and
data/models_genealogy.csv; nothing is hand-entered."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
S = json.loads((HERE / "data" / "summary.json").read_text())
df = pd.read_csv(HERE / "data" / "models_genealogy.csv", low_memory=False)
CH = HERE / "charts"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

demand = df[df["samples"].str.contains("downloads")]

# 1. Lorenz curve of downloads among demand models
x = np.sort(demand["downloads"].values)
cum = np.cumsum(x) / x.sum()
plt.figure(figsize=(7, 5))
plt.plot(np.linspace(0, 100, len(cum)), cum * 100, color="#b34700", lw=2)
plt.plot([0, 100], [0, 100], ls="--", color="grey", lw=1)
plt.xlabel("Share of top-5,000 models (ranked by downloads, %)")
plt.ylabel("Share of their downloads (%)")
plt.title("Downloads are a power law, not a market")
plt.tight_layout(); plt.savefig(CH / "lorenz.png", dpi=150); plt.close()

# 2. Top families by downloads
tf = pd.DataFrame(S["top_families"]).head(12).iloc[::-1]
plt.figure(figsize=(8.5, 5.5))
plt.barh(tf["family"], tf["downloads"] / 1e6, color="#31572c")
plt.xlabel("Last-30-day downloads (millions, incl. all descendants in sample)")
plt.title("The family trees that collect the downloads")
plt.tight_layout(); plt.savefig(CH / "families.png", dpi=150); plt.close()

# 3. Derivative share: models vs downloads
labels = ["Share of\nmodels", "Share of\nlast-30d downloads", "Share of\nall-time downloads"]
vals = [S["demand_deriv_share_of_models"], S["demand_deriv_share_of_downloads"],
        S["demand_deriv_share_of_downloads_alltime"]]
plt.figure(figsize=(7, 4.5))
plt.bar(labels, [v * 100 for v in vals], color=["#7f8c8d", "#b34700", "#31572c"])
for i, v in enumerate(vals):
    plt.text(i, v * 100 + 1.5, f"{v:.0%}", ha="center", fontweight="bold")
plt.ylabel("%")
plt.title("Derivatives: a minority of models, a different share of demand")
plt.tight_layout(); plt.savefig(CH / "derivative_share.png", dpi=150); plt.close()

# 4. Vintage: download share by creation cohort
vt = pd.Series(S["vintage_download_share"]).sort_index()
plt.figure(figsize=(8, 4.5))
plt.bar(vt.index, vt.values * 100, color="#4a6fa5")
for i, v in enumerate(vt.values):
    plt.text(i, v * 100 + 1, f"{v:.0%}", ha="center", fontweight="bold")
plt.ylabel("Share of last-30-day downloads (%)")
plt.xlabel("Model creation cohort (Hub createdAt)")
plt.title("Old models still collect the downloads")
plt.xticks(rotation=30, ha="right")
plt.tight_layout(); plt.savefig(CH / "vintage.png", dpi=150); plt.close()

# 5. Task mix: downloads share vs model share
tasks = list(S["task_download_share"].keys())[:10]
dsh = [S["task_download_share"][t] * 100 for t in tasks]
msh = [S["task_model_share_top"].get(t, 0) * 100 for t in tasks]
y = np.arange(len(tasks))
plt.figure(figsize=(8.5, 5.5))
plt.barh(y + 0.2, dsh, height=0.4, label="Share of downloads", color="#b34700")
plt.barh(y - 0.2, msh, height=0.4, label="Share of models", color="#7f8c8d")
plt.yticks(y, tasks)
plt.gca().invert_yaxis()
plt.xlabel("% of top-5,000 universe")
plt.title("What the downloads actually are: tasks, not chat")
plt.legend()
plt.tight_layout(); plt.savefig(CH / "task_mix.png", dpi=150); plt.close()

# 6. Likes vs downloads scatter (union, both > 0)
b = df[(df["downloads"] > 0) & (df["likes"] > 0)]
plt.figure(figsize=(7, 5.5))
plt.scatter(np.log10(b["likes"]), np.log10(b["downloads"]), s=3, alpha=0.25, color="#4a6fa5")
plt.xlabel("Likes (log10), human attention")
plt.ylabel("Last-30-day downloads (log10), machine usage")
plt.title("Attention and usage are different economies")
plt.tight_layout(); plt.savefig(CH / "likes_vs_downloads.png", dpi=150); plt.close()

print("charts written:", sorted(p.name for p in CH.glob("*.png")))
