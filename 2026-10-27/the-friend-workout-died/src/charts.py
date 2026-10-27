"""Charts for Working Out Alone — all figures read output/*.csv + results.json
written by analyze.py. Style matches the rest of the repo: muted, labeled,
no chartjunk."""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)
R = json.loads((OUT / "results.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
SOLO = "#c0392b"
SOCIAL = "#2471a3"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CH / name, bbox_inches="tight")
    plt.close(fig)
    print(name)


# 1 — the headline trend: alone share of fitness minutes by year
y = pd.DataFrame(R["yearly"])
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.plot(y["year"], y["alone_share_min"] * 100, color=SOLO, lw=2, marker="o", ms=3)
ax.axvspan(2020.6, 2025.4, color="#f5b041", alpha=0.12)
ax.set_ylabel("Share of exercise minutes done alone (%)")
ax.set_xlabel("Diary year (2020 excluded: pandemic collection break)")
ax.set_title("Exercise went solo: alone share of U.S. fitness minutes, 2003–2025")
save(fig, "01_alone_trend.png")

# 2 — who the company is, when there is company (era stacked minutes)
e = pd.DataFrame(R["era_table"])
e = e[e["set"] == "fitness"].set_index("era")
cats = [("alone_share_min", "Alone", SOLO),
        ("friend_share_min", "With friends", "#27ae60"),
        ("partner_share_min", "With spouse/partner", SOCIAL),
        ("family_share_min", "With family", "#7d3c98")]
fig, ax = plt.subplots(figsize=(7.2, 3.8))
left = pd.Series(0.0, index=e.index)
for col, lab, c in cats:
    ax.bar(e.index, e[col] * 100, bottom=left, label=lab, color=c)
    left = left + e[col] * 100
ax.set_ylabel("Share of fitness minutes (%)")
ax.set_title("Companion mix of America's exercise minutes, by era")
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
save(fig, "02_companion_mix.png")

# 3 — duration: social episodes last longer
cc = pd.DataFrame(R["companion_classes"])
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ccp = cc.set_index("companion").reindex(
    ["Alone", "Friends", "Spouse/partner", "Family", "Other people"]).dropna()
ax.barh(ccp.index, ccp["mean_dur"],
        color=[SOLO if i == "Alone" else SOCIAL for i in ccp.index])
for i, v in enumerate(ccp["mean_dur"]):
    ax.text(v + 1, i, f"{v:.0f} min", va="center")
ax.set_xlabel("Mean episode length (minutes, weighted)")
ax.set_title("Company is a duration drug: exercise lasts longer with people")
save(fig, "03_duration.png")

# 4 — by activity: alone share then vs now
ba = pd.read_csv(OUT / "by_activity.csv").dropna(subset=["alone_min_0307", "alone_min_2125"])
ba = ba.sort_values("alone_min_2125")
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.barh(ba["label"], ba["alone_min_0307"] * 100, height=0.38, color="#aab7b8", label="2003–07")
ax.barh(ba["label"], ba["alone_min_2125"] * 100, height=0.38, color=SOLO, label="2021–25")
ax.set_xlabel("Share of minutes done alone (%)")
ax.set_title("Which workouts went solo, activity by activity")
ax.legend(frameon=False)
save(fig, "04_by_activity.png")

# 5 — the gym: share of minutes and alone share inside it
g = pd.DataFrame(R["gym"])
fig, ax1 = plt.subplots(figsize=(7.2, 3.8))
ax1.bar(g["era"], g["gym_share_min"] * 100, color="#aab7b8", width=0.5,
        label="Gym share of all fitness minutes")
ax1.set_ylabel("Gym share of fitness minutes (%)", color="#616a6b")
ax2 = ax1.twinx()
ax2.plot(g["era"], g["gym_alone_share_min"] * 100, color=SOLO, lw=2, marker="o",
         label="Alone share inside the gym")
ax2.set_ylabel("Alone share of gym minutes (%)", color=SOLO)
ax1.set_title("The gym: a shrinking, solo room")
save(fig, "05_gym.png")

# 6 — participation rose while company fell (two panels)
p = pd.DataFrame(R["participation"])
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
axes[0].plot(p["TUYEAR"], p["participation"] * 100, color=SOCIAL, lw=2, marker="o", ms=3)
axes[0].set_title("Share who exercised that day (%)")
axes[1].plot(p["TUYEAR"], p["min_per_capita"], color=SOCIAL, lw=2, marker="o", ms=3)
axes[1].set_title("Exercise minutes per capita per day")
save(fig, "06_participation.png")
print("done")
