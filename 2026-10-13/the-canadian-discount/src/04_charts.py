"""
04_charts.py - figures for the README, plus the interactive site's data.js.
Run after 02_analysis.py and 03_model.py.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CH = os.path.join(HERE, "..", "charts")
SITE = os.path.join(HERE, "..", "site")
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "grid.linestyle": "--"})
CAN, USA = "#d80621", "#1f4e79"  # flag red / deep blue

panel = pd.read_csv(os.path.join(DATA, "annual_panel.csv"))
F = json.load(open(os.path.join(DATA, "findings.json")))
M = json.load(open(os.path.join(DATA, "model.json")))

# 1 ---------------------------------------------------------------- the canyon
fig, ax = plt.subplots(figsize=(9, 4.6))
hist = panel[panel.year <= 2025]
fcst = panel[panel.year >= 2025]
for col, color, label in [("ratio_nom", CAN, "Nominal (market FX)"),
                          ("ratio_ppp", USA, "PPP (real, FX stripped out)")]:
    ax.plot(hist.year, hist[col] * 100, color=color, lw=2.2, label=label)
    ax.plot(fcst.year, fcst[col] * 100, color=color, lw=2.2, ls="--")
ax.axvspan(2025, 2030, color="grey", alpha=0.08)
ax.text(2027.5, 97, "IMF forecast", ha="center", fontsize=9, color="grey")
ax.axhline(100, color="k", lw=0.7)
pk = F["nominal_peak"]
ax.annotate(f"{pk['year']}: {pk['ratio']*100:.0f}c on the dollar",
            (pk["year"], pk["ratio"] * 100), textcoords="offset points",
            xytext=(8, 6), fontsize=9)
ax.annotate(f"2024: {F['ratio_nom']['2024']*100:.0f}c nominal, "
            f"{F['ratio_ppp']['2024']*100:.0f}c PPP",
            (2024, F["ratio_ppp"]["2024"] * 100), textcoords="offset points",
            xytext=(-150, -26), fontsize=9)
ax.set_ylabel("Canadian GDP per capita, cents per US $1")
ax.set_title("The canyon: Canada's income per person as a share of America's")
ax.legend(frameon=False, loc="lower left")
fig.tight_layout(); fig.savefig(f"{CH}/canyon.png"); plt.close(fig)

# 2 ------------------------------------------------------- bigger, not richer
wb = pd.read_csv(os.path.join(DATA, "indexed_2019.csv"))
fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
for ax, c, name in [(axes[0], "can", "Canada"), (axes[1], "usa", "United States")]:
    ax.plot(wb.year, wb[f"real_gdp_idx_{c}"], color=CAN if c == "can" else USA,
            lw=2.2, label="Total real GDP")
    ax.plot(wb.year, wb[f"gdppc_idx_{c}"], color="k", lw=2.2, ls="--",
            label="Real GDP per person")
    ax.axhline(100, color="grey", lw=0.7)
    ax.set_title(name); ax.legend(frameon=False, fontsize=8.5)
axes[0].set_ylabel("Index, 2019 = 100")
fig.suptitle("Bigger, not richer: the whole economy grew, the average person shrank")
fig.tight_layout(); fig.savefig(f"{CH}/bigger_not_richer.png"); plt.close(fig)

# 3 ------------------------------------------------------------- league table
league = pd.read_csv(os.path.join(DATA, "league_table.csv"))
focus_states = ["US-DC", "US-ND", "US-NY", "US-CA", "US-WA", "US-TX", "US-FL", "US-MS"]
sel = league[(league.kind == "province") | (league.geo.isin(focus_states))]
sel = sel.sort_values("gdppc_usd")
fig, ax = plt.subplots(figsize=(9, 5.6))
colors = [CAN if k == "province" else "#9db8d2" for k in sel.kind]
ax.barh(sel.geo.str.replace("US-", ""), sel.gdppc_usd / 1000, color=colors)
for i, (v, r) in enumerate(zip(sel.gdppc_usd, sel["rank"])):
    ax.text(v / 1000 + 1, i, f"${v/1000:.0f}k  (#{int(r)} of {len(league)})",
            va="center", fontsize=8.5)
ax.set_xlabel("GDP per capita, 2024, thousand US$ (provinces converted at 2024 avg FX)")
ax.set_title("The league table: every Canadian province vs selected US states\n"
             "(red = province)")
ax.set_xlim(0, sel.gdppc_usd.max() / 1000 * 1.28)
fig.tight_layout(); fig.savefig(f"{CH}/league.png"); plt.close(fig)

# 4 ----------------------------------------------------------------- drivers
fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True)
h = panel[(panel.year >= 2000) & (panel.year <= 2025)]
axes[0].plot(h.year, h.ratio_nom * 100, color=CAN, lw=2.2, label="Nominal ratio (%)")
ax2 = axes[0].twinx()
ax2.plot(h.year, h.fx_cad_per_usd, color="grey", lw=1.6, ls="--", label="CAD per USD")
ax2.set_ylabel("CAD per USD", color="grey")
axes[0].set_ylabel("cents per $1")
axes[0].set_title("The discount tracks the loonie, and the loonie tracks oil")
axes[1].plot(h.year, h.oil_wti, color="#b58900", lw=2)
axes[1].set_ylabel("WTI, US$/bbl (annual avg)")
fig.tight_layout(); fig.savefig(f"{CH}/drivers.png"); plt.close(fig)

# 5 -------------------------------------------------------------------- SHAP
fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
labels = {"d_log_fx": "FX move", "d_log_oil": "Oil move", "popgrowth_diff": "Pop growth gap",
          "hp_growth_diff": "House-price growth gap", "unemp_diff": "Unemployment gap"}
for ax, target, title in [(axes[0], "d_log_ratio_ppp", "Real (PPP) gap"),
                          (axes[1], "d_log_ratio_nom", "Lived (nominal) gap")]:
    imp = M["models"][target]["shap_mean_abs"]
    items = sorted(imp.items(), key=lambda kv: kv[1])
    ax.barh([labels[k] for k, _ in items], [v for _, v in items],
            color=USA if target.endswith("ppp") else CAN)
    ax.set_title(f"SHAP importance: {title}", fontsize=10)
    ax.set_xlabel("mean |SHAP|, log pts/yr")
fig.suptitle("What moves the gap year to year (XGBoost, 2001-2024)")
fig.tight_layout(); fig.savefig(f"{CH}/shap.png"); plt.close(fig)

# 6 ----------------------------------------------------------------- diaspora
d = F["diaspora"]
names = ["Canada\nChinese 25-54", "Toronto\nChinese 25-54", "Vancouver\nChinese 25-54",
         "Canada 2nd gen\nChinese 25-54", "United States\nAsian median earnings"]
vals = [d["Canada"]["chinese_usd_at_2020_fx"], d["Toronto (CMA), Ont."]["chinese_usd_at_2020_fx"],
        d["Vancouver (CMA), B.C."]["chinese_usd_at_2020_fx"],
        round(d["canada_by_generation"]["Second generation"]["chinese_cad"] / d["fx_2020_avg"]),
        d["us_asian_median_earnings_usd"]]
fig, ax = plt.subplots(figsize=(9, 4.4))
bars = ax.bar(names, np.array(vals) / 1000, color=[CAN, CAN, CAN, "#7a0c1d", USA])
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v / 1000 + 1.2, f"${v/1000:.1f}k",
            ha="center", fontsize=9)
ax.set_ylabel("Median income, thousand US$ (Canada converted at 2020 avg FX 1.34)")
ax.set_title("The discount is personal: Chinese diaspora medians, Canada vs the US\n"
             "(Census 2021 income yr 2020 vs ACS 2023 median earnings, workers)")
fig.tight_layout(); fig.savefig(f"{CH}/diaspora.png"); plt.close(fig)

# ------------------------------------------------------------------ site data
row2024 = panel[panel.year == 2024].iloc[0]
site_data = {
    "fx_latest": F["fx_latest"],
    # IMF-implied PPP conversion factor for Canada, 2024:
    # nominal GDP pc in CAD divided by PPP GDP pc in international dollars.
    "ppp_factor_2024": round(float(row2024.NGDPDPC_CAN * row2024.fx_cad_per_usd
                                   / row2024.PPPPC_CAN), 4),
    "fx_2011_avg": round(float(panel[panel.year == 2011].iloc[0].fx_cad_per_usd), 4),
    "ratio_nom_2024": F["ratio_nom"]["2024"],
    "ratio_ppp_2024": F["ratio_ppp"]["2024"],
    "ratio_nom_2011": F["ratio_nom"]["2011"],
    "gdppc_2024": F["gdppc_nom_usd"]["2024"],
    "league": league[league.kind == "province"][["geo", "gdppc_usd", "rank"]]
              .to_dict("records"),
    "series": panel[(panel.year >= 2000) & (panel.year <= 2030)][
        ["year", "ratio_nom", "ratio_ppp"]].dropna().to_dict("records"),
}
with open(os.path.join(SITE, "data.js"), "w") as f:
    f.write("window.SITE_DATA = " + json.dumps(site_data, indent=1) + ";\n")
print("charts + site data done:", os.listdir(CH))
