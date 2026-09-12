"""Generate all charts for the Protein Atlas."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "output")
CH = os.path.join(HERE, "charts")
os.makedirs(CH, exist_ok=True)

TEAL, CORAL, GOLD = "#0e7c7b", "#d95f02", "#b5892e"
INK, GRID = "#222222", "#d9d9d9"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def short(name, n=42):
    return name if len(name) <= n else name[:n - 1] + "…"


derived = pd.read_csv(os.path.join(OUT, "foods_derived.csv"))
cat_prot = pd.read_csv(os.path.join(OUT, "category_protein_density.csv"))
cat_nrf = pd.read_csv(os.path.join(OUT, "category_nutrient_density.csv"))
cat_na = pd.read_csv(os.path.join(OUT, "category_sodium.csv"))
asia = pd.read_csv(os.path.join(OUT, "asian_spotlight.csv"))
top_leu = pd.read_csv(os.path.join(OUT, "top20_leucine_density.csv"))
top_sug = pd.read_csv(os.path.join(OUT, "top15_sugar.csv"))

# ------------------------------------------------- 1. protein density by category
fig, ax = plt.subplots(figsize=(9, 7))
c = cat_prot.sort_values("median")
ax.barh(c["category"], c["median"], color=TEAL)
for i, v in enumerate(c["median"]):
    ax.text(v + 0.15, i, f"{v:.1f}", va="center", fontsize=9)
ax.set_xlabel("Median g protein per 100 kcal")
ax.set_title("Protein density by food category — median grams of protein per 100 kcal",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(axis="x", color=GRID, alpha=.5)
fig.text(0.01, -0.01, "USDA FoodData Central, SR Legacy (7,756 foods). Spices/herbs excluded.",
         fontsize=8, color="#666666")
save(fig, "01_protein_density_by_category.png")

# ------------------------------------------------- 2. top protein-dense real foods
top = pd.read_csv(os.path.join(OUT, "top25_protein_density.csv"))
# drop protein isolates/powders for the "real food" leaderboard
real = top[~top["description"].str.contains("isolate|powder|Gelatins", case=False)].head(18)
real = real.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 7.5))
colors = [CORAL if "Finfish" in c else TEAL for c in real["category"]]
ax.barh([short(d) for d in real["description"]], real["prot_100kcal"], color=colors)
for i, v in enumerate(real["prot_100kcal"]):
    ax.text(v + 0.15, i, f"{v:.1f}", va="center", fontsize=9)
ax.set_xlabel("g protein per 100 kcal")
ax.set_title("The most protein-dense real foods in the USDA database",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(axis="x", color=GRID, alpha=.5)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=CORAL, label="Fish / shellfish"),
                   Patch(color=TEAL, label="Other")], fontsize=9, loc="lower right")
save(fig, "02_protein_density_top_foods.png")

# ------------------------------------------------- 3. protein leverage
prot_cats = ["Beef Products", "Poultry Products", "Pork Products",
             "Lamb, Veal, and Game Products", "Finfish and Shellfish Products",
             "Dairy and Egg Products", "Legumes and Legume Products",
             "Sausages and Luncheon Meats"]
excl = ["Spices and Herbs", "Quality Control Materials",
        "Branded Food Products Database", "American Indian/Alaska Native Foods"]
sub_all = derived[~derived["category"].isin(excl)]
pf = sub_all[sub_all["category"].isin(prot_cats)]
r_all = sub_all[["prot_kcal_share", "energy_density"]].corr(method="spearman").iloc[0, 1]
r_pf = pf[["prot_kcal_share", "energy_density"]].corr(method="spearman").iloc[0, 1]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for ax, d, title, r in [
    (axes[0], sub_all, f"All foods (n={len(sub_all):,})", r_all),
    (axes[1], pf, f"Protein foods: meat, fish, dairy, legumes (n={len(pf):,})", r_pf),
]:
    hb = ax.hexbin(d["prot_kcal_share"], d["energy_density"], gridsize=40,
                   cmap="YlGnBu", mincnt=1)
    ax.set_xlabel("% of calories from protein")
    ax.text(0.04, 0.96, f"Spearman r = {r:.2f}", transform=ax.transAxes,
            fontsize=11, va="top",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=GRID))
    ax.set_title(title, fontsize=11, fontweight="bold")
axes[0].set_ylabel("Energy density (kcal per 100 g)")
fig.suptitle("Testing protein leverage in food-composition data",
             fontsize=12, fontweight="bold", y=1.02)
fig.text(0.5, -0.02, "Water content dominates energy density across all foods; "
         "within protein foods, more protein per calorie clearly means fewer calories per bite.",
         ha="center", fontsize=9, color="#666666")
save(fig, "03_protein_leverage.png")

# ------------------------------------------------- 4. leucine density
tl = top_leu.head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh([short(d) for d in tl["description"]], tl["leu_100kcal_mg"], color=GOLD)
for i, (v, kc) in enumerate(zip(tl["leu_100kcal_mg"], tl["kcal_per_3g_leu"])):
    ax.text(v + 15, i, f"{v:.0f} mg  ({kc:.0f} kcal to 3 g)", va="center", fontsize=9)
ax.set_xlabel("mg leucine per 100 kcal")
ax.set_title("Leucine density — how many calories to trigger muscle protein synthesis (~3 g leucine)",
             fontsize=11, fontweight="bold", pad=12)
ax.grid(axis="x", color=GRID, alpha=.5)
save(fig, "04_leucine_density.png")

# ------------------------------------------------- 5. nutrient density by category
fig, ax = plt.subplots(figsize=(9, 7))
c = cat_nrf.sort_values("median")
cols = [TEAL if v >= 0 else CORAL for v in c["median"]]
ax.barh(c["category"], c["median"], color=cols)
ax.axvline(0, color=INK, lw=1)
for i, v in enumerate(c["median"]):
    ax.text(v + (4 if v >= 0 else -4), i, f"{v:.0f}", va="center", fontsize=9,
            ha="left" if v >= 0 else "right")
ax.set_xlabel("Median NRF-style nutrient density score (per 100 kcal)")
ax.set_title("Nutrient density by category — 9 nutrients to encourage minus sugar, sodium, sat fat",
             fontsize=11, fontweight="bold", pad=12)
ax.grid(axis="x", color=GRID, alpha=.5)
save(fig, "05_nutrient_density_by_category.png")

# ------------------------------------------------- 6. sugar bombs + sodium traps
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
ts = top_sug.head(12).iloc[::-1]
axes[0].barh([short(d) for d in ts["description"]], ts["sugar_100kcal"], color=CORAL)
axes[0].set_xlabel("g sugar per 100 kcal")
axes[0].set_title("Sugar bombs", fontsize=11, fontweight="bold")
axes[0].grid(axis="x", color=GRID, alpha=.5)
cn = cat_na.sort_values("median").tail(12)
axes[1].barh(cn["category"], cn["median"], color=TEAL)
for i, v in enumerate(cn["median"]):
    axes[1].text(v + 8, i, f"{v:.0f}", va="center", fontsize=9)
axes[1].set_xlabel("Median mg sodium per 100 kcal")
axes[1].set_title("Sodium traps by category", fontsize=11, fontweight="bold")
axes[1].grid(axis="x", color=GRID, alpha=.5)
fig.suptitle("The other side of the label: sugar and sodium", fontsize=12,
             fontweight="bold", y=1.02)
save(fig, "06_sugar_and_sodium.png")

# ------------------------------------------------- 7. asian spotlight
fig, ax = plt.subplots(figsize=(9, 5.5))
a = asia.sort_values("prot_100kcal")
cols = [TEAL if f in ("Tofu", "Tempeh", "Edamame", "Seitan/wheat gluten", "Natto")
        else GOLD for f in a["food"]]
ax.barh(a["food"], a["prot_100kcal"], color=cols)
for i, (v, lv) in enumerate(zip(a["prot_100kcal"], a["leu_mg_100kcal"])):
    lbl = f"{v:.1f}" + (f"  ·  leucine {lv:.0f} mg" if pd.notna(lv) else "")
    ax.text(v + 0.2, i, lbl, va="center", fontsize=9)
ax.set_xlabel("Median g protein per 100 kcal")
ax.set_title("Soy foods vs. animal proteins — protein density and leucine",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(axis="x", color=GRID, alpha=.5)
ax.legend(handles=[Patch(color=TEAL, label="Soy / plant"),
                   Patch(color=GOLD, label="Animal / other legume")], fontsize=9)
save(fig, "07_asian_spotlight.png")

# ------------------------------------------------- 8. fiber gap
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
f = derived["fiber_100kcal"].fillna(0)
axes[0].hist(f, bins=60, range=(0, 15), color=TEAL, edgecolor="white")
axes[0].axvline(f.median(), color=CORAL, lw=2, ls="--",
                label=f"median {f.median():.2f} g/100 kcal")
axes[0].set_xlabel("g fiber per 100 kcal")
axes[0].set_ylabel("Number of foods")
axes[0].set_title("Most foods have almost no fiber", fontsize=11, fontweight="bold")
axes[0].legend(fontsize=9)
axes[0].grid(axis="y", color=GRID, alpha=.5)
cf = derived.groupby("category")["fiber_100kcal"].median().sort_values().tail(10)
axes[1].barh(cf.index, cf.values, color=TEAL)
axes[1].set_xlabel("Median g fiber per 100 kcal")
axes[1].set_title("…except legumes and breakfast cereals", fontsize=11, fontweight="bold")
axes[1].grid(axis="x", color=GRID, alpha=.5)
fig.suptitle("The fiber gap: only 17% of foods deliver ≥3 g fiber per 100 g",
             fontsize=12, fontweight="bold", y=1.02)
save(fig, "08_fiber_gap.png")

print("done")
