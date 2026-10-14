"""
04_charts.py - figures for the README. Run after 02 and 03.
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
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25,
                     "grid.linestyle": "--"})
INK, ACC, GREY = "#1a1a2e", "#c0392b", "#7f8c8d"

F = json.load(open(os.path.join(DATA, "findings.json")))
M = json.load(open(os.path.join(DATA, "model.json")))
series = pd.read_csv(os.path.join(DATA, "year_series.csv"))

# 1 ------------------------------------------------------- the flat line, then the cliff
fig, ax = plt.subplots(figsize=(9, 4.6))
s = series[series.year >= 1974]
ax.fill_between(s.year, s.friend_monthly - 1.96 * s.friend_monthly_se,
                s.friend_monthly + 1.96 * s.friend_monthly_se,
                color=ACC, alpha=0.12, lw=0)
ax.plot(s.year, s.friend_monthly, color=INK, lw=2.2, marker="o", ms=3.5)
ax.axhline(F["friend_monthly_longrun_mean"], color=GREY, lw=1, ls=":")
ax.annotate(f"1974-2018 average: {F['friend_monthly_longrun_mean']}%",
            (1975, F["friend_monthly_longrun_mean"] + 1.6), fontsize=9,
            color=GREY)
ax.annotate("2021: 48.4%\n(web survey, mid-COVID)",
            (2021, 48.4), textcoords="offset points", xytext=(-118, -6),
            fontsize=9, color=ACC)
ax.annotate(f"2022-24: {F['friend_monthly_2022_24']}%",
            (2024, F["friend_monthly_2022_24"]), textcoords="offset points",
            xytext=(-96, 14), fontsize=10, color=ACC, fontweight="bold")
ax.set_ylim(42, 74)
ax.set_ylabel("% spending social evenings\nwith friends at least monthly")
ax.set_title("Forty-four flat years, then the evenings disappeared")
fig.tight_layout(); fig.savefig(f"{CH}/the_cliff.png"); plt.close(fig)

# 2 ------------------------------------------------------- who it hit (age)
age_era = pd.read_csv(os.path.join(DATA, "age_era.csv"))
fig, ax = plt.subplots(figsize=(9, 4.4))
for era, color, lw in [("1974-1989", "#bdc3c7", 1.6), ("1990-2009", "#95a5a6", 1.6),
                       ("2010-2018", INK, 2.2), ("2022-2024", ACC, 2.6)]:
    g = age_era[age_era.era == era]
    ax.plot(g.ageband, g.friend_monthly, marker="o", color=color, lw=lw,
            label=era)
ax.set_ylabel("% friend evenings at least monthly")
ax.set_title("The drop is a young person's story: 25-34 fell 11 points, 65+ fell 2")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(f"{CH}/age_drop.png"); plt.close(fig)

# 3 ------------------------------------------------------- everything fell
items = ["friend", "relatives", "community", "bar"]
labels = ["Friends", "Relatives", "Community /\nneighbours", "Bar / tavern"]
pre = [F[f"{i}_monthly_change_pp"] for i in items]
epm = [F[f"{i}_epm_change_pct"] for i in items]
x = np.arange(len(items))
fig, ax = plt.subplots(figsize=(9, 4.2))
b = ax.bar(x, pre, color=ACC, alpha=0.85, width=0.55)
for xi, v, e in zip(x, pre, epm):
    ax.text(xi, v - 0.7, f"{v:+.1f} pp\n({e:+.0f}% in evenings/mo)",
            ha="center", va="top", fontsize=9, color="white",
            fontweight="bold")
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(x, labels)
ax.set_ylabel("Change in % at least monthly,\n2014-18 -> 2022-24 (pp)")
ax.set_title("Not substitution. Everything fell at once")
ax.set_ylim(min(pre) - 3.5, 1.5)
fig.tight_layout(); fig.savefig(f"{CH}/everything_fell.png"); plt.close(fig)

# 4 ------------------------------------------------------- decomposition
dec = F["decomp"]
fig, ax = plt.subplots(figsize=(9, 3.8))
vals = [dec["composition_pp"], dec["behaviour_pp"]]
ax.barh(["Who Americans are\n(age, family, work mix)", "How each group behaves"],
        vals, color=[GREY, ACC], height=0.5)
for i, v in enumerate(vals):
    ax.text(v - 0.25, i, f"{v:+.1f} pp", ha="right", va="center",
            fontsize=11, color="white", fontweight="bold")
ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("Share of the -7.8 pp drop in monthly friend evenings")
ax.set_title("92% of the drop is behaviour inside identical life situations")
fig.tight_layout(); fig.savefig(f"{CH}/decomposition.png"); plt.close(fig)

# 5 ------------------------------------------------------- SHAP
imp = pd.read_csv(os.path.join(DATA, "shap_importance.csv")).head(10).iloc[::-1]
nice = {"age": "Age", "marital_lbl_Married": "Married",
        "childs": "Number of children", "educ": "Years of education",
        "year": "Survey year", "attend": "Religious attendance",
        "log_size": "City size (log)", "log_rinc": "Income (log)",
        "tvhours_c": "TV hours / day", "hrs1_c": "Work hours / week",
        "marital_lbl_Never married": "Never married",
        "sex_lbl_Female": "Female", "employed": "Employed"}
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.barh([nice.get(f, f) for f in imp.feature], imp.mean_abs_shap,
        color=INK, alpha=0.88)
ax.set_xlabel("Mean |SHAP| - pooled XGBoost, P(friend evening at least monthly)")
ax.set_title("What sorts people into friend-evening lives: age first, then marriage and kids")
fig.tight_layout(); fig.savefig(f"{CH}/shap_bar.png"); plt.close(fig)

# 6 ------------------------------------------------------- ATUS age curve (cross-check)
ow = pd.read_csv(os.path.join(DATA, "atus_time_by_age_owid.csv"))
allp = ow[ow.Entity == "All people"].sort_values("Year")
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(allp.Year, allp["With friends"], color=ACC, lw=2.4,
        label="With friends")
ax.plot(allp.Year, allp["Alone"], color=INK, lw=2.4, label="Alone")
ax.plot(allp.Year, allp["With partner"], color="#2471a3", lw=1.8,
        label="With partner")
ax.plot(allp.Year, allp["With children"], color="#229954", lw=1.8,
        label="With children")
ax.set_xlabel("Age")
ax.set_ylabel("Hours per day (ATUS diaries, pooled)")
ax.set_title("The diary agrees: friend time peaks at 19 and never comes back")
ax.legend(frameon=False, ncol=4, loc="upper center",
          bbox_to_anchor=(0.5, -0.13))
fig.tight_layout(); fig.savefig(f"{CH}/atus_age_curve.png"); plt.close(fig)

# 7 ------------------------------------------------------- happiness penalty
hap = M["happiness_adjusted"]
cats = ["Weekly+", "Monthly", "Yearly", "Rarely/never"]
x = np.arange(len(cats))
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(x - 0.2, [hap["pre_2014_18"][c] for c in cats], width=0.4,
       color=GREY, label="2014-2018")
ax.bar(x + 0.2, [hap["post_2022_24"][c] for c in cats], width=0.4,
       color=ACC, label="2022-2024")
ax.set_xticks(x, ["Weekly+", "Monthly", "A few times\na year", "Once a year\nor never"])
ax.set_ylabel('Adjusted % "very happy"')
ax.set_title("Friend evenings still price into happiness - about 8-9 points, both eras")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(f"{CH}/happiness_penalty.png"); plt.close(fig)

print("charts written:", sorted(os.listdir(CH)))
