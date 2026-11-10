"""Analysis for The Poppy Gap.

Reads data/country_table.csv + pageviews/trends CSVs, computes the
per-capita poppy economics, tests the casualty-rate hypothesis, and
produces the charts in charts/.

Headline test: does the poppy gap track WWI sacrifice (deaths per capita)?
Spoiler: it does not. New Zealand lost 1.6% of its population and wears
0.19 poppies per person; Canada lost 0.8% and wears 0.50. The variable
that lines up is whether 11 November stayed the country's *single* day
of remembrance (UK, Canada) or remembrance split across two days
(US: Memorial Day + Veterans Day; AU/NZ: Anzac Day + Remembrance Day).
"""
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#888888",
        "axes.labelcolor": "#222222",
        "figure.facecolor": "white",
    }
)

RED = "#C1272D"      # poppy red
DARK = "#1F1F1F"
GREY = "#8A8A8A"
BLUE = "#2E5A88"
GOLD = "#C99A2B"
TEAL = "#2E7D6B"

os.makedirs("charts", exist_ok=True)

# ---------------------------------------------------------------- country table
ct = pd.read_csv("data/country_table.csv")
ct["poppies_per_person"] = ct["poppies_millions"] / ct["population_millions_2024"]
ct["appeal_usd_per_person"] = ct["appeal_usd_millions"] / ct["population_millions_2024"]
ct["deaths_per_1000"] = ct["ww1_military_deaths"] / (ct["ww1_population_millions"] * 1000)
ct = ct.sort_values("poppies_per_person", ascending=False)
ct.to_csv("data/country_table_computed.csv", index=False)

print(ct[["country", "poppies_per_person", "appeal_usd_per_person", "deaths_per_1000"]].to_string(index=False))

# casualty hypothesis: correlation of deaths/1000 vs poppies/person
sub = ct.dropna(subset=["poppies_per_person"])
r = np.corrcoef(sub["deaths_per_1000"], sub["poppies_per_person"])[0, 1]
print(f"\ncorr(WWI deaths per 1,000, poppies per person) across {len(sub)} countries: r = {r:.2f}")
print("Canada vs US poppy ratio: "
      f"{ct.loc[ct.country=='Canada','poppies_per_person'].iloc[0] / ct.loc[ct.country=='United States','poppies_per_person'].iloc[0]:.1f}x")
print("Canada vs US appeal $/person ratio: "
      f"{ct.loc[ct.country=='Canada','appeal_usd_per_person'].iloc[0] / ct.loc[ct.country=='United States','appeal_usd_per_person'].iloc[0]:.1f}x")

# ---------------------------------------------------------------- chart 1: poppies per person
fig, ax = plt.subplots(figsize=(8.2, 4.6))
plot = ct.dropna(subset=["poppies_per_person"]).sort_values("poppies_per_person")
colors = [RED if c in ("Canada", "United Kingdom") else BLUE if c == "United States" else TEAL if c == "New Zealand" else GREY for c in plot["country"]]
ax.barh(plot["country"], plot["poppies_per_person"], color=colors, height=0.62)
for i, v in enumerate(plot["poppies_per_person"]):
    ax.text(v + 0.012, i, f"{v:.2f}", va="center", fontsize=11, color=DARK)
ax.set_xlim(0, 0.58)
ax.set_xlabel("Poppies distributed per person per year")
ax.set_title("One poppy for every two people — or one for every twenty-five",
             fontsize=13, fontweight="bold", loc="left", color=DARK)
ax.tick_params(axis="y", labelsize=11)
plt.tight_layout()
plt.savefig("charts/poppies_per_person.png", dpi=180)
plt.close()

# ---------------------------------------------------------------- chart 2: appeal dollars per person (USD)
fig, ax = plt.subplots(figsize=(8.2, 4.6))
plot = ct.dropna(subset=["appeal_usd_per_person"]).sort_values("appeal_usd_per_person")
colors = [RED if c in ("Canada", "United Kingdom") else BLUE for c in plot["country"]]
ax.barh(plot["country"], plot["appeal_usd_per_person"], color=colors, height=0.62)
for i, v in enumerate(plot["appeal_usd_per_person"]):
    ax.text(v + 0.02, i, f"${v:.2f}", va="center", fontsize=11, color=DARK)
ax.set_xlim(0, 1.12)
ax.set_xlabel("Poppy-appeal dollars raised per person per year (USD, 2024 avg FX)")
ax.set_title("The poppy economy, per person: Canada gives 9x the US",
             fontsize=13, fontweight="bold", loc="left", color=DARK)
