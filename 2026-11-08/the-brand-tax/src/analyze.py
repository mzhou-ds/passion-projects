"""Analysis for The Brand Tax (build #62).

Metrics per product:
  cost_per_trial_dose = price / (total active in container / trial dose)
  servings_per_day    = trial dose / dose per serving
  dose_gap_pct        = dose per serving / trial dose (100% = one serving is the trial dose)
  markup_vs_cheapest  = cost per trial dose / cheapest cost per trial dose in the same compound

Stacks (one product per compound, at trial dose):
  cheapest  = cheapest cost-per-trial-dose product in each compound
  premium   = all-Thorne stack (Thorne where it makes the compound; ResveraCel for NR)
  gummy     = cheapest gummy in each compound (NR has no gummy: Life Extension 300 mg)

Charts:
  01_cost_per_dose.png   cost per trial dose, every product, grouped by compound (log scale)
  02_markup_by_tier.png  markup vs compound cheapest, by tier
  03_dose_gap.png        dose per serving as % of trial dose, every product
  04_stack_cost.png      annual cost of the three stacks
  05_gummy_count.png     gummies per day to hit every trial dose on the gummy stack
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "products.csv"
CHARTS = ROOT / "charts"
OUT = ROOT / "output"
CHARTS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#666666",
    "axes.labelcolor": "#222222",
    "figure.facecolor": "white",
})

COMPOUND_LABELS = {
    "creatine": "Creatine\n5 g/day",
    "magnesium": "Magnesium glycinate\n400 mg/day",
    "vitamin_d3": "Vitamin D3\n2,000 IU/day",
    "omega3": "Omega-3 (EPA+DHA)\n1,000 mg/day",
    "zinc": "Zinc picolinate\n15 mg/day",
    "nr": "Nicotinamide riboside\n300 mg/day",
}
TIER_COLORS = {"bulk": "#2c7fb8", "mainstream": "#7fcdbb", "premium": "#f03b20", "brand": "#8856a7", "gummy": "#e31a1c"}
FORM_COLORS = {"powder": "#2c7fb8", "capsule": "#41ab5d", "softgel": "#41ab5d", "gummy": "#e31a1c"}

df = pd.read_csv(DATA)
df["markup_vs_cheapest"] = df.groupby("compound")["cost_per_trial_dose"].transform(
    lambda s: s / s.min())
df["label"] = df["brand"] + " " + df["form"]

# ---------------------------------------------------------------- stacks
STACKS = {
    "cheapest": {
        "creatine": "BulkSupplements", "magnesium": "Pure Encapsulations",
        "vitamin_d3": "NOW", "omega3": "NOW Foods", "zinc": "NOW", "nr": "Life Extension",
    },
    "premium (all Thorne)": {
        "creatine": "Thorne", "magnesium": "Thorne", "vitamin_d3": "Thorne",
        "omega3": "Thorne", "zinc": "Thorne", "nr": "Thorne",
    },
    "gummy": {
        "creatine": "Legion Athletics", "magnesium": "Nature's Bounty",
        "vitamin_d3": "Nature Made", "omega3": "Nature Made",
        "zinc": "Nature's Bounty", "nr": "Life Extension",
    },
}
# disambiguate duplicate brand rows by picking, per compound+stack, the row
# with the lowest cost per trial dose among that brand's rows in that compound
stack_rows = {}
for stack_name, picks in STACKS.items():
    chosen = {}
    for compound, brand in picks.items():
        sub = df[(df["compound"] == compound) & (df["brand"] == brand)]
        if stack_name == "cheapest":
            # cheapest stack = globally cheapest per-dose product, any brand
            sub = df[df["compound"] == compound]
        if stack_name == "premium (all Thorne)" and compound == "zinc":
            sub = sub[sub["dose_per_serving"] == 15]  # the 15 mg Thorne zinc
        if stack_name == "gummy" and compound == "vitamin_d3":
            sub = sub[sub["form"] == "gummy"]
        if stack_name == "gummy" and compound == "nr":
            sub = sub[sub["dose_per_serving"] == 300]
        # otherwise: cheapest cost per trial dose wins (final sort below)
        chosen[compound] = sub.sort_values("cost_per_trial_dose").iloc[0]
    stack_rows[stack_name] = chosen

stack_summary = {}
for name, chosen in stack_rows.items():
    daily = sum(r["cost_per_trial_dose"] for r in chosen.values())
    stack_summary[name] = {
        "per_day": round(daily, 4),
        "per_month": round(daily * 30, 2),
        "per_year": round(daily * 365, 2),
        "products": {c: f"{r['brand']} ({r['form']}, ${r['cost_per_trial_dose']:.3f}/day)"
                     for c, r in chosen.items()},
    }

# gummies per day on the gummy stack
gummy = stack_rows["gummy"]
gummies_per_day = {}
for c, r in gummy.items():
    gps = r["gummies_per_serving"]
    if pd.notna(gps):
        gummies_per_day[c] = float(r["servings_per_day"] * gps)
gummies_total = sum(gummies_per_day.values())

# ---------------------------------------------------------------- headline stats
cheapest = df.loc[df.groupby("compound")["cost_per_trial_dose"].idxmin()]
most_exp = df.loc[df.groupby("compound")["cost_per_trial_dose"].idxmax()]
stats = {
    "n_products": int(len(df)),
    "n_compounds": int(df["compound"].nunique()),
    "under_dosed_servings": int((df["dose_gap_pct"] < 100).sum()),
    "under_dosed_pct": round(100 * (df["dose_gap_pct"] < 100).mean(), 1),
    "median_servings_per_day": round(float(df["servings_per_day"].median()), 2),
    "median_markup_gummy": round(float(df[df["form"] == "gummy"]["markup_vs_cheapest"].median()), 2),
    "median_markup_premium": round(float(df[df["tier"] == "premium"]["markup_vs_cheapest"].median()), 2),
    "median_markup_bulk": round(float(df[df["tier"] == "bulk"]["markup_vs_cheapest"].median()), 2),
    "max_markup": round(float(df["markup_vs_cheapest"].max()), 1),
    "max_markup_product": df.loc[df["markup_vs_cheapest"].idxmax(), "brand"]
        + " " + df.loc[df["markup_vs_cheapest"].idxmax(), "product"][:60],
    "gummies_per_day_on_gummy_stack": round(gummies_total, 1),
    "stacks": stack_summary,
    "cheapest_per_compound": {
        c: {"brand": r["brand"], "form": r["form"], "cost_per_day": round(r["cost_per_trial_dose"], 4)}
        for c, r in cheapest.set_index("compound").iterrows()
    },
    "priciest_per_compound": {
        c: {"brand": r["brand"], "form": r["form"], "cost_per_day": round(r["cost_per_trial_dose"], 4),
            "markup_vs_cheapest": round(r["markup_vs_cheapest"], 1)}
        for c, r in most_exp.set_index("compound").iterrows()
    },
}
(OUT / "results.json").write_text(json.dumps(stats, indent=2))

# ---------------------------------------------------------------- chart 1: cost per trial dose, log scale
fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharex=False)
axes = axes.ravel()
for ax, (compound, sub) in zip(axes, df.groupby("compound", sort=False)):
    sub = sub.sort_values("cost_per_trial_dose").copy()
    # disambiguate repeated brand+form labels inside a compound
    counts = sub.groupby(["brand", "form"])["brand"].transform("count")
    dup = counts > 1
    sub["short"] = sub["brand"] + " (" + sub["form"] + ")"
    sub.loc[dup, "short"] = (
        sub.loc[dup, "brand"] + " " + sub.loc[dup, "dose_per_serving"].astype(int).astype(str)
        + sub.loc[dup, "dose_unit"] + "/" + sub.loc[dup, "servings_per_container"].astype(int).astype(str)
        + " (" + sub.loc[dup, "form"] + ")")
    colors = [FORM_COLORS[f] for f in sub["form"]]
    ax.barh(sub["short"], sub["cost_per_trial_dose"],
            color=colors, edgecolor="white", height=0.62)
    ax.set_xscale("log")
    ax.set_xlim(0.02, 10)
    ax.set_xticks([0.05, 0.2, 1, 5])
    ax.set_xticklabels(["$0.05", "$0.20", "$1", "$5"])
    ax.set_title(COMPOUND_LABELS[compound], fontsize=11, fontweight="bold")
    ax.set_xlabel("cost per trial dose ($/day, log scale)")
    ax.grid(axis="x", alpha=0.3)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
fig.suptitle("The same dose, wildly different prices: cost per trial dose by product",
             fontsize=14, fontweight="bold", y=1.0)
fig.tight_layout()
fig.savefig(CHARTS / "01_cost_per_dose.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- chart 2: markup by tier
# Median markup per tier (bars) with every product as a dot. "Mainstream" has
# only one non-gummy product, so it is a single dot, not a distribution.
fig, ax = plt.subplots(figsize=(9, 5))
tier_order = ["bulk", "mainstream", "premium", "brand", "gummy"]
plot_df = df.copy()
plot_df["tier_label"] = plot_df["tier"]
plot_df.loc[plot_df["form"] == "gummy", "tier_label"] = "gummy"
medians = [plot_df[plot_df["tier_label"] == t]["markup_vs_cheapest"].median() for t in tier_order]
ns = [int((plot_df["tier_label"] == t).sum()) for t in tier_order]
x = np.arange(len(tier_order))
bars = ax.bar(x, medians, color=[TIER_COLORS[t] for t in tier_order],
              edgecolor="white", width=0.55, alpha=0.85, zorder=2)
for xi, t in enumerate(tier_order):
    vals = plot_df[plot_df["tier_label"] == t]["markup_vs_cheapest"]
    shown = vals[vals <= 12]
    ax.scatter(np.random.uniform(xi - 0.16, xi + 0.16, size=len(shown)), shown,
               s=30, alpha=0.65, color="#333333", zorder=3)
ax.text(4, 11.4, "▲ 31.6x outlier:\nNature Made fish-oil gummies",
        ha="center", fontsize=9, color="#e31a1c")
ax.axhline(1, color="#999999", linestyle="--", linewidth=1)
ax.set_xticks(x)
ax.set_xticklabels([f"{t}\n(n={n})" for t, n in zip(tier_order, ns)])
ax.set_ylabel("price multiple vs cheapest product for the same compound")
ax.set_title("The gummy tax: same molecule, priced by form factor and brand\n(median markup; dots = individual products)",
             fontsize=12, fontweight="bold")
for bar, m in zip(bars, medians):
    ax.text(bar.get_x() + bar.get_width() / 2, m + 0.6, f"{m:.1f}x",
            ha="center", fontsize=11, fontweight="bold")
ax.set_ylim(0, 12)
ax.grid(axis="y", alpha=0.3)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(CHARTS / "02_markup_by_tier.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- chart 3: dose gap
fig, ax = plt.subplots(figsize=(11, 8))
d = df.sort_values(["compound", "dose_gap_pct"])
colors = ["#e31a1c" if v < 100 else "#41ab5d" for v in d["dose_gap_pct"]]
labels = d["brand"] + " " + d["form"] + " (" + d["compound"] + ")"
ax.barh(labels, d["dose_gap_pct"], color=colors, edgecolor="white", height=0.62)
ax.axvline(100, color="#222222", linewidth=1.5)
ax.text(103, 1, "one serving = the trial dose", fontsize=9, va="center")
ax.set_xlabel("dose in one serving, as % of the trial dose")
ax.set_title("One serving is usually not one dose: the serving-size gap",
             fontsize=12, fontweight="bold")
ax.grid(axis="x", alpha=0.3)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(CHARTS / "03_dose_gap.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- chart 4: stack cost
fig, ax = plt.subplots(figsize=(9, 5))
names = list(stack_summary.keys())
yearly = [stack_summary[n]["per_year"] for n in names]
colors = ["#2c7fb8", "#f03b20", "#e31a1c"]
bars = ax.barh(names, yearly, color=colors, edgecolor="white", height=0.55)
ax.set_xlabel("annual cost at trial doses ($/year)")
ax.set_title(f"The same six molecules: \\${stack_summary['cheapest']['per_year']:,.0f} a year, or "
             f"\\${stack_summary['gummy']['per_year']:,.0f}",
             fontsize=12, fontweight="bold")
for bar, v, n in zip(bars, yearly, names):
    ax.text(v + 60, bar.get_y() + bar.get_height() / 2,
            f"\\${v:,.0f}/yr  (\\${stack_summary[n]['per_month']:,.0f}/mo)", va="center", fontsize=11)
ax.set_xlim(0, max(yearly) * 1.35)
ax.grid(axis="x", alpha=0.3)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(CHARTS / "04_stack_cost.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- chart 5: gummies per day
fig, ax = plt.subplots(figsize=(9, 5))
items = sorted(gummies_per_day.items(), key=lambda kv: -kv[1])
labels = [COMPOUND_LABELS[c].replace("\n", " ") for c, _ in items]
vals = [v for _, v in items]
ax.barh(labels, vals, color="#e31a1c", edgecolor="white", height=0.55)
ax.set_xlabel("gummies per day to reach the trial dose")
ax.set_title(f"The all-gummy stack is {gummies_total:.0f} gummies a day",
             fontsize=12, fontweight="bold")
for i, v in enumerate(vals):
    ax.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=11)
ax.set_xlim(0, max(vals) * 1.25)
ax.grid(axis="x", alpha=0.3)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(CHARTS / "05_gummy_count.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- findings text
lines = []
lines.append("THE BRAND TAX — headline numbers (2026-11-08, 40 products, 6 compounds)")
lines.append("")
for name, s in stack_summary.items():
    lines.append(f"STACK {name}: ${s['per_day']:.2f}/day, ${s['per_month']:.0f}/month, ${s['per_year']:,.0f}/year")
lines.append("")
lines.append(f"Under-dosed servings (one serving < trial dose): {stats['under_dosed_servings']}/{stats['n_products']} "
             f"({stats['under_dosed_pct']}%). Median servings/day to hit trial dose: {stats['median_servings_per_day']}.")
lines.append(f"Median markup vs compound cheapest — bulk {stats['median_markup_bulk']}x, "
             f"premium {stats['median_markup_premium']}x, gummy {stats['median_markup_gummy']}x.")
lines.append(f"Biggest single markup: {stats['max_markup']}x ({stats['max_markup_product']}).")
lines.append(f"Gummies per day on the all-gummy stack: {stats['gummies_per_day_on_gummy_stack']}.")
lines.append("")
for c in df["compound"].unique():
    sub = df[df["compound"] == c].sort_values("cost_per_trial_dose")
    lo, hi = sub.iloc[0], sub.iloc[-1]
    lines.append(f"{c}: cheapest {lo['brand']} {lo['form']} ${lo['cost_per_trial_dose']:.3f}/day; "
                 f"priciest {hi['brand']} {hi['form']} ${hi['cost_per_trial_dose']:.3f}/day "
                 f"({hi['markup_vs_cheapest']:.1f}x).")
(OUT / "findings.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
print("\ncharts written to", CHARTS)
