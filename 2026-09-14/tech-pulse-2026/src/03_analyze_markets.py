"""Part 3 — Capital: what the market thinks of tech (2021-2026).

Yahoo Finance daily closes for QQQ, SPY, XLK, SMH, ^IXIC. Computes normalized
performance, drawdowns/recoveries, and the AI-era (2023+) contribution. Saves
charts + findings JSON.
"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json

BASE = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026"
plt.rcParams.update({"figure.dpi": 140, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

syms = {"QQQ": "Nasdaq 100 (tech)", "SPY": "S&P 500", "XLK": "Tech sector",
        "SMH": "Semiconductors", "IXIC": "Nasdaq Comp"}
px = {}
for s in syms:
    fn = "yahoo_^ixic.csv" if s == "IXIC" else f"yahoo_{s.lower()}.csv"
    d = pd.read_csv(f"{BASE}/data/{fn}", parse_dates=["date"]).set_index("date")["close"]
    px[s] = d
px = pd.DataFrame(px).dropna()
norm = px / px.iloc[0] * 100

# drawdown helper
def drawdown(s):
    peak = s.cummax()
    return (s - peak) / peak

# ---------- chart 5: normalized performance ----------
fig, ax = plt.subplots(figsize=(11, 5.5))
colors = {"QQQ": "#1f4e79", "SPY": "#7f7f7f", "XLK": "#2e86ab", "SMH": "#c0392b", "IXIC": "#8e44ad"}
for s in syms:
    ax.plot(norm.index, norm[s], label=f"{s} ({syms[s]})", color=colors[s], lw=2 if s in ("QQQ", "SPY") else 1.2)
for x, lab in [("2022-01-03", "rate-hike\nselloff"), ("2022-11-30", "ChatGPT\nlaunch"),
               ("2023-10-27", "2023 bottom"), ("2025-04-08", "tariff\nshock")]:
    ax.axvline(pd.Timestamp(x), color="gray", ls="--", alpha=0.5)
ax.set_title("Tech vs the market, 2021–2026 (rebased to 100)", fontsize=14, pad=12)
ax.set_ylabel("Index = 100 on 2021-01-04")
ax.legend(frameon=False, ncol=2, fontsize=9)
fig.tight_layout(); fig.savefig(f"{BASE}/charts/05_tech_vs_market.png")

# ---------- chart 6: QQQ drawdown ----------
dd = drawdown(px["QQQ"])
fig, ax = plt.subplots(figsize=(11, 4))
ax.fill_between(dd.index, dd * 100, 0, color="#c0392b", alpha=0.35)
ax.plot(dd.index, dd * 100, color="#c0392b", lw=1.5)
ax.set_title("Nasdaq 100 drawdown: two crashes in four years", fontsize=14, pad=12)
ax.set_ylabel("Drawdown (%)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
fig.tight_layout(); fig.savefig(f"{BASE}/charts/06_qqq_drawdown.png")

# ---------- stats ----------
stats = {}
for s in syms:
    series = px[s]
    dd_s = drawdown(series)
    trough = dd_s.idxmin()
    recovered = dd_s[dd_s == 0].index
    rec = [d for d in recovered if d > trough]
    stats[s] = {
        "total_return_pct": round((series.iloc[-1] / series.iloc[0] - 1) * 100, 1),
        "max_drawdown_pct": round(dd_s.min() * 100, 1),
        "trough_date": str(trough.date()),
        "recovery_date": str(rec[0].date()) if rec else None,
    }
# AI-era share: gains since ChatGPT launch vs total
cut = pd.Timestamp("2022-11-30")
for s in syms:
    tot = px[s].iloc[-1] / px[s].iloc[0] - 1
    era = px[s].iloc[-1] / px[s].loc[px[s].index >= cut].iloc[0] - 1
    stats[s]["ai_era_return_pct"] = round(era * 100, 1)
    stats[s]["ai_era_share_of_total_pct"] = round(era / tot * 100, 1) if tot != 0 else None

with open(f"{BASE}/data/findings_markets.json", "w") as f:
    json.dump(stats, f, indent=2)
print(json.dumps(stats, indent=2))
