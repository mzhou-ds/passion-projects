#!/usr/bin/env python3
"""Charts for Same Grandparents, Different Deal."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJ = Path("/home/hatch/workspace/passion-projects/2026-09-24/same-grandparents-different-deal")
CH = PROJ / "charts"
CH.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
    "figure.dpi": 150,
})
RED, GOLD, INK, TEAL = "#c8102e", "#b98a00", "#1a1a1a", "#0e7c7b"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CH / name, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ---------------- 1. H-1B lottery ----------------
def h1b():
    years = ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025", "FY2026"]
    reg = [274237, 308613, 483927, 780884, 479953, 345737]
    sel = [124415, 131924, 127600, 188400, 135137, 120141]
    rate = [s / r * 100 for s, r in zip(sel, reg)]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(years))
    ax.bar(x, reg, color="#d9d2c2", label="Registrations")
    ax.bar(x, sel, color=RED, label="Selected")
    ax2 = ax.twinx()
    ax2.plot(x, rate, color=INK, marker="o", ms=7, lw=2.5)
    for i, v in enumerate(rate):
        ax2.annotate(f"{v:.0f}%", (i, v), textcoords="offset points", xytext=(0, 10),
                     ha="center", fontsize=10, weight="bold")
    ax.set_xticks(list(x)); ax.set_xticklabels(years)
    ax.set_ylabel("Registrations / selections")
    ax2.set_ylabel("Selection rate")
    ax2.set_ylim(0, 60)
    ax.set_title("The H-1B lottery: registrations vs selections, FY2021–2026", weight="bold", loc="left")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: USCIS registration/selection figures (via BAL, Congress reporting). FY2025+ uses beneficiary-centric selection.",
             fontsize=8, color="#777")
    save(fig, "chart_h1b_lottery.png")


# ---------------- 2. EE citizenships ----------------
def ee_cit():
    d = json.load(open(PROJ / "data" / "ircc_summary.json"))
    rows = d["ee_top_citizenships"][:10]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    colors = [RED if c in ("India", "China, People's Republic of") else TEAL if "Cameroon" in c else "#8a8a8a"
              for c, _ in rows]
    ax.barh([c.replace(", People's Republic of", "").replace(", Federal Republic of", "") for c, _ in rows],
            [t for _, t in rows], color=colors)
    for i, (_, t) in enumerate(rows):
        ax.text(t, i, f" {t:,}", va="center", fontsize=10)
    ax.set_title("Express Entry invitations by citizenship, 2015–2026 (top 10)", weight="bold", loc="left")
    ax.set_xlabel("Invitations to apply")
    fig.text(0.01, -0.02, "Source: IRCC Open Data, Express Entry invited candidates by citizenship (monthly).",
             fontsize=8, color="#777")
    save(fig, "chart_ee_citizenship.png")


# ---------------- 3. EE score bands ----------------
def ee_bands():
    d = json.load(open(PROJ / "data" / "ircc_summary.json"))
    order = list(d["ee_bands_2024"].keys())
    labels = [b.replace("Score ", "") for b in order]
    a = [d["ee_bands_alltime"][b] for b in order]
    b24 = [d["ee_bands_2024"][b] for b in order]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(order))
    w = 0.42
    ax.bar([i - w / 2 for i in x], a, w, color="#d9d2c2", label="2015–2026 all-time")
    ax.bar([i + w / 2 for i in x], b24, w, color=RED, label="2024")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_title("Where invitations land: CRS score bands", weight="bold", loc="left")
    ax.set_ylabel("Invitations")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: IRCC Open Data. The 901–1100 hump is the Provincial Nominee Program (600 bonus points).",
             fontsize=8, color="#777")
    save(fig, "chart_ee_bands.png")


# ---------------- 4. generation income (Canada) ----------------
def generation():
    df = pd.read_csv(PROJ / "data" / "statcan_income_filtered.csv")
    q = df[(df["GEO"] == "Canada")
           & (df["Highest certificate, diploma or degree (16)"] == "Total - Highest certificate, diploma or degree")
           & (df["Age (15B)"] == "25 to 54 years") & (df["Gender (3)"] == "Total - Gender")
           & (df["Income statistics (17)"] == "Median total income ($)")]
    gens = ["First generation", "Second generation", "Third generation or more"]
    gl = ["1st gen", "2nd gen", "3rd+ gen"]
    ch = [float(q[q["Generation status (4)"] == g]["Chinese[4]"].iloc[0]) for g in gens]
    nv = [float(q[q["Generation status (4)"] == g]["Not a visible minority[15]"].iloc[0]) for g in gens]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(3); w = 0.38
    ax.bar([i - w / 2 for i in x], ch, w, color=RED, label="Chinese Canadians")
    ax.bar([i + w / 2 for i in x], nv, w, color="#8a8a8a", label="Non-visible-minority Canadians")
    for i, (c, n) in enumerate(zip(ch, nv)):
        ax.text(i - w / 2, c + 800, f"${c:,.0f}", ha="center", fontsize=10, weight="bold")
        ax.text(i + w / 2, n + 800, f"${n:,.0f}", ha="center", fontsize=10)
    ax.set_xticks(list(x)); ax.set_xticklabels(gl)
    ax.set_title("Median income by generation: the second-generation flip (Canada, 25–54)", weight="bold", loc="left")
    ax.set_ylabel("Median total income (2020 CAD)")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: Statistics Canada 2021 Census, table 98-10-0331-01. Income reference year 2020.",
             fontsize=8, color="#777")
    save(fig, "chart_generation.png")


# ---------------- 5. US outcomes ----------------
def outcomes():
    r = json.load(open(PROJ / "data" / "us_indicators.json"))
    items = [
        ("Bachelor's+ (%)", r["us_baplus_asian"] * 100, r["us_baplus_total"] * 100, "%"),
        ("White-collar occ. (%)", r["us_whitecollar_asian"] * 100, r["us_whitecollar_total"] * 100, "%"),
        ("Homeownership (%)", r["us_homeown_asian"] * 100, r["us_homeown_total"] * 100, "%"),
        ("Unemployment (%)", r["us_unemp_asian"] * 100, r["us_unemp_total"] * 100, "%"),
        ("Poverty (%)", r["us_poverty_asian"] * 100, r["us_poverty_total"] * 100, "%"),
    ]
    fig, axes = plt.subplots(1, 5, figsize=(12, 4.2), sharey=False)
    for ax, (label, a, t, _) in zip(axes, items):
        ax.barh(["Asian", "US avg"], [a, t], color=[RED, "#8a8a8a"], height=0.55)
        ax.set_title(label, fontsize=11)
        mx = max(a, t) * 1.25
        ax.set_xlim(0, mx)
        for i, v in enumerate([a, t]):
            ax.text(v, i, f" {v:.1f}%", va="center", fontsize=10)
        ax.tick_params(left=False); ax.set_yticks([0, 1]); ax.set_yticklabels(["Asian", "US avg"])
    fig.suptitle("Asian Americans vs the US average (ACS 2020–2024)", weight="bold", x=0.02, ha="left", fontsize=14)
    fig.text(0.01, -0.01, "Source: US Census Bureau ACS 5-year estimates via Census Reporter. Asian-alone vs total population.",
             fontsize=8, color="#777")
    save(fig, "chart_outcomes.png")


# ---------------- 6. income comparison US vs Canada ----------------
def income_compare():
    r = json.load(open(PROJ / "data" / "us_indicators.json"))
    df = pd.read_csv(PROJ / "data" / "statcan_income_filtered.csv")
    q = df[(df["GEO"] == "Canada") & (df["Generation status (4)"] == "Total - Generation status")
           & (df["Highest certificate, diploma or degree (16)"] == "Total - Highest certificate, diploma or degree")
           & (df["Age (15B)"] == "25 to 54 years") & (df["Gender (3)"] == "Total - Gender")
           & (df["Income statistics (17)"] == "Median total income ($)")].iloc[0]
    ca_ch, ca_nv = float(q["Chinese[4]"]), float(q["Not a visible minority[15]"])
    fig, ax = plt.subplots(figsize=(9, 5))
    cats = ["US: Asian vs\nUS average", "Canada: Chinese vs\nnon-vis-min (25–54)"]
    vals_a = [r["us_medearn_asian"], ca_ch]
    vals_b = [r["us_medearn_total"], ca_nv]
    x = range(2); w = 0.38
    ax.bar([i - w / 2 for i in x], vals_a, w, color=RED, label="Asian / Chinese")
    ax.bar([i + w / 2 for i in x], vals_b, w, color="#8a8a8a", label="Average / non-visible-minority")
    for i, (a, b) in enumerate(zip(vals_a, vals_b)):
        ax.text(i - w / 2, a + 600, f"${a:,.0f}", ha="center", fontsize=10, weight="bold")
        ax.text(i + w / 2, b + 600, f"${b:,.0f}", ha="center", fontsize=10)
    ax.set_xticks(list(x)); ax.set_xticklabels(cats)
    ax.set_title("Median earnings: the US premium vs the Canadian discount", weight="bold", loc="left")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "US: median earnings 16+ w/ earnings, ACS 2020–24 (USD). Canada: median total income 25–54, Census 2021 ref. year 2020 (CAD). Different universes — direction, not precision.",
             fontsize=8, color="#777")
    save(fig, "chart_income_compare.png")


# ---------------- 7. metros ----------------
def metros():
    us = json.load(open(PROJ / "data" / "us_metro.json"))
    order = ["San Jose", "San Francisco", "Seattle", "Washington DC", "New York", "Los Angeles"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    a = [us[m]["asian_medhh"] / 1000 for m in order]
    t = [us[m]["total_medhh"] / 1000 for m in order]
    y = range(len(order))
    ax.barh([i + 0.22 for i in y], a, 0.4, color=RED, label="Asian median HH income")
    ax.barh([i - 0.22 for i in y], t, 0.4, color="#8a8a8a", label="Metro median HH income")
    ax.set_yticks(list(y)); ax.set_yticklabels(order)
    ax.set_xlabel("Median household income ($000s, USD)")
    ax.set_title("US metros: Asian HH income beats the metro avg everywhere", weight="bold", loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=9)
    ax = axes[1]
    ca = [("Toronto CMA", 48800, 50000, 11.1), ("Vancouver CMA", 44400, 50800, 18.9)]
    names = [c[0] for c in ca]
    y2 = range(len(names))
    ax.barh([i + 0.22 for i in y2], [c[1] / 1000 for c in ca], 0.4, color=RED, label="Chinese median (25–54)")
    ax.barh([i - 0.22 for i in y2], [c[2] / 1000 for c in ca], 0.4, color="#8a8a8a", label="Metro median (25–54)")
    for i, c in enumerate(ca):
        ax.text(52, i, f"{c[3]:.1f}% Chinese", va="center", fontsize=10, color="#555")
    ax.set_yticks(list(y2)); ax.set_yticklabels(names)
    ax.set_xlabel("Median total income ($000s, CAD)")
    ax.set_title("Canadian CMAs: near parity in Toronto, a gap in Vancouver", weight="bold", loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=9)
    fig.suptitle("Two Chinatowns: the metro spotlight", weight="bold", x=0.02, ha="left", fontsize=14)
    fig.text(0.01, -0.01, "US: ACS 2020–24 5-yr, Asian-alone vs total. Canada: 2021 Census, Chinese visible minority vs all, ages 25–54, income ref. year 2020.",
             fontsize=8, color="#777")
    save(fig, "chart_metros.png")


# ---------------- 8. LCA wages ----------------
def lca():
    d = json.load(open(PROJ / "data" / "lca_tech_wages.json"))
    rows = [(k, v) for k, v in d.items() if v["n"] >= 12]
    rows.sort(key=lambda x: x[1]["median"])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    names = [k for k, _ in rows][::-1]
    meds = [v["median"] for _, v in rows][::-1]
    ns = [v["n"] for _, v in rows][::-1]
    colors = [RED if k in ("Meta", "Google") else TEAL for k in names]
    ax.barh(names, meds, color=colors)
    for i, (m, n) in enumerate(zip(meds, ns)):
        ax.text(m, i, f" ${m:,.0f} (n={n})", va="center", fontsize=10)
    ax.set_xlim(0, max(meds) * 1.28)
    ax.set_xlabel("Median offered wage, annualized (USD)")
    ax.set_title("The price tag: Big Tech software LCA medians, Bay Area (FY2025 Q4)", weight="bold", loc="left")
    fig.text(0.01, -0.02, "Source: DOL OFLC LCA disclosure FY2025 Q4; certified cases, job titles containing 'software', CA Bay Area worksites.",
             fontsize=8, color="#777")
    save(fig, "chart_lca_wages.png")


# ---------------- 9. employment income trend ----------------
def emp_trend():
    df = pd.read_csv(PROJ / "data" / "statcan_empincome_years_filtered.csv")
    q = df[(df["immgen"] == "Total – Immigrant and generation status")
           & (df["education"] == "Total - Highest certificate, diploma or degree")
           & (df["income_stat"] == "Average employment income ($)")]
    years = ["2006", "2011", "2016", "2021"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for grp, color, ls in [("Chinese", RED, "-"), ("Not a visible minority", "#8a8a8a", "--")]:
        r = q[q["vismin"] == grp].iloc[0]
        vals = [r["y" + y] for y in years]
        ax.plot(years, vals, color=color, marker="o", ms=7, lw=2.5, label=grp)
        for x, v in zip(years, vals):
            ax.annotate(f"${v:,.0f}", (x, v), textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=9)
    ax.set_title("Average employment income, 2006–2021: the slow convergence", weight="bold", loc="left")
    ax.set_ylabel("Average employment income (nominal CAD)")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: Statistics Canada 2021 Census, table 98-10-0642-01 (income ref. years 2005/2010/2015/2020). Nominal dollars.",
             fontsize=8, color="#777")
    save(fig, "chart_empincome_trend.png")


# ---------------- 10. mother tongue ----------------
def mothertongue():
    rows = list(__import__("csv").DictReader(open(PROJ / "data" / "statcan_mothertongue_filtered.csv")))
    gens = ["First generation", "Second generation", "Third generation or more"]
    gl = ["1st gen", "2nd gen", "3rd+ gen"]
    man, can = [], []
    for gen in gens:
        tot = m = c = 0
        for r in rows:
            if r["vismin"] == "Chinese" and r["generation"] == gen and r["age"] == "Total - Age":
                if r["mother_tongue"] == "Total - Mother tongue":
                    tot = float(r["single"])
                elif r["mother_tongue"] == "Mandarin":
                    m = float(r["single"])
                elif r["mother_tongue"] == "Yue (Cantonese)":
                    c = float(r["single"])
        man.append(m / tot * 100); can.append(c / tot * 100)
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(3); w = 0.38
    ax.bar([i - w / 2 for i in x], man, w, color=RED, label="Mandarin mother tongue")
    ax.bar([i + w / 2 for i in x], can, w, color=GOLD, label="Cantonese mother tongue")
    for i, (a, b) in enumerate(zip(man, can)):
        ax.text(i - w / 2, a + 1, f"{a:.0f}%", ha="center", fontsize=10, weight="bold")
        ax.text(i + w / 2, b + 1, f"{b:.0f}%", ha="center", fontsize=10, weight="bold")
    ax.set_xticks(list(x)); ax.set_xticklabels(gl)
    ax.set_ylabel("% with Chinese mother tongue (single response)")
    ax.set_title("What survives: mother tongue by generation (Chinese Canadians)", weight="bold", loc="left")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: Statistics Canada 2021 Census, table 98-10-0325-01. Share reporting Mandarin or Yue (Cantonese) as single mother tongue.",
             fontsize=8, color="#777")
    save(fig, "chart_mothertongue.png")


# ---------------- 11. low income by generation ----------------
def lowincome():
    rows = list(__import__("csv").DictReader(open(PROJ / "data" / "statcan_lowincome_filtered.csv")))
    groups = ["Chinese", "Not a visible minority"]
    gl = ["All gens", "1st gen", "2nd gen", "3rd+ gen"]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(4); w = 0.38
    for j, g in enumerate(groups):
        r = next(r for r in rows if r["vismin"] == g and "Prevalence" in r["status"])
        vals = [float(r["gen_total"]), float(r["gen_first"]), float(r["gen_second"]), float(r["gen_thirdplus"])]
        ax.bar([i + (j - 0.5) * w for i in x], vals, w,
               color=RED if g == "Chinese" else "#8a8a8a",
               label="Chinese Canadians" if g == "Chinese" else "Non-visible-minority")
        for i, v in enumerate(vals):
            ax.text(i + (j - 0.5) * w, v + 0.3, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels(gl)
    ax.set_ylabel("Low-income rate, LIM-AT (%)")
    ax.set_title("Low-income rate collapses by the third generation", weight="bold", loc="left")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: Statistics Canada 2021 Census, table 98-10-0332-01 (income ref. year 2020).",
             fontsize=8, color="#777")
    save(fig, "chart_lowincome.png")


# ---------------- 12. management (bamboo ceiling) ----------------
def mgmt():
    import csv as _csv
    rows = list(_csv.DictReader(open(PROJ / "data" / "statcan_occupation_filtered.csv")))
    gens = ["Total - Generation status", "First generation", "Second generation"]
    gl = ["All gens", "1st gen", "2nd gen"]
    # NOC nesting check: is major group 21 (professional) nested inside broad 2?
    r0 = [r for r in rows if r["generation"] == "Total - Generation status"
          and r["education"] == "Total - Highest certificate, diploma or degree"
          and r["age"] == "Total - Age"]
    b2 = sum(float(r["chinese"] or 0) for r in r0 if r["kind"] == "tech_broad")
    p21 = sum(float(r["chinese"] or 0) for r in r0 if r["kind"] == "tech_prof")
    nested = p21 > 0 and p21 <= b2  # broad categories already include their major groups
    print(f"NOC nesting check: broad-2 Chinese={b2:,.0f} vs 21-prof Chinese={p21:,.0f} -> nested={nested}")
    ch, nv = [], []
    prime = ("25 to 34 years", "35 to 44 years", "45 to 54 years")
    for gen in gens:
        for grp, store in (("chinese", ch), ("not_vismin", nv)):
            m0 = m2 = bsum = 0.0
            for r in rows:
                if (r["generation"] == gen and r["education"] == "Total - Highest certificate, diploma or degree"
                        and r["age"] in prime):
                    v = float(r[grp] or 0)
                    occ = r["occupation"]
                    if r["kind"] == "mgmt" and occ.startswith("0 "):
                        m0 += v
                    elif r["kind"] == "mgmt":
                        m2 += v
                    elif r["kind"] == "broad":
                        bsum += v
            mgmt_total = m0 + m2
            # if broad cats nest their major groups, denominator = broad + '0'; else broad + all mgmt
            denom = bsum + m0 if nested else bsum + mgmt_total
            store.append(mgmt_total / denom * 100 if denom else 0)
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(3); w = 0.38
    ax.bar([i - w / 2 for i in x], ch, w, color=RED, label="Chinese Canadians")
    ax.bar([i + w / 2 for i in x], nv, w, color="#8a8a8a", label="Non-visible-minority Canadians")
    for i, (a, b) in enumerate(zip(ch, nv)):
        ax.text(i - w / 2, a + 0.15, f"{a:.1f}%", ha="center", fontsize=10, weight="bold")
        ax.text(i + w / 2, b + 0.15, f"{b:.1f}%", ha="center", fontsize=10)
    ax.set_xticks(list(x)); ax.set_xticklabels(gl)
    ax.set_ylabel("% of employed in management occupations (ages 25–54)")
    ax.set_title("The bamboo ceiling that wasn't: management share by generation", weight="bold", loc="left")
    ax.legend(frameon=False)
    fig.text(0.01, -0.02, "Source: Statistics Canada 2021 Census, table 98-10-0330-01, ages 25–54. Management = NOC broad cat. 0 + middle-management groups.",
             fontsize=8, color="#777")
    save(fig, "chart_mgmt.png")


if __name__ == "__main__":
    h1b(); ee_cit(); ee_bands(); generation(); outcomes(); income_compare(); metros(); lca()
    emp_trend(); mothertongue(); lowincome(); mgmt()
