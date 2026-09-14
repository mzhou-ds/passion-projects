"""Part 4 — Synthesis: the efficiency era (layoffs vs market recovery).

Combines Part 1 (quarterly layoff headcount) with Part 3 (QQQ price) to show
that mass layoffs continued through 2024-2025 even as tech stocks fully
recovered — the "do more with less / AI restructuring" regime.
"""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026"
plt.rcParams.update({"figure.dpi": 140, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

lay = pd.read_csv(f"{BASE}/data/layoffs_clean_tb.csv", parse_dates=["date"])
lay = lay[lay["date"] >= "2022-01-01"].sort_values(["company", "date"]) \
         .drop_duplicates(["company", "date"])
q = lay.groupby(lay["date"].dt.to_period("Q").dt.to_timestamp())["total_laid_off"].sum()
qqq = pd.read_csv(f"{BASE}/data/yahoo_qqq.csv", parse_dates=["date"]).set_index("date")["close"]
qq = qqq.resample("Q").last()

corr = q.pct_change().corr(qq.pct_change().reindex(q.index, method="ffill"))
print(f"corr(quarterly layoff change, QQQ quarterly change) = {corr:.3f}")

fig, ax1 = plt.subplots(figsize=(11, 5))
ax1.bar(q.index, q.values / 1e3, width=70, color="#4a6fa5", alpha=0.7)
ax1.set_ylabel("Employees laid off (thousands)", color="#4a6fa5")
ax2 = ax1.twinx()
ax2.plot(qq.index, qq.values, color="#c0392b", lw=2.5)
ax2.set_ylabel("QQQ price ($)", color="#c0392b")
ax1.set_title("The efficiency era: layoffs continued even as tech stocks recovered",
              fontsize=14, pad=12)
ax1.axvline(pd.Timestamp("2022-11-30"), color="gray", ls="--", alpha=0.6)
ax1.text(pd.Timestamp("2022-11-30"), ax1.get_ylim()[1] * 0.95, " ChatGPT launch", fontsize=9)
fig.tight_layout()
fig.savefig(f"{BASE}/charts/11_efficiency_era.png")
