#!/usr/bin/env python3
"""Analyze raw data and produce charts + findings for the 49th Parallel project."""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw"
CHARTS = BASE / "charts"
DATA = BASE / "data"
CHARTS.mkdir(exist_ok=True)

CAN = "#D52B1E"   # Canadian red
USA = "#3C3B6E"   # US navy
GREY = "#8a8a8a"
GOLD = "#c9a227"

plt.rcParams.update({
    "figure.dpi": 130, "font.size": 11, "axes.titlesize": 13,
    "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.autolayout": True, "font.family": "DejaVu Sans",
})
FINDINGS = {}


def despine(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ============ 1. World Bank: Canada vs USA ============
def wb_series(code_name):
    d = json.loads((RAW / f"wb_{code_name}.json").read_text())
    rows = d[1]
    out = {"CAN": {}, "USA": {}}
    for r in rows:
        if r["value"] is None:
            continue
        iso = r["countryiso3code"]
        if iso in out:
            out[iso][int(r["date"])] = float(r["value"])
    return out


def wb_chart(name, ylabel, title, fname, pct=False):
    s = wb_series(name)
    years = sorted(set(s["CAN"]) & set(s["USA"]))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(years, [s["CAN"][y] for y in years], color=CAN, lw=2.5, label="Canada")
    ax.plot(years, [s["USA"][y] for y in years], color=USA, lw=2.5, label="United States")
    ax.set_ylabel(ylabel); ax.set_title(title); ax.legend(frameon=False)
    despine(ax)
    fig.savefig(CHARTS / fname, bbox_inches="tight")
    plt.close(fig)
    return s, years


s_le, yrs = wb_chart("life_expectancy", "Years",
                     "Life expectancy at birth: Canada vs the United States (1990–2023)",
                     "life_expectancy.png")
gap = s_le["CAN"][2023] - s_le["USA"][2023]
FINDINGS["life_expectancy_gap_2023"] = round(gap, 2)
FINDINGS["life_expectancy"] = {"CAN_2023": round(s_le["CAN"][2023], 1), "USA_2023": round(s_le["USA"][2023], 1)}

s_he, _ = wb_chart("health_exp_gdp", "% of GDP",
                   "Current health expenditure as % of GDP (2000–2022)",
                   "health_spending.png")
FINDINGS["health_exp_gdp_latest"] = {
    "CAN": round(s_he["CAN"][max(s_he["CAN"])], 1),
    "USA": round(s_he["USA"][max(s_he["USA"])], 1),
}

s_hom, _ = wb_chart("homicide_rate", "Deaths per 100,000 people",
                    "Intentional homicide rate (1990–2023)",
                    "homicide_rate.png")
FINDINGS["homicide_rate_latest"] = {
    "CAN": round(s_hom["CAN"][max(s_hom["CAN"])], 2),
    "USA": round(s_hom["USA"][max(s_hom["USA"])], 2),
}

s_gini, _ = wb_series("gini"), None
FINDINGS["gini_latest"] = {
    "CAN": round(s_gini["CAN"][max(s_gini["CAN"])], 1),
    "USA": round(s_gini["USA"][max(s_gini["USA"])], 1),
}
s_mig, _ = wb_series("migrant_stock"), None
s_pop, _ = wb_series("population"), None
y = max(set(s_mig["CAN"]) & set(s_pop["CAN"]))
FINDINGS["migrant_share_latest"] = {
    "CAN": round(100 * s_mig["CAN"][y] / s_pop["CAN"][y], 1),
    "USA": round(100 * s_mig["USA"][y] / s_pop["USA"][y], 1),
    "year": y,
}
s_gdp, _ = wb_series("gdp_per_capita"), None
FINDINGS["gdp_per_capita_latest"] = {
    "CAN": round(s_gdp["CAN"][max(s_gdp["CAN"])]),
    "USA": round(s_gdp["USA"][max(s_gdp["USA"])]),
}
print("WB findings:", json.dumps(FINDINGS, indent=1))


# ============ 2. NHL draft nationality ============
draft = {}
for year in range(2000, 2026):
    d = json.loads((RAW / f"nhl_draft_{year}.json").read_text())
    draft[year] = d["data"]

years = sorted(draft)
cats = ["CAN", "USA", "OTHER"]
shares = {c: [] for c in cats}
first_round_can, first_round_usa = [], []
n_picks = 0
for y in years:
    picks = draft[y]
    n_picks += len(picks)
    c = Counter((p.get("countryCode") or "OTHER") for p in picks)
    tot = sum(c.values())
    shares["CAN"].append(100 * c["CAN"] / tot)
    shares["USA"].append(100 * c["USA"] / tot)
    shares["OTHER"].append(100 * (tot - c["CAN"] - c["USA"]) / tot)
    fr = [p for p in picks if p.get("pickInRound") is not None and p.get("overallPickNumber", 999) <= 32]
    if not fr:
        fr = picks[:32]
    fc = Counter((p.get("countryCode") or "OTHER") for p in fr)
    ftot = sum(fc.values())
    first_round_can.append(100 * fc["CAN"] / ftot)
    first_round_usa.append(100 * fc["USA"] / ftot)

FINDINGS["draft"] = {
    "years": f"{years[0]}-{years[-1]}",
    "total_picks": n_picks,
    "can_share_2000": round(shares["CAN"][0], 1),
    "can_share_2025": round(shares["CAN"][-1], 1),
    "usa_share_2000": round(shares["USA"][0], 1),
    "usa_share_2025": round(shares["USA"][-1], 1),
}

fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
a1.stackplot(years, shares["CAN"], shares["USA"], shares["OTHER"],
             labels=["Canada", "United States", "Rest of world"],
             colors=[CAN, USA, "#c9c9c9"])
a1.legend(frameon=False, loc="upper right")
a1.set_title("Where NHL draft picks are born (2000–2025)")
a1.set_ylabel("% of picks")
a1.set_ylim(0, 100)
a2.plot(years, first_round_can, color=CAN, lw=2.5, label="Canada (1st round)")
a2.plot(years, first_round_usa, color=USA, lw=2.5, label="USA (1st round)")
a2.set_title("First-round picks: Canada vs USA")
a2.set_ylabel("% of first-round picks")
a2.legend(frameon=False)
for ax in (a1, a2):
    despine(ax)
fig.savefig(CHARTS / "draft_nationality.png", bbox_inches="tight")
plt.close(fig)
print("draft findings:", FINDINGS["draft"])


# ============ 3. Ngrams: the vocabulary border ============
# corpus 27 = British English (2019), corpus 28 = American English (2019)
# (verified empirically: "cheque", "lorry", "petrol" all dominate in corpus 27)
def ngram_series(slug, corpus):
    d = json.loads((RAW / f"ngram_{slug}_corpus{corpus}.json").read_text())
    return {e["ngram"]: np.array(e["timeseries"], dtype=float) for e in d}

YRS = np.arange(1960, 2020)
NG = {}
for slug in ["toque_beanie", "washroom_restroom", "eh", "cheque"]:
    for corpus in (27, 28):
        key = f"{slug}_{'uk' if corpus == 27 else 'us'}"
        NG[key] = ngram_series(slug, corpus)

def vocab_chart(pairs, titles, fname):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    for ax, (slug, w1, w2), title in zip(axes, pairs, titles):
        us = NG[f"{slug}_us"]; uk = NG[f"{slug}_uk"]
        ax.plot(YRS, us[w1], color=USA, lw=2, label=f"{w1} (US corpus)")
        ax.plot(YRS, us[w2], color=USA, lw=2, ls="--", label=f"{w2} (US corpus)")
        ax.plot(YRS, uk[w1], color=CAN, lw=2, label=f"{w1} (British corpus)")
        ax.plot(YRS, uk[w2], color=CAN, lw=2, ls="--", label=f"{w2} (British corpus)")
        ax.set_title(title); ax.legend(frameon=False, fontsize=9)
        despine(ax)
    fig.savefig(CHARTS / fname, bbox_inches="tight")
    plt.close(fig)

vocab_chart([("toque_beanie", "toque", "beanie"), ("washroom_restroom", "washroom", "restroom")],
            ["toque vs beanie", "washroom vs restroom"], "ngram_words.png")

# ratio summary: British corpus frequency / American corpus frequency in 2019
ratio = {}
for w in ["toque", "beanie", "washroom", "restroom", "eh", "cheque"]:
    slug = {"toque": "toque_beanie", "beanie": "toque_beanie",
            "washroom": "washroom_restroom", "restroom": "washroom_restroom",
            "eh": "eh", "cheque": "cheque"}[w]
    uk = NG[f"{slug}_uk"][w][-1]
    us = NG[f"{slug}_us"][w][-1]
    ratio[w] = round(float(uk / us), 2) if us else None
FINDINGS["ngram_british_vs_american_2019"] = ratio
# within-corpus 2019 winners
for corpus_name, tag in [("American English", "us"), ("British English", "uk")]:
    tb = NG[f"toque_beanie_{tag}"]
    wr = NG[f"washroom_restroom_{tag}"]
    FINDINGS[f"ngram_2019_{tag}"] = {
        "toque_vs_beanie": "toque" if tb["toque"][-1] > tb["beanie"][-1] else "beanie",
        "washroom_vs_restroom": "washroom" if wr["washroom"][-1] > wr["restroom"][-1] else "restroom",
    }
print("ngram ratios:", ratio)


# ============ 4. Diaspora: Chinese Canadians ============
# Historical share of Canadian population (%), compiled from census data.
# Sources: Statistics Canada censuses via en.wikipedia.org/wiki/Chinese_Canadians
# ("Chinese population by year") and StatCan "Portrait of the Chinese Populations
# in Canada" (89-657-X2026001). See data/diaspora_sources.md.
# Absolute Chinese population by census year — "Chinese ethnic origin (incl.
# partial ancestry)" series, the most consistent long-run cut available.
# Sources: Wikipedia "Chinese Canadians" (citing StatCan censuses):
# 1901: 17,312; religion-table population row for 1971/1981/1991/2001;
# 2006: 1,346,510; 2011: 1,487,000; 2016: ~1.57M; 2021: 1,713,163.
# See data/diaspora_sources.md for full citations.
hist = [
    (1901, 17312), (1971, 124600), (1981, 285800), (1991, 633931),
    (2001, 1094700), (2006, 1346510), (2011, 1487000), (2016, 1570000),
    (2021, 1713163),
]
with open(DATA / "diaspora_history.csv", "w") as f:
    f.write("year,population\n")
    for y, v in hist:
        f.write(f"{y},{v}\n")

hy, hv = zip(*hist)
hv_k = [v / 1000 for v in hv]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.plot(hy, hv_k, color=CAN, lw=3, marker="o", ms=6)
ax.fill_between(hy, hv_k, alpha=0.12, color=CAN)
ann = [
    (1885, 60, "Head tax\n(1885)"), (1923, 120, "Exclusion Act\n(1923–47)"),
    (1967, 420, "Points system\n(1967)"), (1990, 1150, "HK wave\n1988–93"),
    (2021, 1713, "1.7M people\n(2021)"),
]
for y, v, label in ann:
    ax.annotate(label, xy=(y, v), xytext=(y - 6, v + 260),
                fontsize=9, ha="center", color="#444",
                arrowprops=dict(arrowstyle="-", color="#999", lw=1))
ax.set_ylim(0, 2100)
ax.set_title("Chinese Canadians: from 17,312 people (1901) to 1.7 million (2021)")
ax.set_ylabel("Population (thousands)")
despine(ax)
fig.savefig(CHARTS / "diaspora_growth.png", bbox_inches="tight")
plt.close(fig)

cmas = [("Toronto CMA", 631050, 10.8), ("Vancouver CMA", 474655, 19.6),
        ("Calgary", 89675, 7.0), ("Montréal", 89400, 2.2),
        ("Edmonton", 60200, 4.6), ("Ottawa–Gatineau", 43775, 3.4)]
with open(DATA / "diaspora_cma.csv", "w") as f:
    f.write("cma,population,share_pct\n")
    for n, p, s in cmas:
        f.write(f"{n},{p},{s}\n")
names = [c[0] for c in cmas]; pops = [c[1] / 1000 for c in cmas]
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(names[::-1], pops[::-1], color=CAN, alpha=0.85)
for b, (n, p, s) in zip(bars, list(zip(names, pops, [c[2] for c in cmas]))[::-1]):
    ax.text(b.get_width() + 8, b.get_y() + b.get_height() / 2, f"{p:.0f}k  ({s}%)",
            va="center", fontsize=10)
ax.set_xlabel("Chinese population (thousands)")
ax.set_title("Where Chinese Canadians live: largest metro areas (2021 Census)")
despine(ax)
fig.savefig(CHARTS / "diaspora_cma.png", bbox_inches="tight")
plt.close(fig)

birth = [("China", 47.8), ("Canada", 28.4), ("Hong Kong", 12.8),
         ("Taiwan", 4.1), ("Southeast Asia", 4.1), ("Elsewhere", 2.8)]
fig, ax = plt.subplots(figsize=(7, 7))
colors = ["#D52B1E", "#3C3B6E", "#c9a227", "#7fb069", "#e07a5f", "#c9c9c9"]
wedges, texts, autotexts = ax.pie(
    [b[1] for b in birth], labels=[b[0] for b in birth], autopct="%1.1f%%",
    colors=colors, startangle=90, pctdistance=0.8)
for t in autotexts:
    t.set_fontsize(9); t.set_color("white"); t.set_weight("bold")
ax.set_title("Where Chinese Canadians were born (2021 Census)")
fig.savefig(CHARTS / "diaspora_birthplace.png", bbox_inches="tight")
plt.close(fig)

FINDINGS["diaspora"] = {
    "pop_2021": 1713163, "share_2021_pct": 4.6,
    "top_cma": "Toronto CMA (631,050)", "richmond_share": 54.3,
    "canada_born_share": 28.4,
}
(DATA / "findings.json").write_text(json.dumps(FINDINGS, indent=2))
print("findings.json written")
print(json.dumps(FINDINGS, indent=2))
