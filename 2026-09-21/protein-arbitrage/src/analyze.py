"""Protein Arbitrage — main analysis.

Charts:
  1. league table: $ per 30 g protein (Aug 2026, BLS U.S. city average)
  2. efficient frontier: cost vs protein density, k-means value tiers + Pareto frontier
  3. protein inflation: indexed cost-per-30g-protein, Jan 2020 -> Aug 2026
  4. hedonic regression: what actually drives the price of protein?
Outputs: charts/*.png, output/summary stats + monthly budget table.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import os


def kmeans(X, k, seed=7, iters=100):
    """Minimal k-means (deterministic seed). Returns labels, centers."""
    rng = np.random.default_rng(seed)
    centers = X[rng.choice(len(X), k, replace=False)].copy()
    for _ in range(iters):
        d = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        labels = d.argmin(1)
        new = np.array([X[labels == j].mean(0) if (labels == j).any() else centers[j]
                        for j in range(k)])
        if np.allclose(new, centers):
            break
        centers = new
    return labels, centers


def ols(X, y):
    """OLS with intercept. Returns (coef incl. intercept, R^2, se, t)."""
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    s2 = (resid ** 2).sum() / (len(y) - A.shape[1])
    cov = s2 * np.linalg.inv(A.T @ A)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return coef, se, r2

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "..", "data")
CH = os.path.join(BASE, "..", "charts")
OUT = os.path.join(BASE, "..", "output")
os.makedirs(CH, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 10, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
    "grid.linestyle": "--",
})
TEAL, ORANGE, SLATE, RED, GREEN, PURPLE = (
    "#0e7c7b", "#e07a2e", "#5a6c7d", "#c0392b", "#2e8b57", "#7d5ba6")
CAT_COLORS = {"beef": "#c0392b", "pork": "#e07a2e", "poultry": "#2e8b57",
              "dairy": "#3a7bd5", "eggs": "#b8860b", "pantry": "#7d5ba6",
              "other": "#5a6c7d"}

CATEGORY = {
    "ground_chuck": "beef", "ground_beef": "beef", "ground_beef_lean": "beef",
    "chuck_roast_choice": "beef", "round_steak_choice": "beef",
    "sirloin_steak_choice": "beef", "ground_beef_all": "beef",
    "bacon": "pork", "pork_chops": "pork", "ham_boneless": "pork",
    "chicken_whole": "poultry", "chicken_breast_boneless": "poultry",
    "chicken_legs": "poultry",
    "eggs_large": "eggs",
    "milk_whole_gal": "dairy", "milk_all_gal": "dairy", "yogurt_all": "dairy",
    "cheese_american": "dairy", "cheese_cheddar": "dairy", "ice_cream": "dairy",
    "flour_white": "pantry", "rice_white": "pantry", "spaghetti": "pantry",
    "bread_white": "pantry", "potatoes": "pantry", "beans_dried": "pantry",
    "peanut_butter": "pantry", "tuna_light": "other",
}

df = pd.read_csv(os.path.join(D, "protein_table.csv"))
df["category"] = df["item"].map(CATEGORY)
cur = df[df["price_current"]].copy().sort_values("cost_per_30g_protein_usd")
old = df[~df["price_current"]].copy()
SHORT = {
    "flour_white": "Flour", "rice_white": "Rice", "spaghetti": "Pasta",
    "bread_white": "Bread", "ground_chuck": "Ground chuck", "ground_beef": "Ground beef",
    "ground_beef_lean": "Ground beef, lean", "ground_beef_all": "Ground beef (all)",
    "chuck_roast_choice": "Chuck roast", "round_steak_choice": "Round steak",
    "sirloin_steak_choice": "Sirloin steak", "bacon": "Bacon", "pork_chops": "Pork chops",
    "ham_boneless": "Ham", "chicken_whole": "Whole chicken",
    "chicken_breast_boneless": "Chicken breast", "chicken_legs": "Chicken legs",
    "eggs_large": "Eggs", "milk_whole_gal": "Whole milk", "milk_all_gal": "Low-fat milk",
    "yogurt_all": "Yogurt", "cheese_american": "American cheese",
    "cheese_cheddar": "Cheddar", "ice_cream": "Ice cream", "potatoes": "Potatoes",
    "beans_dried": "Dried beans", "peanut_butter": "Peanut butter", "tuna_light": "Tuna",
}
df["short"] = df["item"].map(SHORT)
cur["short"] = cur["item"].map(SHORT)

# ---------------------------------------------------------------- chart 1: league table
plot_df = pd.concat([cur, old]).sort_values("cost_per_30g_protein_usd", ascending=False)
fig, ax = plt.subplots(figsize=(10, 9))
y = np.arange(len(plot_df))
colors = [CAT_COLORS.get(c, SLATE) if cur_flag else "#c9c9c9"
          for c, cur_flag in zip(plot_df["category"], plot_df["price_current"])]
bars = ax.barh(y, plot_df["cost_per_30g_protein_usd"], color=colors, edgecolor="white")
labels = [l if f else f"{l} *" for l, f in zip(plot_df["label"], plot_df["price_current"])]
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Cost per 30 g protein (USD)")
ax.set_title("The protein league table — what 30 g of protein actually costs\n"
             "BLS U.S. city-average prices, Aug 2026 × USDA nutrition", fontsize=12, pad=12)
for i, v in enumerate(plot_df["cost_per_30g_protein_usd"]):
    ax.text(v + 0.06, i, f"${v:.2f}", va="center", fontsize=8.5)
ax.set_xlim(0, plot_df["cost_per_30g_protein_usd"].max() * 1.18)
ax.text(0.98, 0.01, "* greyed rows use the last available price (BLS series discontinued)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="grey")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=v, label=k) for k, v in CAT_COLORS.items()
                   if k in set(plot_df["category"])],
          loc="lower right", fontsize=8, title="Category")
fig.tight_layout(); fig.savefig(os.path.join(CH, "01_league_table.png")); plt.close(fig)

# ---------------------------------------------------------------- chart 2: frontier + tiers
X = np.column_stack([np.log(cur["cost_per_30g_protein_usd"]),
                     cur["protein_g_per_100kcal"]])
Xs = (X - X.mean(0)) / X.std(0)
labels, centers = kmeans(Xs, 4, seed=7)
cur = cur.copy(); cur["tier"] = labels
# name tiers by centroid cost
order = np.argsort(centers[:, 0])
tier_names = {order[0]: "Budget staples", order[1]: "Efficient everyday",
              order[2]: "Mid-market", order[3]: "Luxury / low-density"}
cur["tier_name"] = cur["tier"].map(tier_names)

# Pareto frontier: minimize cost AND maximize density
pts = cur[["cost_per_30g_protein_usd", "protein_g_per_100kcal"]].values
pareto = []
for i, p in enumerate(pts):
    if not np.any((pts[:, 0] <= p[0]) & (pts[:, 1] >= p[1]) &
                  ((pts[:, 0] < p[0]) | (pts[:, 1] > p[1]))):
        pareto.append(i)
pf = cur.iloc[pareto].sort_values("cost_per_30g_protein_usd")

fig, ax = plt.subplots(figsize=(10, 7))
tier_palette = {"Budget staples": GREEN, "Efficient everyday": TEAL,
                "Mid-market": ORANGE, "Luxury / low-density": RED}
for name, g in cur.groupby("tier_name"):
    ax.scatter(g["cost_per_30g_protein_usd"], g["protein_g_per_100kcal"],
               s=90, color=tier_palette[name], label=name, alpha=0.85,
               edgecolors="white", linewidths=0.8, zorder=3)
ax.plot(pf["cost_per_30g_protein_usd"], pf["protein_g_per_100kcal"],
        color="black", ls="--", lw=1.2, alpha=0.7, label="Efficient frontier")
# manual nudges for overlapping annotations: item -> (dx, dy) in points
NUDGE = {"chicken_whole": (-52, -12), "chicken_legs": (4, 8),
         "ground_beef": (4, -14), "ground_chuck": (4, 6),
         "round_steak_choice": (4, 8), "sirloin_steak_choice": (4, -14),
         "milk_whole_gal": (4, -14), "milk_all_gal": (4, 6),
         "cheese_american": (4, -14), "cheese_cheddar": (4, 6)}
for _, r in cur.iterrows():
    dx, dy = NUDGE.get(r["item"], (4, 4))
    ax.annotate(r["short"], (r["cost_per_30g_protein_usd"],
                r["protein_g_per_100kcal"]), fontsize=8,
                xytext=(dx, dy), textcoords="offset points", alpha=0.9)
ax.set_xscale("log")
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.2f}"))
ax.set_xlabel("Cost per 30 g protein (USD, log scale)")
ax.set_ylabel("Protein density (g protein per 100 kcal)")
ax.set_title("The protein efficient frontier\n"
             "Foods on the dashed line are unbeaten on price AND density",
             fontsize=12, pad=12)
ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(os.path.join(CH, "02_frontier.png")); plt.close(fig)

# ---------------------------------------------------------------- chart 3: protein inflation
panel = pd.read_csv(os.path.join(D, "bls_prices_panel.csv"), parse_dates=["date"])
SERIES = ["eggs_large", "chicken_breast_boneless", "ground_beef_all",
          "milk_whole_gal", "cheese_cheddar", "chicken_legs",
          "beans_dried", "bread_white"]
ref = cur.set_index("item")["cost_per_30g_protein_usd"]
fig, ax = plt.subplots(figsize=(11, 6.5))
for item in SERIES:
    p = panel[panel["item"] == item].sort_values("date")
    p = p[(p["date"] >= "2020-01-01") & (p["date"] <= "2026-08-01")].copy()
    if len(p) < 12 or item not in ref.index:
        continue
    base = p.iloc[0]["price"]
    idx = p["price"] / base * 100  # nutrition constant -> same index for cost/30g
    lab = df.set_index("item").loc[item, "short"]
    ax.plot(p["date"], idx, lw=2, label=f"{lab} (${ref[item]:.2f}/30g today)")
ax.axhline(100, color="black", lw=1, alpha=0.5)
ax.set_ylabel("Cost per 30 g protein, indexed (Jan 2020 = 100)")
ax.set_title("Protein inflation: what happened to the price of 30 g of protein since 2020\n"
             "BLS average prices, nutrition held constant", fontsize=12, pad=12)
ax.legend(fontsize=8.5, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(CH, "03_protein_inflation.png")); plt.close(fig)

# ---------------------------------------------------------------- chart 4: hedonic regression
reg = cur[~cur["item"].isin(["ice_cream"])].copy()  # ice cream unit conversion is squishy
reg["log_cost"] = np.log(reg["cost_per_30g_protein_usd"])
dums = pd.get_dummies(reg["category"], prefix="cat", drop_first=True, dtype=float)
Xr = pd.concat([reg[["protein_g_per_100kcal", "fat_g_per_100g"]], dums,
                reg[["bone_in"]].astype(float)], axis=1)
Xr = Xr.fillna(Xr.median())
coef_all, se_all, r2 = ols(Xr.values, reg["log_cost"].values)
coef = pd.Series(coef_all[1:], index=Xr.columns).sort_values()
se = pd.Series(se_all[1:], index=Xr.columns)

PRETTY = {"fat_g_per_100g": "Fat (g/100g)", "protein_g_per_100kcal": "Protein density",
           "cat_pork": "Pork (vs beef)", "bone_in": "Bone-in",
           "cat_dairy": "Dairy (vs beef)", "cat_poultry": "Poultry (vs beef)",
           "cat_eggs": "Eggs (vs beef)", "cat_pantry": "Pantry staples (vs beef)"}
fig, ax = plt.subplots(figsize=(9, 5.5))
cols = [GREEN if c < 0 else RED for c in coef.values]
ypos = np.arange(len(coef))
ax.barh(ypos, coef.values, color=cols, edgecolor="white",
        xerr=se.loc[coef.index].values, error_kw={"ecolor": "black", "capsize": 3, "alpha": 0.6})
ax.set_yticks(ypos); ax.set_yticklabels([PRETTY.get(i, i) for i in coef.index], fontsize=9)
ax.set_xlabel("Effect on log(cost per 30 g protein)")
ax.set_title(f"What actually drives the price of protein? (hedonic regression, R² = {r2:.2f})\n"
             "Negative = cheaper protein; positive = more expensive", fontsize=11, pad=12)
fig.tight_layout(); fig.savefig(os.path.join(CH, "04_price_drivers.png")); plt.close(fig)

# ---------------------------------------------------------------- monthly budget + rotisserie
budget = cur[["label", "cost_per_30g_protein_usd"]].copy()
budget["monthly_cost_160g_day"] = (budget["cost_per_30g_protein_usd"] * 160 / 30 * 30).round(0)
budget.to_csv(os.path.join(OUT, "monthly_protein_budget.csv"), index=False)

# rotisserie: USDA roasted chicken meat protein
import csv as _csv
SR = os.path.join(D, "sr_legacy", "FoodData_Central_sr_legacy_food_csv_2018-04")
nut = {}
with open(os.path.join(SR, "food_nutrient.csv")) as f:
    for row in _csv.DictReader(f):
        if row["fdc_id"] == "171054" and row["nutrient_id"] in ("1003", "1008"):
            nut[row["nutrient_id"]] = float(row["amount"])
roast_prot = nut.get("1003", 27.0)
rot = {"price": 4.99, "weight_lb": 3.0, "meat_yield": 0.70,
       "protein_g_per_100g_cooked": roast_prot}
rot_meat_g = rot["weight_lb"] * 453.592 * rot["meat_yield"]
rot_protein = rot_meat_g * rot["protein_g_per_100g_cooked"] / 100
rot["cost_per_30g"] = rot["price"] / rot_protein * 30

raw = cur[cur["item"] == "chicken_whole"].iloc[0]
raw_cost_3lb = raw["price_usd"] * 3.0
raw_meat_g = 3.0 * 453.592 * 0.70 * 0.75  # bone out, then cooking loss
raw_protein = raw_meat_g * rot["protein_g_per_100g_cooked"] / 100
raw_cost_per_30 = raw_cost_3lb / raw_protein * 30

with open(os.path.join(OUT, "rotisserie_math.txt"), "w") as f:
    f.write(f"Costco rotisserie $4.99 / 3 lb bird:\n"
            f"  cooked meat protein (USDA fdc 171054): {roast_prot:.1f} g/100g\n"
            f"  est. protein per bird: {rot_protein:.0f} g -> ${rot['cost_per_30g']:.2f} per 30 g\n"
            f"Raw whole chicken @ ${raw['price_usd']:.3f}/lb, 3 lb = ${raw_cost_3lb:.2f}:\n"
            f"  est. protein after bone-out + cooking: {raw_protein:.0f} g -> ${raw_cost_per_30:.2f} per 30 g\n")

# console summary
print("=== cheapest 8 (current) ===")
print(cur[["label", "cost_per_30g_protein_usd"]].head(8).to_string(index=False))
print("\n=== priciest 5 (current) ===")
print(cur[["label", "cost_per_30g_protein_usd"]].tail(5).to_string(index=False))
print(f"\n=== regression R2={r2:.3f} ==="); print(coef.to_string())
print(f"\n=== rotisserie ${rot['cost_per_30g']:.2f}/30g vs raw whole ${raw_cost_per_30:.2f}/30g ===")
print("\n=== monthly budget for 160 g protein/day ===")
print(budget.head(8).to_string(index=False))
