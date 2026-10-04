#!/usr/bin/env python3
"""The Mother-Tongue Half-Life — analysis.

Canada: StatCan 2021 Census table 98-10-0325-01 extract (data/statcan_cma_mothertongue.csv)
US: ACS 2023 5-year (data/acs_chinese_language.json)

Parts: 1) generational retention + exponential-decay fits, 2) CMA market table,
3) kids' transmission, 4) US metro structure, 5) KMeans diaspora archetypes,
6) 2021->2051 projections under immigration-refill scenarios.
Outputs data/findings.json, charts/*.png, site/data.js
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
GEN_YEARS = 27.5  # average generation length, stated assumption
LANGS = {"Chinese languages": "Chinese (all)", "Mandarin": "Mandarin", "Yue (Cantonese)": "Cantonese"}

ca = pd.read_csv(PROJ / "data/statcan_cma_mothertongue.csv")
us = json.load(open(PROJ / "data/acs_chinese_language.json"))["2023"]

def cell(geo, gen, age, mt, vismin="Chinese"):
    r = ca[(ca.geo == geo) & (ca.generation == gen) & (ca.age == age)
           & (ca.mother_tongue == mt) & (ca.vismin == vismin)]
    return float(r.total.iloc[0]) if len(r) else 0.0

GEOS = ["Canada", "Toronto (CMA), Ont.", "Vancouver (CMA), B.C.", "Montréal (CMA), Que.",
        "Calgary (CMA), Alta.", "Edmonton (CMA), Alta.", "Ottawa - Gatineau (CMA), Ont./Que.",
        "Winnipeg (CMA), Man."]
SHORT = {"Canada": "Canada", "Toronto (CMA), Ont.": "Toronto", "Vancouver (CMA), B.C.": "Vancouver",
         "Montréal (CMA), Que.": "Montreal", "Calgary (CMA), Alta.": "Calgary",
         "Edmonton (CMA), Alta.": "Edmonton", "Ottawa - Gatineau (CMA), Ont./Que.": "Ottawa-Gatineau",
         "Winnipeg (CMA), Man.": "Winnipeg"}
GENS = ["First generation", "Second generation", "Third generation or more"]

# ---------- 1) retention + decay fits ----------
def retention_table(geo):
    out = {}
    for mt in LANGS:
        shares, pops = [], []
        for g in GENS:
            pop = cell(geo, g, "Total - Age", "Total - Mother tongue")
            shares.append(cell(geo, g, "Total - Age", mt) / pop if pop else 0.0)
            pops.append(pop)
        out[mt] = {"shares": shares, "pop_by_gen": pops}
    return out

def decay_fit(shares):
    x = np.arange(3.0)
    slope, _ = np.polyfit(x, np.log(np.maximum(shares, 1e-6)), 1)
    r = float(np.exp(slope))
    return {"r_per_gen": round(r, 3),
            "halflife_gens": round(float(np.log(0.5) / np.log(r)), 2) if r < 1 else None,
            "halflife_years": round(float(np.log(0.5) / np.log(r)) * GEN_YEARS, 1) if r < 1 else None,
            "r12": round(shares[1] / shares[0], 3) if shares[0] else None,
            "r23": round(shares[2] / shares[1], 3) if shares[1] else None}

nat = retention_table("Canada")
findings = {"canada_retention": {LANGS[m]: {"shares_pct": [round(100 * s, 1) for s in v["shares"]],
                                            **decay_fit(v["shares"])} for m, v in nat.items()},
            "canada_pop_by_gen": [int(x) for x in nat["Chinese languages"]["pop_by_gen"]]}

# ---------- 2) CMA table + 3) kids transmission ----------
cma_rows = []
for geo in GEOS:
    rt = retention_table(geo)
    chinese = rt["Chinese languages"]
    speakers = sum(cell(geo, g, "Total - Age", "Chinese languages") for g in GENS)
    total_pop = cell(geo, "Total - Generation status", "Total - Age", "Total - Mother tongue",
                     vismin="Total - Visible minority")
    gen1_spk = cell(geo, "First generation", "Total - Age", "Chinese languages")
    yue = sum(cell(geo, g, "Total - Age", "Yue (Cantonese)") for g in GENS)
    kids_pop = cell(geo, "Second generation", "0 to 14 years", "Total - Mother tongue")
    kids_mt = cell(geo, "Second generation", "0 to 14 years", "Chinese languages")
    gen2_pop = cell(geo, "Second generation", "Total - Age", "Total - Mother tongue")
    gen2_mt = cell(geo, "Second generation", "Total - Age", "Chinese languages")
    gen3_pop = cell(geo, "Third generation or more", "Total - Age", "Total - Mother tongue")
    gen3_mt = cell(geo, "Third generation or more", "Total - Age", "Chinese languages")
    cma_rows.append({
        "geo": SHORT[geo], "speakers": int(speakers), "per_1k": round(1000 * speakers / total_pop, 1),
        "cantonese_share_pct": round(100 * yue / speakers, 1),
        "gen1_share_of_speakers_pct": round(100 * gen1_spk / speakers, 1),
        "gen2_retention_pct": round(100 * chinese["shares"][1], 1),
        "kids_transmission_pct": round(100 * kids_mt / kids_pop, 1) if kids_pop else None,
        "lapsed_gen2": int(gen2_pop - gen2_mt), "lapsed_gen3": int(gen3_pop - gen3_mt),
        "halflife_years": decay_fit(chinese["shares"])["halflife_years"]})
findings["cma_table"] = cma_rows

# ---------- 4) US metros ----------
us_rows = []
for name, v in us.items():
    born = v["born_china"] + v["born_hk"] + v["born_tw"]
    us_rows.append({"geo": name, "speakers": v["chinese"], "per_1k": round(1000 * v["chinese"] / v["pop"], 1),
                    "lep_share_pct": round(100 * v["chinese_less"] / v["chinese"], 1),
                    "lep_people": v["chinese_less"], "born_region": born,
                    "speakers_per_born": round(v["chinese"] / born, 2),
                    "hk_share_born_pct": round(100 * v["born_hk"] / born, 1)})
us_rows.sort(key=lambda r: -r["speakers"])
findings["us_table"] = us_rows
findings["us_national"] = next(r for r in us_rows if r["geo"] == "United States")

# ---------- 5) KMeans archetypes (CA CMAs + US metros, harmonized features) ----------
feat = []
for r in cma_rows:
    if r["geo"] == "Canada":
        continue
    feat.append({"geo": r["geo"], "country": "CA", "per_1k": r["per_1k"],
                 "cantonese_ness": r["cantonese_share_pct"], "firstgen_intensity": r["gen1_share_of_speakers_pct"],
                 "log_speakers": float(np.log10(r["speakers"]))})
for r in us_rows:
    if r["geo"] == "United States":
        continue
    feat.append({"geo": r["geo"], "country": "US", "per_1k": r["per_1k"],
                 "cantonese_ness": r["hk_share_born_pct"], "firstgen_intensity": r["lep_share_pct"],
                 "log_speakers": float(np.log10(r["speakers"]))})
fdf = pd.DataFrame(feat)
X = StandardScaler().fit_transform(fdf[["per_1k", "cantonese_ness", "firstgen_intensity", "log_speakers"]])
best = max(((silhouette_score(X, KMeans(k, n_init=20, random_state=7).fit_predict(X)), k)
            for k in range(2, 6)))
k = best[1]
fdf["cluster"] = KMeans(k, n_init=20, random_state=7).fit_predict(X)
cent = fdf.groupby("cluster")[["per_1k", "cantonese_ness", "firstgen_intensity", "log_speakers"]].mean().round(1)
findings["archetypes"] = {"k": int(k), "silhouette": round(float(best[0]), 3),
                          "members": {str(int(c)): sorted(fdf[fdf.cluster == c].geo) for c in sorted(fdf.cluster.unique())},
                          "centroids": {str(int(i)): cent.loc[i].to_dict() for i in cent.index}}
fdf.to_csv(PROJ / "data/archetype_features.csv", index=False)

# ---------- 6) projections 2021-2051 ----------
# stock(y+1) = stock(y) * (1-loss_lang) + inflow_geo_lang ; loss from national per-gen r
nat_lang_share_2021 = {LANGS[m]: sum(cell("Canada", g, "Total - Age", m) for g in GENS) for m in LANGS}
lang_loss = {}
for m in LANGS:
    r = np.exp(np.polyfit(np.arange(3.0), np.log(np.maximum(nat[m]["shares"], 1e-6)), 1)[0])
    lang_loss[LANGS[m]] = 1 - r ** (1 / GEN_YEARS)
gen1_mix = {LANGS[m]: cell("Canada", "First generation", "Total - Age", m) for m in LANGS}
mix_sum = sum(gen1_mix.values())
gen1_mix = {k2: v / mix_sum for k2, v in gen1_mix.items()}
SCEN = {"low": 15000, "base": 30000, "high": 45000}  # net new Chinese-MT immigrants/yr, Canada

proj = {}
for geo in ["Toronto (CMA), Ont.", "Vancouver (CMA), B.C.", "Edmonton (CMA), Alta.", "Canada"]:
    proj[SHORT[geo]] = {}
    geo_share = (sum(cell(geo, g, "Total - Age", "Chinese languages") for g in GENS)
                 / nat_lang_share_2021["Chinese (all)"])
    for m in LANGS:
        stock0 = sum(cell(geo, g, "Total - Age", m) for g in GENS)
        series = {}
        for scen, inflow_nat in SCEN.items():
            inflow = inflow_nat * (geo_share if geo != "Canada" else 1.0) * gen1_mix[LANGS[m]]
            s, ys = stock0, [round(stock0)]
            for _ in range(30):
                s = s * (1 - lang_loss[LANGS[m]]) + inflow
                ys.append(round(s))
            series[scen] = ys
        proj[SHORT[geo]][LANGS[m]] = {"2021": int(stock0), "series": series}
findings["projections_meta"] = {"gen_years": GEN_YEARS, "scenarios_per_year": SCEN,
                                "annual_loss_pct": {k2: round(100 * v, 2) for k2, v in lang_loss.items()}}
# Edmonton crossover (base scenario): year Mandarin stock passes Cantonese
edm = proj["Edmonton"]
cross = next((2021 + i for i, (a, b) in enumerate(
    zip(edm["Mandarin"]["series"]["base"], edm["Cantonese"]["series"]["base"])) if a > b), None)
findings["edmonton_crossover_year"] = cross

json.dump(findings, open(PROJ / "data/findings.json", "w"), indent=1)
with open(PROJ / "site/data.js", "w") as f:
    f.write("const PROJ = " + json.dumps(proj) + ";\n")
    f.write("const FIND = " + json.dumps(findings) + ";\n")

# ---------- charts ----------
plt.rcParams.update({"figure.dpi": 150, "font.size": 9})
# 1 retention decay
fig, ax = plt.subplots(figsize=(7, 4))
for m, style in zip(LANGS, ["o-", "s-", "^-"]):
    ax.plot([1, 2, 3], [100 * s for s in nat[m]["shares"]], style, label=LANGS[m])
ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["1st gen", "2nd gen", "3rd gen+"])
ax.set_ylabel("% of generation with Chinese mother tongue")
ax.set_title("Canada: the mother-tongue cliff by generation (2021 Census)")
ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(PROJ / "charts/retention_decay.png"); plt.close(fig)
# 2 CMA cantonese vs gen2 retention
c = [r for r in cma_rows if r["geo"] != "Canada"]
fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter([r["cantonese_share_pct"] for r in c], [r["gen2_retention_pct"] for r in c],
           s=[r["speakers"] / 800 for r in c])
for r in c:
    ax.annotate(r["geo"], (r["cantonese_share_pct"], r["gen2_retention_pct"]), fontsize=8, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Cantonese share of Chinese mother-tongue speakers (%)")
ax.set_ylabel("2nd-generation retention (%)")
ax.set_title("Where Cantonese is the heritage language, it sticks (bubble = speakers)")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(PROJ / "charts/cma_cantonese.png"); plt.close(fig)
# 3 US metros
u = [r for r in us_rows if r["geo"] != "United States"]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.scatter([r["per_1k"] for r in u], [r["lep_share_pct"] for r in u], s=[r["speakers"] / 4000 for r in u])
for r in u:
    ax.annotate(r["geo"], (r["per_1k"], r["lep_share_pct"]), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Chinese speakers per 1,000 residents")
ax.set_ylabel("% of Chinese speakers who speak English less than 'very well'")
ax.set_title("US metros: density vs. language-need (ACS 2023, bubble = speakers)")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(PROJ / "charts/us_metros.png"); plt.close(fig)
# 4 archetypes
fig, ax = plt.subplots(figsize=(7, 4.5))
for cl, sub in fdf.groupby("cluster"):
    ax.scatter(sub.per_1k, sub.cantonese_ness, s=sub.log_speakers * 30, label=f"cluster {cl}")
    for _, r in sub.iterrows():
        ax.annotate(r.geo, (r.per_1k, r.cantonese_ness), fontsize=7, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Chinese speakers per 1,000 residents")
ax.set_ylabel("Cantonese-ness (CA: Yue share of speakers; US: HK-born share)")
ax.set_title("Diaspora market archetypes, Canada + US")
ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(PROJ / "charts/archetypes.png"); plt.close(fig)
# 5 projections
fig, axes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=False)
for ax, gname in zip(axes, ["Toronto", "Vancouver", "Edmonton"]):
    years = range(2021, 2052)
    for lang, color in [("Mandarin", "#c0392b"), ("Cantonese", "#2471a3")]:
        s = proj[gname][lang]["series"]
        ax.plot(years, s["base"], color=color, label=lang)
        ax.fill_between(years, s["low"], s["high"], color=color, alpha=.15)
    ax.set_title(gname); ax.grid(alpha=.3)
axes[0].set_ylabel("mother-tongue speakers"); axes[0].legend()
fig.suptitle("Projection to 2051 (base line, low-high refill band)")
fig.tight_layout(); fig.savefig(PROJ / "charts/projections.png"); plt.close(fig)
# 6 halflife bars
fig, ax = plt.subplots(figsize=(7, 3.6))
rows = [r for r in cma_rows if r["halflife_years"]]
ax.barh([r["geo"] for r in rows], [r["halflife_years"] for r in rows])
ax.set_xlabel("mother-tongue half-life (years, generational-decay model)")
ax.set_title("How fast the Chinese-language market halves, by city")
fig.tight_layout(); fig.savefig(PROJ / "charts/halflife.png"); plt.close(fig)

print(json.dumps(findings, indent=1)[:4000])
