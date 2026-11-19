#!/usr/bin/env python3
"""Charts for The Retention Gap (build #73)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#888888",
    "axes.grid": True,
    "grid.color": "#e6e6e6",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})

CA_RED = "#c8102e"
US_BLUE = "#1f4e79"
GOLD = "#c98a1b"
GREY = "#8a8a8a"

ca = pd.read_csv("data/ca_comparison.csv")
us = pd.read_csv("data/us_retention.csv")
ca_age = pd.read_csv("data/ca_age_retention.csv")
us_age = pd.read_csv("data/us_age.csv")
us_sa = pd.read_csv("data/us_state_age.csv")

# ---------------------------------------------------------------- chart 1
# Retention by generation: the two countries are the same number.
fig, ax = plt.subplots(figsize=(10, 5.6))
gens = ["Immigrant\n(1st gen)", "Native-born\n(2nd gen, CA)", "Native-born\n(2nd gen+, US)"]
# Canada MT retention: 1st 89.8, 2nd 42.9, 3rd+ 4.4
# Canada derived home-use: 1st 82.4, 2nd 32.9
# US home-use: foreign-born 81.5, native 32.2
ca_mt = [0.898, 0.429, 0.044]
ca_home = [0.824, 0.329, np.nan]
us_home = [0.815, 0.322, np.nan]
x = np.arange(3)
w = 0.24
b1 = ax.bar(x - w, [v * 100 if v == v else 0 for v in ca_mt], w, label="Canada — Chinese mother tongue", color=CA_RED)
b2 = ax.bar(x, [v * 100 if v == v else 0 for v in ca_home], w, label="Canada — speaks non-official language at home (derived)", color=GOLD)
b3 = ax.bar(x + w, [v * 100 if v == v else 0 for v in us_home], w, label="US — speaks Chinese at home (PUMS)", color=US_BLUE)
for bars in (b1, b2, b3):
    for r in bars:
        if r.get_height() > 0:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1.5,
                    f"{r.get_height():.1f}%", ha="center", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(["Immigrants\n(1st generation)", "Native-born\n(2nd gen in Canada;\n2nd gen and later in US)", "Third generation+\n(Canada only)"])
ax.set_ylabel("Share of the Chinese-heritage population (%)")
ax.set_title("The mosaic and the melting pot retain a language at the same rate",
             fontsize=13, fontweight="bold", loc="left")
ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
fig.text(0.07, 0.01,
         "Canada: 2021 Census. Mother tongue = first language learned, still understood, among the Chinese visible-minority population.\n"
         "Home-use derived as mother-tongue retention × share speaking a non-official language at home. "
         "US: ACS 2022 1-year PUMS, share of Chinese-ancestry\n"
         "persons speaking a Chinese language at home. The US cannot split 2nd from 3rd+ generation, so its native-born bar pools both.",
         fontsize=8, color="#555555", va="bottom")
fig.tight_layout(rect=[0, 0.09, 1, 1])
fig.savefig("charts/retention_by_generation.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 2
# The third-generation cliff (Canada) + age gradient (both countries).
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.2))
ca_nat = ca[ca.geography == "Canada"]
order = ["First generation", "Second generation", "Third generation or more"]
mt = [ca_nat[ca_nat.generation == g]["retention_mt"].values[0] * 100 for g in order]
a1.bar(["1st gen", "2nd gen", "3rd+ gen"], mt, color=[CA_RED, GOLD, GREY], width=0.6)
for i, v in enumerate(mt):
    a1.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
a1.set_ylabel("Chinese mother tongue\n(% of Chinese visible minority)")
a1.set_title("Canada: the third-generation cliff", fontsize=12, fontweight="bold", loc="left")
a1.set_ylim(0, 100)

ages = ["5-17", "18-34", "35-64", "65+"]
ca2 = ca_age[(ca_age.geography == "Canada") & (ca_age.generation == "Second generation")]
# map CA age groups onto US bands: 0-14+15-24 ~ 5-17 approx; use 15-24, 25-34, 35-44+45-54, 55-64+65-74+75+
ca_map = {"5-17": ca2[ca2.age == "15 to 24 years"]["retention_mt"].values[0],
          "18-34": ca2[ca2.age == "25 to 34 years"]["retention_mt"].values[0],
          "35-64": (ca2[ca2.age == "35 to 44 years"]["chinese_mt"].values[0] +
                    ca2[ca2.age == "45 to 54 years"]["chinese_mt"].values[0] +
                    ca2[ca2.age == "55 to 64 years"]["chinese_mt"].values[0]) /
                   (ca2[ca2.age == "35 to 44 years"]["chinese_vm"].values[0] +
                    ca2[ca2.age == "45 to 54 years"]["chinese_vm"].values[0] +
                    ca2[ca2.age == "55 to 64 years"]["chinese_vm"].values[0]),
          "65+": (ca2[ca2.age == "65 to 74 years"]["chinese_mt"].values[0] +
                  ca2[ca2.age == "75 years and over"]["chinese_mt"].values[0]) /
                 (ca2[ca2.age == "65 to 74 years"]["chinese_vm"].values[0] +
                  ca2[ca2.age == "75 years and over"]["chinese_vm"].values[0])}
us_nat = us_age[us_age.nativity == "Native"].set_index("age_group")["share"]
a2.plot(ages, [ca_map[a] * 100 for a in ages], "o-", color=CA_RED, lw=2.5,
        label="Canada 2nd gen — mother tongue")
a2.plot(ages, [us_nat[a] * 100 for a in ages], "s--", color=US_BLUE, lw=2.5,
        label="US native-born — speaks Chinese at home")
a2.set_ylabel("Retention (%)")
a2.set_xlabel("Age group")
a2.set_title("Same age gradient in both countries", fontsize=12, fontweight="bold", loc="left")
a2.legend(frameon=False, fontsize=9)
a2.set_ylim(0, 55)
fig.tight_layout()
fig.savefig("charts/cliff_and_age.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 3
# Geography: within-country spread dwarfs the between-country gap.
fig, ax = plt.subplots(figsize=(10, 5.8))
ca2 = ca[ca.generation == "Second generation"].sort_values("retention_mt")
us_nat_s = pd.read_csv("data/us_enclave.csv")
us_nat_s = us_nat_s[us_nat_s.nativity == "Native"].sort_values("share")
y_ca = np.arange(len(ca2))
y_us = np.arange(len(us_nat_s)) + len(ca2) + 1
ax.barh(y_ca, ca2["retention_mt"] * 100, color=CA_RED, height=0.6,
        label="Canada CMAs — 2nd gen, Chinese mother tongue")
ax.barh(y_us, us_nat_s["share"] * 100, color=US_BLUE, height=0.6,
        label="US states — native-born, speaks Chinese at home")
for y, v, g in zip(y_ca, ca2["retention_mt"] * 100, ca2["geography"]):
    ax.text(v + 0.7, y, f"{g} {v:.1f}%", va="center", fontsize=10)
for y, v, g in zip(y_us, us_nat_s["share"] * 100, us_nat_s["state"]):
    ax.text(v + 0.7, y, f"{g} {v:.1f}%", va="center", fontsize=10)
ax.axvline(42.9, color=CA_RED, ls=":", lw=1.5)
ax.axvline(32.2, color=US_BLUE, ls=":", lw=1.5)
ax.set_yticks([])
ax.set_xlim(0, 68)
ax.set_xlabel("Retention among the native-born heritage population (%)")
ax.set_title("Place matters. Country doesn't.", fontsize=13, fontweight="bold", loc="left")
fig.text(0.07, 0.01,
         "Red = Canada CMAs, 2nd generation, Chinese mother tongue; blue = US states, native-born, speaks Chinese at home.\n"
         "Dotted lines: national averages (Canada 42.9% mother tongue; US 32.2% speaks Chinese at home). "
         "The two series measure slightly different things (see README);\n"
         "the point is the spread within each country, not the 10-point level gap between the two measures.",
         fontsize=8, color="#555555", va="bottom")
fig.tight_layout(rect=[0, 0.10, 1, 1])
fig.savefig("charts/geography.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 4
# Mandarin vs Cantonese: two waves, two lifecycles.
split = pd.read_csv("data/ca_mt_split.csv")
split_ca = split[split.geography == "Canada"]
fig, ax = plt.subplots(figsize=(10, 5.6))
langs = ["Mandarin", "Yue (Cantonese)", "Other Chinese*"]
gens = ["First generation", "Second generation", "Third generation or more"]
data = {}
for g in gens:
    sub = split_ca[split_ca.generation == g]
    tot = sub["count"].sum()
    man = sub[sub.mother_tongue == "Mandarin"]["count"].values[0] / tot * 100
    can = sub[sub.mother_tongue == "Yue (Cantonese)"]["count"].values[0] / tot * 100
    data[g] = (man, can, 100 - man - can)
x = np.arange(len(gens))
man = [data[g][0] for g in gens]
can = [data[g][1] for g in gens]
oth = [data[g][2] for g in gens]
ax.bar(x, man, 0.55, label="Mandarin", color=CA_RED)
ax.bar(x, can, 0.55, bottom=man, label="Cantonese (Yue)", color=GOLD)
ax.bar(x, oth, 0.55, bottom=np.array(man) + np.array(can), label="Other Chinese*", color=GREY)
for i, g in enumerate(gens):
    ax.text(i, man[i] / 2, f"{man[i]:.0f}%", ha="center", color="white", fontweight="bold")
    ax.text(i, man[i] + can[i] / 2, f"{can[i]:.0f}%", ha="center", color="white", fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(["Immigrants\n(1st generation)", "Second generation", "Third generation+"])
ax.set_ylabel("Share of Chinese mother-tongue population (%)")
ax.set_title("There is no single “Chinese” in Canada: Mandarin immigrates, Cantonese inherits",
             fontsize=12, fontweight="bold", loc="left")
ax.legend(frameon=False, fontsize=9.5)
ax.text(0, -16, "*Other: Hakka, Min Dong, Min Nan, Wu, Chinese n.o.s., Chinese languages n.i.e.  Source: Statistics Canada table 98-10-0617-01, 2021 Census.",
        fontsize=8, color="#555555")
fig.tight_layout()
fig.savefig("charts/mandarin_cantonese.png", dpi=150)
plt.close(fig)
print("charts done")