plt.tight_layout()
plt.savefig("charts/appeal_dollars_per_person.png", dpi=180)
plt.close()

# ---------------------------------------------------------------- chart 3: casualty rate vs poppies (the failed hypothesis)
fig, ax = plt.subplots(figsize=(8.2, 5.0))
for _, row in sub.iterrows():
    c = RED if row["country"] in ("Canada", "United Kingdom") else BLUE if row["country"] == "United States" else TEAL
    ax.scatter(row["deaths_per_1000"], row["poppies_per_person"], s=260, color=c, zorder=3)
    ax.annotate(row["country"], (row["deaths_per_1000"], row["poppies_per_person"]),
                xytext=(8, 8), textcoords="offset points", fontsize=11, color=DARK)
ax.set_xlabel("WWI military deaths per 1,000 people (1914 population)")
ax.set_ylabel("Poppies distributed per person per year")
ax.set_title("Sacrifice does not explain the poppy gap (r = %.2f)" % r,
             fontsize=13, fontweight="bold", loc="left", color=DARK)
ax.set_xlim(0, 22)
ax.set_ylim(0, 0.58)
plt.tight_layout()
plt.savefig("charts/casualty_vs_poppy.png", dpi=180)
plt.close()

# ---------------------------------------------------------------- chart 4: pageviews, Nov window (daily)
pv = pd.read_csv("data/pageviews_daily_2025.csv", parse_dates=["date"])
nov = pv[(pv["date"] >= "2025-10-20") & (pv["date"] <= "2025-11-20")]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
for art, color, ls in [("Remembrance Day", RED, "-"), ("Veterans Day", BLUE, "-"),
                       ("Remembrance poppy", GOLD, "--")]:
    s = nov[nov["article"] == art].set_index("date")["views"]
    ax.plot(s.index, s.values, color=color, ls=ls, lw=2, label=art)
ax.axvline(pd.Timestamp("2025-11-11"), color=GREY, lw=1, ls=":")
ax.text(pd.Timestamp("2025-11-11"), ax.get_ylim()[1] * 0.92, "  11 Nov",
        fontsize=10, color=GREY)
ax.set_ylabel("Daily Wikipedia pageviews (global, all devices)")
ax.set_title("11 November belongs to both — but only one article is about a flower",
             fontsize=13, fontweight="bold", loc="left", color=DARK)
ax.legend(frameon=False, loc="upper left")
ax.set_yscale("log")
plt.tight_layout()
plt.savefig("charts/pageviews_nov2025.png", dpi=180)
plt.close()

# Nov 11 totals, for the README
d11 = pv[pv["date"] == "2025-11-11"].set_index("article")["views"]
print("\nNov 11, 2025 pageviews:")
print(d11.to_string())

# ---------------------------------------------------------------- chart 5: monthly attention shape 2025
m = pd.read_csv("data/pageviews_monthly_2025.csv", parse_dates=["date"])
m = m[m["date"] < "2025-12-01"]  # Dec is a partial month in the pull
fig, ax = plt.subplots(figsize=(8.6, 4.8))
months = pd.date_range("2025-01-01", periods=11, freq="MS")
for art, color in [("Anzac Day", TEAL), ("Memorial Day", GOLD),
                   ("Remembrance Day", RED), ("Veterans Day", BLUE)]:
    s = m[m["article"] == art].set_index("date")["views"].reindex(months)
    ax.plot(s.index, s.values, color=color, lw=2, marker="o", ms=4, label=art)
ax.set_ylabel("Monthly Wikipedia pageviews (global)")
ax.set_title("Each country spikes on its own day — the US spikes twice",
             fontsize=13, fontweight="bold", loc="left", color=DARK)
ax.legend(frameon=False, loc="upper left")
ax.set_yscale("log")
ax.set_xticks(months)
ax.set_xticklabels([d.strftime("%b") for d in months])
plt.tight_layout()
plt.savefig("charts/pageviews_monthly_2025.png", dpi=180)
plt.close()

# peak-month shares, for the README
piv = m.pivot_table(index="article", columns="date", values="views", aggfunc="sum")
for art in ["Anzac Day", "Memorial Day", "Remembrance Day", "Veterans Day"]:
    row = piv.loc[art]
    print(f"{art}: peak {row.idxmax().strftime('%b')} {int(row.max()):,} views; "
          f"peak share of year {row.max()/row.sum()*100:.0f}%")
print("\ncharts written.")
