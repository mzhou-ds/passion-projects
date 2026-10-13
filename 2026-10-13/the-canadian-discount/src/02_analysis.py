"""
02_analysis.py - turn raw pulls into the numbers the README quotes.

Outputs:
  data/annual_panel.csv   one row per year, both countries, ratios, drivers
  data/league_table.csv   provinces + US states ranked by GDP per capita (USD)
  data/findings.json      every headline number, generated not hand-typed
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
F = {}

# ------------------------------------------------------------------ IMF panel
imf = pd.read_csv(os.path.join(DATA, "imf_weo.csv"))
piv = imf.pivot_table(index="year", columns=["indicator", "country"], values="value")
piv.columns = [f"{a}_{b}" for a, b in piv.columns]
piv = piv.reset_index()

piv["ratio_nom"] = piv["NGDPDPC_CAN"] / piv["NGDPDPC_USA"]
piv["ratio_ppp"] = piv["PPPPC_CAN"] / piv["PPPPC_USA"]
piv["pop_growth_can"] = piv["LP_CAN"].pct_change() * 100
piv["pop_growth_usa"] = piv["LP_USA"].pct_change() * 100

# ------------------------------------------------------------------ FRED annual
fred = pd.read_csv(os.path.join(DATA, "fred_core.csv"), parse_dates=["date"])
fred["year"] = fred["date"].dt.year
ann = fred.groupby("year").agg(
    fx_cad_per_usd=("DEXCAUS", "mean"),
    oil_wti=("DCOILWTICO", "mean"),
    hp_can=("QCAN628BIS", "mean"),
    hp_usa=("QUSN628BIS", "mean"),
    unemp_can=("LRUNTTTTCAM156S", "mean"),
    unemp_usa=("UNRATE", "mean"),
    gdppc_const_can=("NYGDPPCAPKDCAN", "mean"),
    gdppc_const_usa=("NYGDPPCAPKDUSA", "mean"),
    popgrowth_wb_can=("SPPOPGROWCAN", "mean"),
    popgrowth_wb_usa=("SPPOPGROWUSA", "mean"),
).reset_index()
panel = piv.merge(ann, on="year", how="left")
panel = panel[(panel.year >= 2000) & (panel.year <= 2030)]
panel.to_csv(os.path.join(DATA, "annual_panel.csv"), index=False)

latest_fx_row = fred.dropna(subset=["DEXCAUS"]).iloc[-1]
F["fx_latest"] = {"date": str(latest_fx_row["date"].date()),
                  "cad_per_usd": round(float(latest_fx_row["DEXCAUS"]), 4)}

def at(year, col):
    row = panel[panel.year == year]
    return float(row[col].iloc[0]) if len(row) and pd.notna(row[col].iloc[0]) else None

F["ratio_nom"] = {y: round(at(y, "ratio_nom"), 4) for y in
                  [2000, 2005, 2010, 2011, 2012, 2015, 2019, 2020, 2022, 2024, 2025, 2030]}
F["ratio_ppp"] = {y: round(at(y, "ratio_ppp"), 4) for y in
                  [2000, 2010, 2019, 2024, 2025, 2030]}
F["gdppc_nom_usd"] = {y: {"can": round(at(y, "NGDPDPC_CAN")), "usa": round(at(y, "NGDPDPC_USA"))}
                      for y in [2011, 2019, 2024, 2030]}
peak_year = int(panel.loc[panel[panel.year <= 2025]["ratio_nom"].idxmax(), "year"])
F["nominal_peak"] = {"year": peak_year, "ratio": round(at(peak_year, "ratio_nom"), 4)}
F["fx_annual"] = {y: round(at(y, "fx_cad_per_usd"), 3) for y in [2011, 2015, 2019, 2024, 2025]}

# ------------------------------------------------- bigger, not richer (2019->2024)
wb = panel.dropna(subset=["gdppc_const_can", "gdppc_const_usa", "LP_CAN", "LP_USA"])
wb = wb[(wb.year >= 2019) & (wb.year <= 2024)].copy()
for c, C in [("can", "CAN"), ("usa", "USA")]:
    wb[f"real_gdp_idx_{c}"] = wb[f"gdppc_const_{c}"] * wb[f"LP_{C}"]
    wb[f"real_gdp_idx_{c}"] = wb[f"real_gdp_idx_{c}"] / wb[f"real_gdp_idx_{c}"].iloc[0] * 100
    wb[f"gdppc_idx_{c}"] = wb[f"gdppc_const_{c}"] / wb[f"gdppc_const_{c}"].iloc[0] * 100
wb.to_csv(os.path.join(DATA, "indexed_2019.csv"), index=False)
last = wb.iloc[-1]
F["bigger_not_richer_2019_2024"] = {
    "can_total_real_gdp_pct": round(float(last.real_gdp_idx_can - 100), 1),
    "can_gdppc_pct": round(float(last.gdppc_idx_can - 100), 1),
    "can_pop_pct": round(float((last["LP_CAN"] / wb.iloc[0]["LP_CAN"] - 1) * 100), 1),
    "usa_total_real_gdp_pct": round(float(last.real_gdp_idx_usa - 100), 1),
    "usa_gdppc_pct": round(float(last.gdppc_idx_usa - 100), 1),
    "usa_pop_pct": round(float((last["LP_USA"] / wb.iloc[0]["LP_USA"] - 1) * 100), 1),
}
# peak-to-latest per-capita slide within the window
F["can_gdppc_peak_year"] = int(wb.loc[wb.gdppc_const_can.idxmax(), "year"])
F["can_gdppc_from_peak_pct"] = round(float(
    (wb.iloc[-1].gdppc_const_can / wb.gdppc_const_can.max() - 1) * 100), 1)
# population surge years from World Bank growth rates
pg = panel.dropna(subset=["popgrowth_wb_can"])
F["pop_growth_can"] = {int(r.year): round(float(r.popgrowth_wb_can), 2)
                       for r in pg.itertuples() if 2021 <= r.year <= 2025}
F["pop_growth_usa_2023"] = round(at(2023, "popgrowth_wb_usa"), 2)

# ------------------------------------------------------------------ league table
gdp = pd.read_csv(os.path.join(DATA, "statcan_prov_gdp.csv"))
pop = pd.read_csv(os.path.join(DATA, "statcan_prov_pop.csv"))
prov = gdp.merge(pop, on=["year", "geo"])
prov = prov[~prov.geo.isin(["Canada", "Northwest Territories", "Nunavut", "Yukon"])]
prov["gdppc_cad"] = prov.gdp_m_cad * 1e6 / prov["pop"]
fx_by_year = ann.set_index("year")["fx_cad_per_usd"]
prov["gdppc_usd"] = prov.apply(lambda r: r.gdppc_cad / fx_by_year.get(r.year, np.nan), axis=1)

states = pd.read_csv(os.path.join(DATA, "fred_states.csv"), parse_dates=["date"])
states["year"] = states["date"].dt.year
gcol = [c for c in states.columns if c.endswith("NGSP")][0]  # placeholder, handled below
state_rows = []
for (st, yr), grp in states.groupby(["state", "year"]):
    g = grp[f"{st}NGSP"].dropna()
    p = grp[f"{st}POP"].dropna()
    if len(g) and len(p):
        state_rows.append({"year": yr, "geo": f"US-{st}", "kind": "state",
                           "gdppc_usd": float(g.iloc[0]) * 1e6 / (float(p.iloc[0]) * 1e3)})
sdf = pd.DataFrame(state_rows)

LY = 2024  # latest year common to provinces and states
league_prov = prov[prov.year == LY][["geo", "gdppc_cad", "gdppc_usd"]].copy()
league_prov["kind"] = "province"
league = pd.concat([league_prov[["geo", "kind", "gdppc_usd"]],
                    sdf[sdf.year == LY][["geo", "kind", "gdppc_usd"]]])
league = league.sort_values("gdppc_usd", ascending=False).reset_index(drop=True)
league.insert(0, "rank", league.index + 1)
league.to_csv(os.path.join(DATA, "league_table.csv"), index=False)
prov_only = league[league.kind == "province"]
F["league_year"] = LY
F["league"] = {
    "n_ranked": int(len(league)),
    "top": league.iloc[0]["geo"], "top_val": round(float(league.iloc[0].gdppc_usd)),
    "provinces": {r.geo: {"rank": int(r.rank), "gdppc_usd": round(float(r.gdppc_usd)),
                          "gdppc_cad": round(float(league_prov.set_index("geo").loc[r.geo, "gdppc_cad"]))}
                  for r in prov_only.itertuples()},
    "states_below_alberta": int((league[league.kind == "state"].gdppc_usd <
                                 prov_only.iloc[0].gdppc_usd).sum()) if len(prov_only) else None,
    "mississippi_gdppc": round(float(league[league.geo == "US-MS"].gdppc_usd.iloc[0])),
    "ontario_vs_mississippi_pct": round(float(
        league[league.geo == "Ontario"].gdppc_usd.iloc[0] /
        league[league.geo == "US-MS"].gdppc_usd.iloc[0] - 1) * 100, 1),
}

# ------------------------------------------------------------------ diaspora
dia = json.load(open(os.path.join(DATA, "diaspora.json")))
fx2020 = float(ann[ann.year == 2020].fx_cad_per_usd.iloc[0])
d = {"fx_2020_avg": round(fx2020, 3)}
try:
    stats = dia["canada_chinese_25_54"]
    for geo in ["Canada", "Toronto (CMA), Ont.", "Vancouver (CMA), B.C."]:
        med = stats[geo]["Median total income ($)"]
        d[geo] = {"chinese_cad": med["chinese"], "not_vismin_cad": med["not_vismin"],
                  "chinese_usd_at_2020_fx": round(med["chinese"] / fx2020)}
    d["us_asian_median_earnings_usd"] = dia["us"]["us_medearn_asian"]
    d["us_asian_median_hh_usd"] = dia["us"]["us_median_hh_asian"]
    # generation split for Canada, straight from the archived census extract
    base = os.path.join(HERE, "..", "..", "..", "2026-09-24",
                        "same-grandparents-different-deal", "data",
                        "statcan_income_filtered.csv")
    inc = pd.read_csv(base)
    m = (inc["GEO"] == "Canada") & (inc["Age (15B)"] == "25 to 54 years") & \
        (inc["Gender (3)"] == "Total - Gender") & \
        (inc["Income statistics (17)"] == "Median total income ($)") & \
        (inc["Highest certificate, diploma or degree (16)"].str.startswith("Total"))
    gens = {}
    for _, row in inc[m].iterrows():
        gens[row["Generation status (4)"]] = {"chinese_cad": row["Chinese[4]"],
                                              "not_vismin_cad": row["Not a visible minority[15]"]}
    d["canada_by_generation"] = gens
except Exception as e:
    d["error"] = str(e)
F["diaspora"] = d

json.dump(F, open(os.path.join(DATA, "findings.json"), "w"), indent=1)
print(json.dumps(F, indent=1))
