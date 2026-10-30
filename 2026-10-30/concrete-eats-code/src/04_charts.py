"""Charts for Concrete Eats Code. Style: plain, large labels, $B units."""
import pandas as pd, numpy as np, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(HERE, "charts"); os.makedirs(CH, exist_ok=True)
df = pd.read_csv(os.path.join(HERE, "data", "derived.csv"))
S = json.load(open(os.path.join(HERE, "data", "summary.json")))
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 150})
NAMES = {"MSFT": "Microsoft", "GOOGL": "Alphabet", "META": "Meta"}
COLORS = {"MSFT": "#0078D4", "GOOGL": "#34A853", "META": "#0082FB"}

# 1. The crossover: capex vs R&D, one panel per company
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
for ax, t in zip(axes, ["MSFT", "GOOGL", "META"]):
    g = df[(df.ticker == t) & (df.cal_year >= 2016)]
    ax.plot(g.cal_year, g.capex, "o-", color="#C0392B", label="Capex (PP&E)")
    ax.plot(g.cal_year, g.rnd, "s-", color="#2C3E50", label="R&D")
    ax.axvline(S["crossover"][t]["sustained_crossover_year"], color="gray",
               linestyle="--", linewidth=1)
    ax.set_title(f"{NAMES[t]} (crossover {S['crossover'][t]['sustained_crossover_year']})")
    ax.set_xlabel("Year"); ax.set_ylabel("$B")
axes[0].legend(fontsize=9, frameon=False)
fig.suptitle("Capex vs R&D: the lines crossed, then kept going", fontsize=13, y=1.02)
fig.tight_layout(); fig.savefig(f"{CH}/crossover.png", bbox_inches="tight"); plt.close(fig)

# 2. Capex intensity
fig, ax = plt.subplots(figsize=(9, 5))
for t in ["MSFT", "GOOGL", "META"]:
    g = df[(df.ticker == t) & (df.cal_year >= 2016)]
    ax.plot(g.cal_year, 100 * g.capex_intensity, "o-", color=COLORS[t], label=NAMES[t])
ax.set_ylabel("Capex as % of revenue"); ax.set_xlabel("Year")
ax.set_title("A quarter to a third of every revenue dollar now goes to concrete")
ax.legend(frameon=False); fig.tight_layout()
fig.savefig(f"{CH}/intensity.png", bbox_inches="tight"); plt.close(fig)

# 3. Productivity: revenue growth per capex dollar (3-yr)
fig, ax = plt.subplots(figsize=(9, 5))
for t in ["MSFT", "GOOGL", "META"]:
    g = df[(df.ticker == t) & (df.cal_year >= 2019)]
    ax.plot(g.cal_year, g.rev_per_capex_3yr, "o-", color=COLORS[t], label=NAMES[t])
ax.set_ylabel("$ of 3-yr revenue growth per $1 of capex (3-yr)")
ax.set_xlabel("Year"); ax.set_title("The marginal capex dollar buys less growth every year")
ax.legend(frameon=False); fig.tight_layout()
fig.savefig(f"{CH}/productivity.png", bbox_inches="tight"); plt.close(fig)

# 4. The toll collector: combined capex vs NVDA revenue
cap = pd.DataFrame(S["nvda_capture"])
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(cap))
ax.bar(x - 0.2, cap.hyper_capex, 0.4, label="Big-three combined capex", color="#2C3E50")
ax.bar(x + 0.2, cap.nvda_revenue, 0.4, label="NVIDIA total revenue", color="#76B900")
for xi, r in zip(x, cap.capture):
    ax.text(xi, max(cap.hyper_capex.max(), cap.nvda_revenue.max()) * 1.02,
            f"{r:.2f}x", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels([f"NVDA FY{int(y)}\nvs cal {int(c)}" for y, c in zip(cap.nvda_fy_end_year, cap.cal)])
ax.set_ylabel("$B"); ax.set_title("NVIDIA's revenue is now ~equal to the big three's entire capex")
ax.legend(frameon=False); fig.tight_layout()
fig.savefig(f"{CH}/capture.png", bbox_inches="tight"); plt.close(fig)

# 5. SHAP (in-sample association only)
m = json.load(open(os.path.join(HERE, "data", "model.json")))
items = sorted(m["shap_mean_abs"].items(), key=lambda kv: kv[1])
fig, ax = plt.subplots(figsize=(9, 4))
ax.barh([k for k, _ in items], [v for _, v in items], color="#2C3E50")
ax.set_title("What the full-sample model leans on (association, NOT prediction:\nleave-one-company-out R² is negative)")
ax.set_xlabel("Mean |SHAP value| on next-year revenue growth")
fig.tight_layout(); fig.savefig(f"{CH}/shap.png", bbox_inches="tight"); plt.close(fig)
print("charts:", sorted(os.listdir(CH)))
