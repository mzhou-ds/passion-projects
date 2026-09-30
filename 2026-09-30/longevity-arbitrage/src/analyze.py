"""Run the Longevity Arbitrage analysis: key numbers + charts."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from model import (build_curves, load_evidence, hr_at, hr_to_years,
                   combined_hr, optimize_portfolio, marginal_roi_minutes)

plt.rcParams.update({"font.size": 11, "figure.dpi": 150,
                     "axes.grid": True, "grid.alpha": 0.25})

ev = load_evidence("data/evidence.csv")
curves = build_curves(ev)
MOD_COLORS = {"aerobic": "#2a7f62", "strength": "#b3541e", "vilpa": "#5b4e9e"}
MOD_LABELS = {"aerobic": "Aerobic (Arem 2015, n=661k)",
              "strength": "Strength (Momma 2022, 16 cohorts)",
              "vilpa": "Incidental vigorous bursts (Stamatakis 2022, device-measured)"}

# ---------------------------------------------------------------- key numbers
def key(label, **kw):
    print(f"{label}: " + "; ".join(f"{k}={v}" for k, v in kw.items()))

hr_a150 = float(hr_at(curves, "aerobic", 150))
hr_a450 = float(hr_at(curves, "aerobic", 450))
hr_s40 = float(hr_at(curves, "strength", 40))
hr_v32 = float(hr_at(curves, "vilpa", 32))
combo = float(combined_hr(curves, 600, 40, 0))

key("aerobic_150min/wk (meeting guidelines)", HR=round(hr_a150, 3),
    years=round(float(hr_to_years(hr_a150)), 2))
key("aerobic_450min/wk (3x guidelines)", HR=round(hr_a450, 3),
    years=round(float(hr_to_years(hr_a450)), 2))
key("strength_40min/wk (sweet spot)", HR=round(hr_s40, 3),
    years=round(float(hr_to_years(hr_s40)), 2))
key("vilpa_32min/wk (~4.5 min/day)", HR=round(hr_v32, 3),
    years=round(float(hr_to_years(hr_v32)), 2))
key("combo_aero600+strength40", HR=round(combo, 3),
    years=round(float(hr_to_years(combo)), 2),
    note="multiplicative estimate; Momma observed 0.60 directly")

for d in (0, 150, 300, 450):
    m = float(marginal_roi_minutes(curves, "aerobic", d))
    key(f"marginal_ROI_aerobic_at_{d}min", min_life_per_min_exercised=round(m, 1))
for d in (0, 40, 140):
    m = float(marginal_roi_minutes(curves, "strength", d))
    key(f"marginal_ROI_strength_at_{d}min", min_life_per_min_exercised=round(m, 1))
m_vil = float(marginal_roi_minutes(curves, "vilpa", 0))
key("marginal_ROI_vilpa_at_0min", min_life_per_min_exercised=round(m_vil, 1))

# ---------------------------------------------------------------- chart 1: dose-response
fig, ax = plt.subplots(figsize=(10, 6))
xs = np.linspace(0.5, 1700, 400)
ax.plot(xs, hr_at(curves, "aerobic", xs), color=MOD_COLORS["aerobic"], lw=2.5,
        label=MOD_LABELS["aerobic"])
ax.plot(np.linspace(0.5, 260, 200), hr_at(curves, "strength", np.linspace(0.5, 260, 200)),
        color=MOD_COLORS["strength"], lw=2.5, label=MOD_LABELS["strength"])
ax.plot(np.linspace(0.5, 60, 120), hr_at(curves, "vilpa", np.linspace(0.5, 60, 120)),
        color=MOD_COLORS["vilpa"], lw=2.5, label=MOD_LABELS["vilpa"])
# verified points
ax.scatter([150, 300, 450, 600], [0.80, 0.69, 0.63, 0.61],
           color=MOD_COLORS["aerobic"], zorder=5, s=40)
ax.scatter([40], [0.83], color=MOD_COLORS["strength"], zorder=5, s=40)
ax.scatter([16, 32], [0.75, 0.61], color=MOD_COLORS["vilpa"], zorder=5, s=40)
ax.axvline(150, ls="--", color="gray", lw=1)
ax.text(150, 0.98, "WHO minimum\n(150 min/wk)", ha="center", fontsize=9, color="gray")
ax.set_xscale("log"); ax.set_xlabel("Weekly exercise (min/week, log scale)")
ax.set_ylabel("Hazard ratio, all-cause mortality (vs inactive)")
ax.set_ylim(0.45, 1.05); ax.set_xlim(0.5, 1700)
ax.set_title("The dose-response: most of the money is made in the first hour")
ax.legend(fontsize=9, loc="lower left")
fig.tight_layout(); fig.savefig("charts/01_dose_response.png", bbox_inches="tight")

# ---------------------------------------------------------------- chart 2: marginal ROI
fig, ax = plt.subplots(figsize=(10, 6))
for mod in ("aerobic", "strength", "vilpa"):
    xm = curves["x_max"][mod]
    xs = np.linspace(0, xm * 0.98, 300)
    mroi = np.array([marginal_roi_minutes(curves, mod, d) for d in xs])
    ax.plot(xs, mroi, color=MOD_COLORS[mod], lw=2.5,
            label=f"{mod.capitalize()} — min of life expectancy per min exercised")
ax.set_yscale("log"); ax.set_xlabel("Current weekly dose (min/week)")
ax.set_ylabel("Marginal return: min of life per min of weekly exercise (log)")
ax.set_title("Marginal ROI collapses: the 8th weekly hour is worth a tenth of the 1st")
ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig("charts/02_marginal_roi.png", bbox_inches="tight")

# ---------------------------------------------------------------- chart 3: portfolio frontier (structured exercisers)
budgets = np.arange(20, 441, 20)
frontier = [optimize_portfolio(curves, int(b), structured=True) for b in budgets]
port = {"budget": [], "aerobic": [], "strength": [], "years": [], "hr": []}
for b, f in zip(budgets, frontier):
    port["budget"].append(int(b)); port["aerobic"].append(f["aerobic"])
    port["strength"].append(f["strength"])
    port["years"].append(f["years"]); port["hr"].append(f["hr"])
with open("output/frontier.json", "w") as fh:
    json.dump(port, fh, indent=1)

vilpa_years = float(hr_to_years(combined_hr(curves, 0, 0, 35.0)))  # the nonexerciser track

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
ax1.stackplot(budgets, port["strength"], port["aerobic"],
              labels=["Strength", "Aerobic"],
              colors=[MOD_COLORS["strength"], MOD_COLORS["aerobic"]], alpha=0.85)
ax1.set_ylabel("Optimal weekly allocation (min)")
ax1.set_title("The efficient frontier: where each minute of your budget should go")
ax1.legend(loc="upper left", fontsize=9)
ax2.plot(budgets, port["years"], color="#1f2937", lw=2.5, label="Optimal structured mix")
ax2.axhline(vilpa_years, ls="--", color=MOD_COLORS["vilpa"], lw=2,
            label=f"VILPA-only track: {vilpa_years:.1f} yr from ~35 min/wk (nonexercisers)")
ax2.set_xlabel("Weekly exercise budget (min/week)")
ax2.set_ylabel("Life expectancy gained (years vs inactive)")
ax2.set_title("Total payoff at the optimum")
ax2.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig("charts/03_portfolio_frontier.png", bbox_inches="tight")

for bb in (60, 120, 180, 300):
    f = optimize_portfolio(curves, bb, structured=True)
    key(f"optimal_{bb}min_budget", allocation=f"aero {f['aerobic']}/strength {f['strength']}",
        HR=round(f["hr"], 3), years=round(f["years"], 2))

# ---------------------------------------------------------------- chart 4: combo + sitting
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
labels = ["Aerobic\nonly", "Strength\nonly", "Combined\n(multiplicative est.)",
          "Combined\n(Momma observed)"]
vals = [float(hr_at(curves, "aerobic", 600)), float(hr_at(curves, "strength", 40)),
        combo, 0.60]
cols = ["#9db4a6", "#d9a06b", "#2a7f62", "#1d5c46"]
bars = ax.bar(labels, vals, color=cols)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", fontsize=11)
ax.axhline(1.0, ls="--", color="gray", lw=1)
ax.set_ylim(0, 1.25); ax.set_ylabel("All-cause mortality HR/RR")
ax.set_title("Aerobic + strength: the combo beats either alone")
ax2 = axes[1]
sit_labels = [">8h sitting\n+ inactive", "5+h TV/day\n(even if active)", "Active:\nsitting risk\nneutralized"]
sit_vals = [1.59, 1.16, 1.00]
sit_cols = ["#a33b3b", "#d98e4a", "#2a7f62"]
bars = ax2.bar(sit_labels, sit_vals, color=sit_cols)
for b, v in zip(bars, sit_vals):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.2f}", ha="center", fontsize=11)
ax2.axhline(1.0, ls="--", color="gray", lw=1)
ax2.set_ylim(0, 1.85); ax2.set_ylabel("HR, all-cause mortality")
ax2.set_title("The sitting tax (Ekelund 2016, n~1M)")
fig.suptitle("Stack the modalities; pay the sitting tax")
fig.tight_layout(); fig.savefig("charts/04_combo_effect.png", bbox_inches="tight")
print("charts + output written")
