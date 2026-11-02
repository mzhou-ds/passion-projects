"""Charts for The Friendless Day. All figures read data/results.json, model.json,
and friend_minutes_by_hour.csv. Style matches the repo: muted, labeled, no junk."""
import json, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parent.parent
CH = ROOT / "charts"; CH.mkdir(exist_ok=True)
R = json.loads((ROOT / "data/results.json").read_text())
M = json.loads((ROOT / "data/model.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
RED, BLUE, PURP, GREY = "#c0392b", "#2471a3", "#7d3c98", "#7f8c8d"
def save(fig, name):
    fig.tight_layout(); fig.savefig(CH / name, bbox_inches="tight"); plt.close(fig); print(name)

# 1 - yearly: zero-friend-day share + friend mean (twin panels)
y = pd.DataFrame(R["yearly"])
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
axes[0].plot(y["year"], y["zero_friend_pct"], color=RED, lw=2, marker="o", ms=3)
axes[0].axvspan(2020, 2020.9, color="#f5b041", alpha=0.25)
axes[0].set_title("Share of days with zero friend contact (%)")
axes[0].set_ylabel("% of diary days")
axes[1].plot(y["year"], y["friend_mean"], color=BLUE, lw=2, marker="o", ms=3)
axes[1].axvspan(2020, 2020.9, color="#f5b041", alpha=0.25)
axes[1].set_title("Mean friend minutes per day")
axes[1].set_ylabel("Minutes")
for ax in axes: ax.set_xlabel("Diary year (2020 excluded: collection break)")
fig.suptitle("The friend day collapsed and never came back, 2003-2025", fontweight="bold")
save(fig, "01_zero_friend_yearly.png")

# 2 - decomposition: extensive vs intensive, by tie
rows = []
for lbl, lab in [("friend", "Friends"), ("family", "Family"), ("partner", "Spouse/partner"), ("alone", "Alone")]:
    d = R[lbl + "_decomp"]; rows.append((lab, d["extensive"], d["intensive"]))
fig, ax = plt.subplots(figsize=(7.2, 3.8))
labs = [r[0] for r in rows]
ax.barh(labs, [r[1] for r in rows], color=RED, label="Extensive: fewer days with any contact")
ax.barh(labs, [r[2] for r in rows], left=[r[1] for r in rows], color=BLUE,
        label="Intensive: shorter contact on contact days")
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Change in mean minutes per day, 2003-07 to 2021-25")
ax.set_title("Where the minutes went: almost all extensive, except alone time")
ax.legend(frameon=False, loc="lower right", fontsize=8)
save(fig, "02_decomposition.png")

# 3 - buckets of friend minutes by era (stacked)
b = pd.DataFrame(R["friend_buckets"]).set_index("era")
fig, ax = plt.subplots(figsize=(7.2, 3.8))
left = pd.Series(0.0, index=b.index)
for col, c in [("zero", GREY), ("1-29", "#f5b041"), ("30-119", BLUE), ("120+", "#27ae60")]:
    ax.bar(b.index, b[col], bottom=left, label=col + " min", color=c); left += b[col]
ax.set_ylabel("% of diary days"); ax.set_title("Friend days by length: the 2+ hour day halved")
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
save(fig, "03_buckets.png")

# 4 - zero-friend share by age band, first vs last era
z = pd.DataFrame(R["zero_by_age"])
p = z.pivot(index="ageband", columns="era", values="zero_friend_pct")
order = ["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]
p = p.reindex(order)
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = range(len(order)); w = 0.38
ax.bar([i - w/2 for i in x], p["2003-07"], w, label="2003-07", color=BLUE)
ax.bar([i + w/2 for i in x], p["2021-25"], w, label="2021-25", color=RED)
ax.set_xticks(list(x)); ax.set_xticklabels(order)
ax.set_ylabel("% of days with zero friend contact")
ax.set_title("Every age lost friend days; the young lost the most")
ax.legend(frameon=False)
save(fig, "04_zero_by_age.png")

# 5 - friend minutes by hour of day, first vs last era
h = pd.read_csv(ROOT / "data/friend_minutes_by_hour.csv")
h["tot"] = h.groupby("era")["wmin"].transform("sum"); h["share"] = 100 * h["wmin"] / h["tot"]
hp = h.pivot(index="hour", columns="era", values="share")
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.plot(hp.index, hp["2003-07"], color=BLUE, lw=2, label="2003-07")
ax.plot(hp.index, hp["2021-25"], color=RED, lw=2, label="2021-25")
ax.set_xlabel("Start hour of friend episode"); ax.set_ylabel("Share of friend minutes (%)")
ax.set_title("Surviving friend time moved toward midday, away from late night")
ax.legend(frameon=False)
save(fig, "05_friend_by_hour.png")

# 6 - SHAP importance, both models
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharex=False)
for ax, key, title in [(axes[0], "zero_friend", "Zero-friend day (AUC 0.70)"),
                       (axes[1], "zero_family", "Zero-family day (AUC 0.85)")]:
    s = pd.DataFrame(M[key]["shap"]).head(7).iloc[::-1]
    ax.barh(s["feature"], s["mean_abs_shap"], color=RED if key == "zero_friend" else PURP)
    ax.set_title(title)
fig.suptitle("What sorts a zero-contact day: era for friends, household for family", fontweight="bold")
save(fig, "06_shap.png")
