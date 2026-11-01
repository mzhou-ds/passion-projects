"""Charts for The Border on the Menu. Reads data/ from 02_analysis.py."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
D, C = BASE / "data", BASE / "charts"
C.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False})
CA, US = "#d62728", "#1f77b4"

stats = pd.read_csv(D / "city_stats.csv")
shares = pd.read_csv(D / "city_cuisine.csv")
pairs = pd.read_csv(D / "pairwise.csv")
means = pd.read_csv(D / "family_country_means.csv", index_col=0)

def save(fig, name):
    fig.tight_layout()
    fig.savefig(C / name, dpi=150)
    plt.close(fig)

# 1. Diversity (entropy) by city, coloured by country.
s = stats.sort_values("entropy")
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(s["city"], s["entropy"],
        color=[CA if c == "CA" else US for c in s["country"]])
ax.set_xlabel("Shannon entropy of cuisine-family shares (tagged restaurants)")
ax.set_title("Menu variety is a wash across the border (US mean slightly higher)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=CA, label="Canada"), Patch(color=US, label="US")])
save(fig, "diversity.png")

# 2. Heatmap: selected families x cities (shares %).
fams = ["chinese", "japanese", "korean", "indian", "mexican", "italian",
        "american", "french", "mediterranean", "thai", "vietnamese", "canadian"]
w = shares.pivot_table(index="city", columns="family", values="share", fill_value=0.0)
w = w.reindex(columns=[f for f in fams if f in w.columns])
order = ["vancouver", "calgary", "edmonton", "winnipeg", "toronto", "ottawa",
         "montreal", "halifax", "seattle", "portland", "san-francisco",
         "los-angeles", "houston", "chicago", "new-york", "boston"]
w = w.reindex(index=[c for c in order if c in w.index])
fig, ax = plt.subplots(figsize=(10, 6.5))
im = ax.imshow(w.values * 100, cmap="YlOrRd", vmin=0,
               vmax=np.percentile(w.values * 100, 95))
ax.set_xticks(range(len(w.columns))); ax.set_xticklabels(w.columns, rotation=35, ha="right")
ax.set_yticks(range(len(w.index))); ax.set_yticklabels(w.index)
for i in range(len(w.index)):
    for j in range(len(w.columns)):
        v = w.values[i, j] * 100
        if v >= 1:
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8)
ax.set_title("Cuisine share (%) among tagged restaurants — rows ordered north to south")
fig.colorbar(im, ax=ax, label="% of tagged restaurants")
save(fig, "heatmap.png")

# 3. Menu distance vs kilometres, same-country vs cross-border.
fig, ax = plt.subplots(figsize=(9, 5.5))
for cross, col, lab in [(False, US, "same country"), (True, CA, "cross-border")]:
    d = pairs[pairs["cross_border"] == cross]
    ax.scatter(d["km"], d["cosine_distance"], c=col, alpha=0.7, label=lab)
for _, r in pairs.sort_values("km").head(8).iterrows():
    ax.annotate(f"{r['city_a']}–{r['city_b']}", (r["km"], r["cosine_distance"]),
                fontsize=7, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Distance between city cores (km)")
ax.set_ylabel("Menu distance (1 − cosine similarity of cuisine shares)")
ax.set_title("Menus drift with distance — and jump at the border")
ax.legend()
save(fig, "border_scatter.png")

# 4. Permeability: CA/US share ratio for headline families (log scale).
fam = ["mexican", "chinese", "japanese", "korean", "indian", "thai",
       "vietnamese", "italian", "american", "french", "mediterranean", "canadian"]
m = means.reindex(index=[f for f in fam if f in means.index]).copy()
m = m.sort_values("ratio_ca_us")
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(m.index, m["ratio_ca_us"], color=[CA if v >= 1 else US for v in m["ratio_ca_us"]])
ax.axvline(1, color="black", lw=1)
ax.set_xscale("log")
ax.set_xlabel("Canada share ÷ US share (log scale; 1 = identical)")
ax.set_title("The border is a wall for some cuisines, a sieve for others")
for i, v in enumerate(m["ratio_ca_us"]):
    ax.text(v * 1.08, i, f"{v:.2f}×", va="center", fontsize=9)
save(fig, "permeability.png")

# 5. Chinese specificity: regional-subtype share of Chinese-family places.
s2 = stats.sort_values("chinese_regional_share")
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(s2["city"], s2["chinese_regional_share"] * 100,
        color=[CA if c == "CA" else US for c in s2["country"]])
ax.set_xlabel("% of Chinese-family restaurants tagged with a regional subtype\n(Sichuan, Cantonese, dim sum, …) rather than generic 'chinese'")
ax.set_title("Chinese menus are no more specific north of the border (CA 4.7% vs US 5.8%)")
ax.legend(handles=[Patch(color=CA, label="Canada"), Patch(color=US, label="US")])
save(fig, "chinese_specificity.png")
print("charts done:", sorted(p.name for p in C.glob("*.png")))
