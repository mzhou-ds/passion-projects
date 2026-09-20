"""04_boston_bq.py — the BQ funnel: what share of 2016 Boston finishers beat
their own qualifying standard on race day, by age group and sex; plus
pacing-archetype comparison Boston (all-qualified field) vs Berlin (open entry).
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# BAA qualifying standards in effect for the 2016 race (men / women), seconds
BQ_M = [(18, 3*3600+5*60), (35, 3*3600+10*60), (40, 3*3600+15*60),
        (45, 3*3600+25*60), (50, 3*3600+30*60), (55, 3*3600+40*60),
        (60, 3*3600+55*60), (65, 4*3600+10*60), (70, 4*3600+25*60),
        (75, 4*3600+40*60), (80, 4*3600+55*60)]
BQ_W = [(18, 3*3600+35*60), (35, 3*3600+40*60), (40, 3*3600+50*60),
        (45, 4*3600), (50, 4*3600+5*60), (55, 4*3600+20*60),
        (60, 4*3600+35*60), (65, 4*3600+50*60), (70, 5*3600+5*60),
        (75, 5*3600+20*60), (80, 5*3600+35*60)]


def bq_std(age, sex):
    table = BQ_M if sex == "M" else BQ_W
    std = table[-1][1]
    for lo, s in table:
        if age >= lo:
            std = s
    return std


bo = pd.read_pickle("output/boston_clean.pkl")
bo["bq_std"] = [bq_std(a, g) for a, g in zip(bo["Age"], bo["gender"])]
bo["beat_bq"] = bo["time_full_s"] <= bo["bq_std"]
bo["margin_min"] = (bo["bq_std"] - bo["time_full_s"]) / 60  # + = beat it

print(f"beat own BQ standard on race day: {bo['beat_bq'].mean():.3f}")
bo["age_group"] = pd.cut(bo["Age"], [17, 34, 39, 44, 49, 54, 59, 64, 120],
                         labels=["18-34", "35-39", "40-44", "45-49", "50-54",
                                 "55-59", "60-64", "65+"])
g = bo.groupby(["age_group", "gender"], observed=True).agg(
    n=("beat_bq", "size"), beat=("beat_bq", "mean"),
    med_margin=("margin_min", "median")).round(3)
print("\nbeat-BQ rate by age group / sex:")
print(g.to_string())
g.to_csv("output/boston_beat_bq.csv")

# ---- chart 4: beat-BQ rate by age group
fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(g.index.levels[0]))
w = 0.35
m = g.xs("M", level=1)["beat"] * 100
f = g.xs("F", level=1)["beat"] * 100
ax.bar(x - w/2, m, w, label="Men")
ax.bar(x + w/2, f, w, label="Women")
ax.set_xticks(x); ax.set_xticklabels(g.index.levels[0])
ax.set_ylabel("% who beat their BQ standard on race day")
ax.set_title("Boston 2016: everyone here qualified — how many re-cleared the bar?")
ax.legend()
plt.tight_layout()
plt.savefig("charts/04_boston_beat_bq.png", dpi=130)
plt.close()

# pacing archetypes at Boston vs Berlin: assign via Berlin centroids
cent = pd.read_csv("output/centroids.csv", index_col=0).values
names = json.load(open("output/archetype_names.json"))
REL = [f"rel{i}" for i in range(9)]
d = ((bo[REL].values[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
bo["archetype"] = [names[str(i)] for i in d]
be = pd.read_pickle("output/berlin_archetypes.pkl")
mix = pd.DataFrame({
    "Boston 2016 (qualified field)": bo["archetype"].value_counts(normalize=True) * 100,
    "Berlin 2016-19 (open entry)": be["archetype"].value_counts(normalize=True) * 100,
}).round(1)
print("\narchetype mix (%):")
print(mix.to_string())
mix.to_csv("output/archetype_mix_boston_berlin.csv")

fig, ax = plt.subplots(figsize=(10, 5.5))
mix.plot(kind="bar", ax=ax)
ax.set_ylabel("% of finishers")
ax.set_title("Pacing discipline: Boston's qualified field vs Berlin's open field")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig("charts/05_boston_vs_berlin.png", dpi=130)
plt.close()

# bonk rates compared
for name, dframe in [("boston", bo), ("berlin", be)]:
    segm = dframe[[f"seg{i}" for i in range(9)]].values
    km = np.array([5, 5, 5, 5, 5, 5, 5, 5, 2.195])
    p30 = (segm[:, :6] * km[:6]).sum(axis=1) / 30
    pl = (segm[:, 6:] * km[6:]).sum(axis=1) / 12.195
    print(f"{name} bonk rate: {((pl / p30 - 1) >= 0.12).mean():.3f}")

json.dump({"beat_bq_overall": round(float(bo["beat_bq"].mean()), 3)},
          open("output/boston_metrics.json", "w"), indent=1)
print("\ndone")
