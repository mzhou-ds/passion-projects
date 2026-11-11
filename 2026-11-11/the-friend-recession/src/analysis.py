#!/usr/bin/env python3
"""The Friend Recession — full analysis of ATUS 2023 time with friends.

Questions:
  1. When does friend time collapse, and does it ever come back?
  2. Is it marriage, kids, or work hours that does the damage? (WLS)
  3. Extensive margin (fewer friend-days) or intensive (shorter hangouts)?
  4. Do parents reclaim friend time on weekends? Does the empty nest rebound?
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#666666", "axes.labelcolor": "#222222",
                     "figure.dpi": 150})
C_FRIEND = "#1f6f8b"   # teal
C_FAM = "#e07a5f"      # terracotta
C_SPOUSE = "#81b29a"   # sage
C_ALONE = "#b0b0b0"
C_ACCENT = "#c0392b"

df = pd.read_pickle(DATA / "merged.pkl")
df = df[df.PRTAGE >= 18].copy()
w = df["TUFINLWGT"].values

def wmean(s, w):
    return float(np.average(s, weights=w))

def wse(s, w):
    """Weighted SE of a weighted mean (Taylor-ish, no replicate weights)."""
    s = np.asarray(s, float); w = np.asarray(w, float)
    m = np.average(s, weights=w)
    return float(np.sqrt(np.sum(w**2 * (s - m) ** 2) / (np.sum(w) ** 2)))

# ---------------------------------------------------------------- age curve
bands = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49",
         "50-54", "55-59", "60-64", "65-74", "75+"]
rows = []
for b in bands:
    x = df[df.age_band == b]
    rows.append({
        "band": b, "n": len(x),
        "friend": wmean(x.TRTFRIEND, x.w), "friend_se": wse(x.TRTFRIEND, x.w),
        "any_friend": wmean((x.TRTFRIEND > 0).astype(float), x.w),
        "cond": wmean(x.loc[x.TRTFRIEND > 0, "TRTFRIEND"], x.loc[x.TRTFRIEND > 0, "w"]),
        "family": wmean(x.TRTFAMILY, x.w), "spouse": wmean(x.TRTSPOUSE, x.w),
        "alone": wmean(x.TRTALONE, x.w),
        "social": wmean(x.TRTFAMILY + x.TRTFRIEND, x.w),
    })
age = pd.DataFrame(rows)
age.to_csv(DATA / "age_curve.csv", index=False)
print(age.round(1).to_string(index=False))

base = age.loc[age.band == "18-24", "friend"].iloc[0]
print(f"\n18-24 baseline: {base:.1f} min/day = {base*365/60:.0f} hrs/yr")
for _, r in age.iterrows():
    print(f"  {r.band:6s} {r.friend:5.1f} min/day ({r.friend*365/60:4.0f} hrs/yr)  "
          f"loss vs 18-24: {(base-r.friend)*365/60:4.0f} hrs/yr  "
          f"friend-days: {r.any_friend*100:4.1f}% of days ({r.any_friend*30:4.1f}/month)")

# ------------------------------------------------------------- regression
df["workhrs"] = df.TEHRUSLT.clip(0, 80).fillna(0)
df["nkids"] = df.TRCHILDNUM
df["youngest"] = df.TRYHHCHILD  # -1 = no kids <18
df["age_c"] = df.PRTAGE
df["age_c2"] = df.PRTAGE ** 2

def run_wls(data, label):
    X = pd.DataFrame({
        "const": 1.0,
        "partnered": data.partnered.astype(float),
        "any_kid": data.any_kid.astype(float),
        "nkids": data.nkids,
        "workhrs": data.workhrs,
        "female": data.female.astype(float),
        "weekend": data.weekend.astype(float),
        "age": data.age_c, "age2": data.age_c2 / 100,
    })
    y = data.TRTFRIEND
    m = sm.WLS(y, X, weights=data.w).fit(cov_type="HC1")
    print(f"\n--- WLS friend minutes/day: {label} (n={len(data)}) ---")
    print(m.summary2().tables[1].round(2).to_string())
    return m

m_all = run_wls(df, "all adults 18+")
m_mid = run_wls(df[(df.PRTAGE >= 25) & (df.PRTAGE <= 54)], "ages 25-54 only")

# youngest-child-age version (parents only, 25-54)
par = df[(df.PRTAGE >= 25) & (df.PRTAGE <= 54) & (df.any_kid)].copy()
par["kid02"] = ((par.youngest >= 0) & (par.youngest <= 2)).astype(float)
par["kid35"] = ((par.youngest >= 3) & (par.youngest <= 5)).astype(float)
par["kid612"] = ((par.youngest >= 6) & (par.youngest <= 12)).astype(float)
par["kid1317"] = (par.youngest >= 13).astype(float)
X = pd.DataFrame({"const": 1.0, "partnered": par.partnered.astype(float),
                  "kid02": par.kid02, "kid35": par.kid35, "kid612": par.kid612,
                  "workhrs": par.workhrs, "female": par.female.astype(float),
                  "weekend": par.weekend.astype(float),
                  "age": par.age_c, "age2": par.age_c2 / 100})
mm = sm.WLS(par.TRTFRIEND, X, weights=par.w).fit(cov_type="HC1")
print("\n--- WLS parents 25-54, youngest-child age (ref: youngest 13-17) ---")
print(mm.summary2().tables[1].round(2).to_string())

# archetype predictions from m_mid
def predict(partnered, any_kid, nkids, workhrs, female, weekend, age):
    X = pd.DataFrame({"const": [1.0], "partnered": [partnered], "any_kid": [any_kid],
                      "nkids": [nkids], "workhrs": [workhrs], "female": [female],
                      "weekend": [weekend], "age": [age], "age2": [age ** 2 / 100]})
    return float(m_mid.predict(X)[0])

print("\n--- Predicted friend minutes/day, weekday, 40 hrs/wk, age 35 (from 25-54 model) ---")
for lab, kw in [("single, no kids", dict(partnered=0, any_kid=0, nkids=0)),
                ("partnered, no kids", dict(partnered=1, any_kid=0, nkids=0)),
                ("partnered, 2 kids", dict(partnered=1, any_kid=1, nkids=2)),
                ("single, 2 kids", dict(partnered=0, any_kid=1, nkids=2))]:
    print(f"  {lab:20s} {predict(workhrs=40, female=0, weekend=0, age=35, **kw):6.1f} min/day")

# ------------------------------------------------- extensive vs intensive
print("\n--- Decomposition of the 18-24 -> 30-34 drop ---")
y = age[age.band == "18-24"].iloc[0]; o = age[age.band == "30-34"].iloc[0]
d_mean = y.friend - o.friend
d_ext = (y.any_friend - o.any_friend) * y.cond          # fewer friend-days, at young conditional length
d_int = o.any_friend * (y.cond - o.cond)          # shorter hangouts, at old frequency
print(f"  total drop: {d_mean:.1f} min/day; extensive (fewer days): {d_ext:.1f} ({d_ext/d_mean*100:.0f}%); "
      f"intensive (shorter): {d_int:.1f} ({d_int/d_mean*100:.0f}%)")
print(f"  friend-days: {y.any_friend*30:.1f}/month at 18-24 -> {o.any_friend*30:.1f}/month at 30-34")

# ------------------------------------------------------------- weekend test
print("\n--- Friend minutes: weekday vs weekend, by life stage (25-54) ---")
mid = df[(df.PRTAGE >= 25) & (df.PRTAGE <= 54)].copy()
mid["stage"] = np.where(mid.any_kid, np.where(mid.partnered, "partnered + kids", "single + kids"),
                        np.where(mid.partnered, "partnered, no kids", "single, no kids"))
for s, x in mid.groupby("stage"):
    wd = x[~x.weekend]; we = x[x.weekend]
    print(f"  {s:20s} weekday {wmean(wd.TRTFRIEND, wd.w):5.1f}  weekend {wmean(we.TRTFRIEND, we.w):5.1f}  "
          f"weekend share of week: {wmean(we.TRTFRIEND, we.w)*2/(wmean(wd.TRTFRIEND, wd.w)*5 + wmean(we.TRTFRIEND, we.w)*2)*100:.0f}%")

# ------------------------------------------------------------- rebound test
print("\n--- The rebound test: 55+ with no kids at home vs 25-29 single, no kids ---")
old = df[(df.PRTAGE >= 55) & (df.TRCHILDNUM == 0)]
young = df[(df.PRTAGE >= 25) & (df.PRTAGE <= 29) & (~df.partnered) & (~df.any_kid)]
print(f"  55+ no kids at home: {wmean(old.TRTFRIEND, old.w):.1f} min/day, friend-days {wmean((old.TRTFRIEND>0).astype(float), old.w)*30:.1f}/month (n={len(old)})")
print(f"  25-29 single no kids: {wmean(young.TRTFRIEND, young.w):.1f} min/day, friend-days {wmean((young.TRTFRIEND>0).astype(float), young.w)*30:.1f}/month (n={len(young)})")
print(f"  recovery: {wmean(old.TRTFRIEND, old.w)/wmean(young.TRTFRIEND, young.w)*100:.0f}% of the young-single level")
# retirees (65+, not working) vs working 65+
ret = df[(df.PRTAGE >= 65) & (df.TELFS == 5)]  # 5 = not in labor force
wrk = df[(df.PRTAGE >= 65) & (df.TELFS != 5)]
print(f"  65+ not in labor force: {wmean(ret.TRTFRIEND, ret.w):.1f} min/day (n={len(ret)})")
print(f"  65+ in labor force:     {wmean(wrk.TRTFRIEND, wrk.w):.1f} min/day (n={len(wrk)})")

# ------------------------------------------------------------- sex split
print("\n--- Friend minutes by sex and age ---")
for b in ["18-24", "30-34", "40-44", "55-59", "65-74"]:
    x = df[df.age_band == b]
    print(f"  {b}: men {wmean(x[~x.female].TRTFRIEND, x[~x.female].w):5.1f}  women {wmean(x[x.female].TRTFRIEND, x[x.female].w):5.1f}")

# ------------------------------------------------------------------ charts
# 1. Age curve with SE band
fig, ax = plt.subplots(figsize=(9, 4.6))
xpos = np.arange(len(age))
ax.errorbar(xpos, age.friend, yerr=1.96 * age.friend_se, fmt="o-", color=C_FRIEND,
            lw=2, capsize=3, markersize=5)
ax.axhline(base, color=C_FRIEND, ls=":", lw=1, alpha=0.6)
ax.set_xticks(xpos); ax.set_xticklabels(age.band, rotation=30)
ax.set_ylabel("Minutes with friends per day")
ax.set_title("Friend time collapses at 30 — and never comes back", fontweight="bold", loc="left")
ax.annotate("58 min/day at 18–24", (0, base), xytext=(0.4, base + 14), fontsize=10, color=C_FRIEND)
ax.annotate("~19 min/day, flat from 30 to 75+", (3, 19), xytext=(4.2, 34), fontsize=10)
ax.set_ylim(0, 80)
fig.tight_layout(); fig.savefig(CH / "age_curve.png"); plt.close(fig)

# 2. Extensive vs intensive: friend-days per month + conditional length
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.2))
a1.bar(xpos, age.any_friend * 30, color=C_FRIEND, width=0.7)
a1.set_xticks(xpos); a1.set_xticklabels(age.band, rotation=30)
a1.set_ylabel("Days with any friend time / month")
a1.set_title("Fewer friend-days", fontweight="bold", loc="left")
a2.bar(xpos, age.cond / 60, color=C_ACCENT, width=0.7)
a2.set_xticks(xpos); a2.set_xticklabels(age.band, rotation=30)
a2.set_ylabel("Hours with friends, on friend-days")
a2.set_title("But hangouts stay long", fontweight="bold", loc="left")
fig.suptitle("The collapse is extensive, not intensive", fontweight="bold", x=0.02, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.92]); fig.savefig(CH / "extensive_vs_intensive.png"); plt.close(fig)

# 3. Regression coefficients (25-54 model)
coef = m_mid.params.drop("const"); se = m_mid.bse.drop("const")
labels = {"partnered": "Partnered\n(vs single)", "any_kid": "Has kids <18\n(vs none)",
          "nkids": "Each extra kid", "workhrs": "Each work hour/wk",
          "female": "Female (vs male)", "weekend": "Weekend day\n(vs weekday)",
          "age": "Each year of age", "age2": "Age² (per 100)"}
order = ["partnered", "any_kid", "nkids", "workhrs", "female", "weekend"]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
vals = [coef[o] for o in order]; errs = [1.96 * se[o] for o in order]
ypos = np.arange(len(order))
ax.barh(ypos, vals, xerr=errs, color=[C_ACCENT if v < 0 else C_FRIEND for v in vals], height=0.6)
ax.set_yticks(ypos); ax.set_yticklabels([labels[o] for o in order])
ax.axvline(0, color="#333", lw=1)
ax.set_xlabel("Minutes of friend time per day (WLS, ages 25–54, 95% CI)")
ax.set_title("What actually costs you friend time: the partner, not the kids — and not work",
             fontweight="bold", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(CH / "regression.png"); plt.close(fig)

# 4. Friends vs alone time: the two lines that move in opposite directions
# (BLS "with whom" categories can overlap when several people are present,
# so this is a comparison of two series, not a partition of the day.)
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(xpos, age.friend / 60, "o-", color=C_FRIEND, lw=2.5, markersize=5, label="With friends")
ax.plot(xpos, age.alone / 60, "s-", color="#888888", lw=2, markersize=4, label="Alone")
ax.set_xticks(xpos); ax.set_xticklabels(age.band, rotation=30)
ax.set_ylabel("Hours per day")
ax.set_title("Friends shrink to a sliver while alone time grows to 8 hours a day",
             fontweight="bold", loc="left", fontsize=11)
ax.annotate("friends: 58 → 19 min/day", (0, 0.97), xytext=(0.5, 2.6), fontsize=10, color=C_FRIEND)
ax.annotate("alone: 5.3 → 8.0 hrs/day", (10, 8.0), xytext=(7.2, 6.4), fontsize=10, color="#666666")
ax.set_ylim(0, 9)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(CH / "substitution.png"); plt.close(fig)

# 5. Rebound gap: archetype bars
arch = pd.DataFrame({
    "group": ["18–24\n(all)", "25–29 single\nno kids", "35 partnered\nno kids*", "35 partnered\n2 kids*", "55+ no kids\nat home", "65+ retired"],
    "mins": [base,
             wmean(young.TRTFRIEND, young.w),
             predict(partnered=1, any_kid=0, nkids=0, workhrs=40, female=0, weekend=0, age=35),
             predict(partnered=1, any_kid=1, nkids=2, workhrs=40, female=0, weekend=0, age=35),
             wmean(old.TRTFRIEND, old.w),
             wmean(ret.TRTFRIEND, ret.w)],
})
fig, ax = plt.subplots(figsize=(9, 4.4))
cols = [C_FRIEND, C_FRIEND, C_FAM, C_ACCENT, "#888888", "#888888"]
ax.bar(np.arange(len(arch)), arch.mins, color=cols, width=0.65)
ax.set_xticks(np.arange(len(arch))); ax.set_xticklabels(arch.group)
ax.set_ylabel("Minutes with friends per day")
ax.set_title("The empty nest does not refill: friend time never returns to young-adult levels",
             fontweight="bold", loc="left", fontsize=11)
for i, v in enumerate(arch.mins):
    ax.text(i, v + 1.5, f"{v:.0f}", ha="center", fontsize=10)
ax.set_ylim(0, max(arch.mins) * 1.18)
fig.tight_layout(); fig.savefig(CH / "rebound_gap.png"); plt.close(fig)

print("\ncharts written to", CH)
print("archetypes:\n", arch.round(1).to_string(index=False))
