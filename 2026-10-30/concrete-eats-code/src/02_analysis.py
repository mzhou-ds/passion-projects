"""Derived metrics from EDGAR annuals (year-keyed; no positional assumptions).

Alignment rules (documented, not hidden):
- MSFT fiscal year ends in June; its FY ending June of year Y is plotted
  in year Y. GOOGL/META end in December. NVDA ends in January; NVDA FY
  ending Jan of year Y mostly overlaps calendar year Y-1, so the capture
  ratio matches NVDA FY(Y) revenue against hyperscaler calendar (Y-1).
- Capex = cash paid for property and equipment. It includes land,
  buildings, power and network gear, not just GPUs: the NVDA ratio is a
  scale comparison, not a literal flow of dollars. NVDA also sells to
  buyers beyond these three hyperscalers.
- Combined totals use complete years only (all three hyperscalers present).
"""
import pandas as pd, numpy as np, json, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(HERE, "data", "edgar_annual.csv"))
HYPER = ["MSFT", "GOOGL", "META"]
df = df.sort_values(["ticker", "cal_year"]).reset_index(drop=True)
df["capex_intensity"] = df.capex / df.revenue
df["rnd_intensity"] = df.rnd / df.revenue
df["capex_over_rnd"] = df.capex / df.rnd
df["capex_over_depr"] = df.capex / df.depr
df["rev_growth_1yr"] = df.groupby("ticker").revenue.pct_change()
df["capex_growth_1yr"] = df.groupby("ticker").capex.pct_change()

# Year-keyed 3-yr productivity: (rev[y]-rev[y-3]) / capex[y-2..y]
prod = {}
for t, g in df.groupby("ticker"):
    by_year = g.set_index("cal_year")
    for y in by_year.index:
        if all(yy in by_year.index for yy in (y - 3, y - 2, y - 1, y)):
            prod[(t, y)] = (by_year.loc[y, "revenue"] - by_year.loc[y - 3, "revenue"]) / \
                           by_year.loc[[y - 2, y - 1, y], "capex"].sum()
df["rev_per_capex_3yr"] = [prod.get((t, y), np.nan) for t, y in zip(df.ticker, df.cal_year)]

# Sustained crossover: walk back from the latest year while capex > R&D
cross = {}
for t in HYPER:
    g = df[df.ticker == t].sort_values("cal_year")
    years = list(g.cal_year); over = list(g.capex_over_rnd > 1)
    start = years[-1]
    i = len(years) - 1
    while i >= 0 and over[i]:
        start = years[i]; i -= 1
    latest = g.iloc[-1]
    g19 = g[g.cal_year == 2019].iloc[0]
    cross[t] = {
        "sustained_crossover_year": int(start),
        "latest_year": int(latest.cal_year),
        "latest_capex": round(float(latest.capex), 1), "latest_rnd": round(float(latest.rnd), 1),
        "latest_ratio": round(float(latest.capex_over_rnd), 2),
        "capex_2019": round(float(g19.capex), 1),
        "capex_intensity_2019": round(float(g19.capex_intensity), 3),
        "capex_intensity_latest": round(float(latest.capex_intensity), 3),
        "capex_multiple_2019_to_latest": round(float(latest.capex / g19.capex), 2),
    }

# Combined, complete years only
piv = df[df.ticker.isin(HYPER)].pivot_table(index="cal_year", columns="ticker",
                                            values=["revenue", "rnd", "capex"], aggfunc="first")
complete = piv.dropna()
comb = pd.DataFrame({"cal_year": complete.index,
                     "revenue": complete["revenue"].sum(axis=1),
                     "rnd": complete["rnd"].sum(axis=1),
                     "capex": complete["capex"].sum(axis=1)})
comb["capex_over_rnd"] = comb.capex / comb.rnd

# NVDA capture
nv = df[df.ticker == "NVDA"][["cal_year", "revenue"]].rename(
    columns={"cal_year": "nvda_fy_end_year", "revenue": "nvda_revenue"})
cap = comb[["cal_year", "capex"]].rename(columns={"cal_year": "cal", "capex": "hyper_capex"})
m = nv.merge(cap, left_on=nv.nvda_fy_end_year - 1, right_on="cal", how="inner")
m["capture"] = m.nvda_revenue / m.hyper_capex

# Counterfactual: 2019-2020 mean productivity held, applied to latest 3-yr capex
cf = {}
for t in HYPER:
    g = df[df.ticker == t].set_index("cal_year")
    base = float(np.mean([prod[(t, y)] for y in (2019, 2020) if (t, y) in prod]))
    latest = int(g.index.max())
    window = [latest - 2, latest - 1, latest]
    actual = float(g.loc[latest, "revenue"] - g.loc[latest - 3, "revenue"])
    pred = base * float(g.loc[window, "capex"].sum())
    cf[t] = {"base_productivity_19_20": round(base, 3), "window": window,
             "actual_drev_3yr": round(actual, 1), "predicted_drev_3yr": round(pred, 1),
             "shortfall": round(pred - actual, 1),
             "latest_productivity": round(float(prod[(t, latest)]), 3),
             "productivity_change_pct": round(100 * (prod[(t, latest)] / base - 1), 1)}

out = {"crossover": cross, "combined": comb.round(1).to_dict("records"),
       "nvda_capture": m.round(3).to_dict("records"), "counterfactual": cf,
       "productivity_table": {str(y): {t: (None if (t, y) not in prod else round(float(prod[(t, y)]), 3))
                                       for t in HYPER}
                              for y in sorted(set(df.cal_year))}}
json.dump(out, open(os.path.join(HERE, "data", "summary.json"), "w"), indent=1)
df.to_csv(os.path.join(HERE, "data", "derived.csv"), index=False)
print(json.dumps(out, indent=1))
