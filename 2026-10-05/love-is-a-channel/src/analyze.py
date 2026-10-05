#!/usr/bin/env python3
"""
"Love is a channel business" — analysis pipeline.

Reads data/couples.csv (built by fetch_hcmst.py) and produces:
  data/findings.json      every headline number used in the README
  charts/*.png            publication figures
  site/data.js            model grid for the interactive scorecard

Methods (honest version):
  * Channel shift  : unweighted shares of primary meeting channel by
                     relationship-start decade. Early cohorts are couples
                     still (or most recently) partnered in 2017, so old
                     decades over-represent long survivors — flagged.
  * Survival       : Kaplan-Meier (hand-rolled, no lifelines dependency)
                     from relationship start, event = breakup, censor =
                     last survey wave / partner death. Log-rank test
                     hand-rolled. This is a current/most-recent-partner
                     sample, so absolute levels run optimistic vs. a true
                     cohort of all relationships ever started; channel
                     *comparisons* are the defensible read.
  * ML             : XGBoost classifier, breakup by the 2022 wave among
                     couples partnered in 2017 and re-interviewed in
                     2022 (horizon ~5 yrs). Stratified 75/25 split,
                     AUC reported for XGB and a logistic baseline.
                     SHAP (TreeExplainer) for interpretation.
  * Channel premium: counterfactual average predicted breakup risk with
                     everyone's channel set to c, covariates as observed
                     (g-computation on the fitted model). Bootstrap CIs.
"""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import xgboost as xgb
import shap

warnings.filterwarnings("ignore")
rng = np.random.default_rng(7)

HERE = Path(__file__).resolve().parent.parent
CH = HERE / "charts"; CH.mkdir(exist_ok=True)
CHAN_ORDER = ["online", "friends", "family", "school", "work",
              "bar_social", "church", "other"]
CHAN_LABEL = {"online": "Online", "friends": "Through friends",
              "family": "Through family", "school": "School",
              "work": "Work", "bar_social": "Bar / social",
              "church": "Church", "other": "Other"}
CHAN_COLOR = {"online": "#d1495b", "friends": "#1d7874", "family": "#f2a541",
              "school": "#4a6fa5", "work": "#7d5ba6", "bar_social": "#8c5e3c",
              "church": "#5a7d2a", "other": "#9aa0a6"}
plt.rcParams.update({"font.size": 10, "axes.titlesize": 12,
                     "figure.dpi": 200, "savefig.bbox": "tight"})

df = pd.read_csv(HERE / "data" / "couples.csv")
F = {"n_couples": int(len(df)),
     "year_range": [int(df.start_year.min()), int(df.start_year.max())]}
print("rows:", len(df))

# ============================================================ 1. channel shift
df["decade"] = (df.start_year // 10 * 10).astype(int)
dec = df[df.decade.between(1940, 2010)]
tab = (pd.crosstab(dec.decade, dec.channel, normalize="index") * 100)
tab = tab.reindex(columns=[c for c in CHAN_ORDER if c in tab], fill_value=0)
F["channel_share_by_decade_pct"] = {
    str(int(d)): {c: round(float(tab.loc[d, c]), 1) for c in tab.columns}
    for d in tab.index}
F["decade_n"] = {str(int(d)): int((dec.decade == d).sum()) for d in tab.index}

# the year online passed friends / family (5-yr rolling, annual starts >=1990)
ann = df[df.start_year.between(1985, 2017)]
sh = (pd.crosstab(ann.start_year, ann.channel, normalize="index") * 100)
for c in CHAN_ORDER:
    if c not in sh: sh[c] = 0.0
roll = sh[CHAN_ORDER].rolling(5, center=True, min_periods=3).mean()
def crossed(a, b):
    d = roll[a] - roll[b]
    yrs = [int(y) for y in roll.index[d > 0]]
    return yrs[0] if yrs else None
F["online_passes_friends_year"] = crossed("online", "friends")
F["online_passes_family_year"] = crossed("online", "family")
F["online_share_2010s_pct"] = round(float(
    sh.loc[sh.index >= 2010, "online"].mean()), 1)
F["online_share_1990s_pct"] = round(float(
    sh.loc[(sh.index >= 1990) & (sh.index < 2000), "online"].mean()), 1)
F["friends_share_1970s_pct"] = round(float(
    sh.loc[(sh.index >= 1970) & (sh.index < 1980), "friends"].mean()), 1)
F["friends_share_2010s_pct"] = round(float(
    sh.loc[sh.index >= 2010, "friends"].mean()), 1)

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.stackplot(tab.index + 5, [tab[c] for c in tab.columns],
             labels=[CHAN_LABEL[c] for c in tab.columns],
             colors=[CHAN_COLOR[c] for c in tab.columns], alpha=.92)
ax.set_xlim(1940, 2020); ax.set_ylim(0, 100)
ax.set_xlabel("Relationship start decade"); ax.set_ylabel("Share of couples (%)")
ax.set_title("How couples met, by the decade the relationship started")
ax.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.14))
fig.savefig(CH / "channel_shift.png"); plt.close(fig)

# ============================================================ 2. survival (KM)
def kaplan_meier(t, e):
    order = np.argsort(t); t, e = np.asarray(t)[order], np.asarray(e)[order]
    times, surv, var_sum, s = [0.0], [1.0], 0.0, 1.0
    for ut in np.unique(t[e == 1]):
        n_risk = (t >= ut).sum(); d = ((t == ut) & (e == 1)).sum()
        if n_risk == 0: continue
        s *= (1 - d / n_risk)
        var_sum += d / (n_risk * (n_risk - d)) if n_risk > d else 0
        times.append(float(ut)); surv.append(float(s))
    times, surv = np.array(times), np.array(surv)
    se = surv * np.sqrt(var_sum) if surv[-1] > 0 else np.zeros_like(surv)
    # proper Greenwood along the curve
    ses, vs, s2 = [], 0.0, 1.0
    for i in range(1, len(times)):
        seg_t, seg_e = t, e
        n_risk = (seg_t >= times[i]).sum()
        d = ((seg_t == times[i]) & (seg_e == 1)).sum()
        if n_risk > d and d > 0: vs += d / (n_risk * (n_risk - d))
        ses.append(surv[i] * np.sqrt(vs))
    return times, surv, np.array([0.0] + ses)

def logrank(t1, e1, t2, e2):
    t = np.concatenate([t1, t2]); e = np.concatenate([e1, e2])
    g = np.array([0]*len(t1) + [1]*len(t2))
    O1 = E1 = V = 0.0
    for ut in np.unique(t[e == 1]):
        risk = t >= ut
        n, n1 = risk.sum(), (risk & (g == 0)).sum()
        d = ((t == ut) & (e == 1)).sum(); d1 = ((t == ut) & (e == 1) & (g == 0)).sum()
        if n <= 1: continue
        O1 += d1; E1 += d * n1 / n
        V += (n1 * (n - n1) * d * (n - d)) / (n**2 * (n - 1))
    z = (O1 - E1) / np.sqrt(V) if V > 0 else 0.0
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))

km = {}
fig, ax = plt.subplots(figsize=(9, 5))
for c in CHAN_ORDER:
    s = df[df.channel == c]
    if len(s) < 80: continue
    t_, s_, se_ = kaplan_meier(s.duration_yrs.values, s.broke_up.values)
    km[c] = (t_, s_)
    ax.step(t_, s_ * 100, where="post", label=f"{CHAN_LABEL[c]} (n={len(s)})",
            color=CHAN_COLOR[c], lw=1.8)
    ax.fill_between(t_, (s_ - 1.96*se_)*100, (s_ + 1.96*se_)*100,
                    step="post", color=CHAN_COLOR[c], alpha=.12)
ax.set_xlim(0, 40); ax.set_ylim(35, 101)
ax.set_xlabel("Years since relationship started")
ax.set_ylabel("Still together (%)")
ax.set_title("Relationship survival by meeting channel (Kaplan–Meier)")
ax.legend(fontsize=8, loc="lower left")
fig.savefig(CH / "km_by_channel.png"); plt.close(fig)

def surv_at(c, yr):
    t_, s_ = km[c]
    idx = np.where(t_ <= yr)[0]
    return float(s_[idx[-1]]) if len(idx) else 1.0

def median_surv(c):
    t_, s_ = km[c]
    below = t_[s_ <= 0.5]
    return float(below[0]) if len(below) else None

F["survival_by_channel"] = {}
for c in km:
    F["survival_by_channel"][c] = {
        "n": int((df.channel == c).sum()),
        "s1": round(surv_at(c, 1) * 100, 1),
        "s3": round(surv_at(c, 3) * 100, 1),
        "s5": round(surv_at(c, 5) * 100, 1),
        "s10": round(surv_at(c, 10) * 100, 1),
        "median_yrs": (round(median_surv(c), 1) if median_surv(c) else None)}
# log-rank: online vs friends; friends vs all-others
o, fr = df[df.channel == "online"], df[df.channel == "friends"]
z, p = logrank(o.duration_yrs, o.broke_up, fr.duration_yrs, fr.broke_up)
F["logrank_online_vs_friends"] = {"z": round(z, 2), "p": f"{p:.2e}"}
rest = df[df.channel != "friends"]
z, p = logrank(fr.duration_yrs, fr.broke_up, rest.duration_yrs, rest.broke_up)
F["logrank_friends_vs_rest"] = {"z": round(z, 2), "p": f"{p:.2e}"}

# raw cumulative breakup at 1/3/5 yrs among couples with full windows
haz = {}
for c in CHAN_ORDER:
    s = df[df.channel == c]
    row = {}
    for h in (1, 3, 5):
        elig = s[(s.broke_up == 1) | (s.duration_yrs >= h)]
        if len(elig) >= 30:
            row[f"break_{h}yr_pct"] = round(float(
                (elig.broke_up[elig.duration_yrs <= h + 1e-9] == 1).mean() * 100), 1) \
                if False else round(float(
                ((elig.broke_up == 1) & (elig.duration_yrs <= h)).mean() * 100), 1)
            row[f"n_{h}yr"] = int(len(elig))
    haz[c] = row
F["hazard_windows_raw"] = haz

# descriptive confound snapshot by channel
conf = (df.groupby("channel")
        .agg(n=("caseid", "size"), age_start=("age_at_start", "mean"),
             married_w1=("married_w1", "mean"), same_sex=("same_sex", "mean"),
             educ_gap=("educ_gap", "mean"),
             start_year=("start_year", "mean")).round(2))
F["confounds_by_channel"] = {c: {k: (float(v) if not isinstance(v, (int, np.integer)) else int(v))
                                 for k, v in conf.loc[c].items()}
                             for c in conf.index}

# ============================================ 3. friend-network effect (raw+adj)
young = df[(df.start_year >= 2005) & (df.partnered_w1 == 1)].copy()
# observed >=5 yrs or broke within 5: use survival S(5) contrast instead
F["friend_effect"] = {
    "km_s5_friends": F["survival_by_channel"]["friends"]["s5"],
    "km_s5_online": F["survival_by_channel"]["online"]["s5"],
    "km_s5_family": F["survival_by_channel"]["family"]["s5"],
    "met_thru_friends_share_1970s_pct": round(float(tab.loc[1970, "friends"]), 1),
    "met_thru_friends_share_2010s_pct": round(float(tab.loc[2010, "friends"]), 1)}

# ============================================================ 4. ML (XGB+SHAP)
ml = df[(df.partnered_w1 == 1) & (df.in_w3 == 1)].copy()
ml["y"] = ml["unpartnered_w3"].astype(int)
# drop partner-death endings misread as breakups is not possible at w3
# (death is coded separately in w3_partner_passaway_*; unpartnered at w3
# after a death shows as unpartnered) -> acknowledged in README caveats.
FEATS = ["age_at_start", "start_year", "rel_age_2017",
         "educ_resp_cat", "educ_gap", "mother_educ_gap",
         "married_w1", "cohab_before_marriage", "same_sex", "female",
         "met_online", "met_via_app", "met_thru_friends", "times_married",
         "time_met_to_rel_yrs"]
ml["rel_age_2017"] = 2017.55 - ml["start_frac"]
ml = ml.dropna(subset=FEATS + ["y", "channel"])
for c in CHAN_ORDER:
    ml[f"ch_{c}"] = (ml.channel == c).astype(int)
XCOLS = FEATS + [f"ch_{c}" for c in CHAN_ORDER if c != "friends"]
X, y = ml[XCOLS].astype(float), ml["y"].values
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, random_state=7,
                                     stratify=y)
model = xgb.XGBClassifier(n_estimators=400, max_depth=3, learning_rate=.05,
                          subsample=.85, colsample_bytree=.85,
                          eval_metric="logloss", random_state=7)
model.fit(Xtr, ytr)
pred = model.predict_proba(Xte)[:, 1]
auc = roc_auc_score(yte, pred)
logit = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
logit.fit(Xtr, ytr)
auc_log = roc_auc_score(yte, logit.predict_proba(Xte)[:, 1])
F["ml"] = {"n": int(len(ml)), "breakup_rate_pct": round(float(y.mean()*100), 1),
           "auc_xgb": round(float(auc), 3), "auc_logit": round(float(auc_log), 3),
           "horizon": "breakup by 2022 wave (~5 yrs after 2017 baseline)"}

expl = shap.TreeExplainer(model)
sv = expl.shap_values(X)
mean_abs = np.abs(sv).mean(axis=0)
order = np.argsort(mean_abs)[::-1]
F["shap_top"] = [{"feature": XCOLS[i], "mean_abs_shap": round(float(mean_abs[i]), 4)}
                 for i in order[:12]]
chan_shap = {c: round(float(mean_abs[XCOLS.index(f"ch_{c}")]), 4)
             for c in CHAN_ORDER if f"ch_{c}" in XCOLS}
F["shap_channel"] = chan_shap

fig, ax = plt.subplots(figsize=(8.5, 5))
top = order[:12][::-1]
ax.barh([XCOLS[i] for i in top], mean_abs[top], color="#1d7874")
ax.set_xlabel("Mean |SHAP| (impact on predicted breakup risk)")
ax.set_title("What predicts a breakup by 2022? (XGBoost + SHAP)")
fig.savefig(CH / "shap_bar.png"); plt.close(fig)
shap.summary_plot(sv, X, show=False, max_display=14)
plt.savefig(CH / "shap_beeswarm.png", dpi=200, bbox_inches="tight")
plt.close("all")

# channel premium: g-computation over the fitted model + bootstrap CI
def premium(data, mdl):
    base = data[XCOLS].copy()
    outp = {}
    for c in CHAN_ORDER:
        d = base.copy()
        for cc in CHAN_ORDER:
            if f"ch_{cc}" in d: d[f"ch_{cc}"] = 1.0 if cc == c else 0.0
        d["met_online"] = 1.0 if c == "online" else d["met_online"]
        if c != "online": d["met_via_app"] = 0.0
        d["met_thru_friends"] = 1.0 if c == "friends" else (
            0.0 if c == "online" else d["met_thru_friends"])
        outp[c] = float(mdl.predict_proba(d[XCOLS])[:, 1].mean())
    return outp

prem = premium(ml, model)
boots = {c: [] for c in CHAN_ORDER}
for b in range(60):
    idx = rng.integers(0, len(ml), len(ml))
    mb = ml.iloc[idx]
    m2 = xgb.XGBClassifier(n_estimators=250, max_depth=3, learning_rate=.06,
                           subsample=.85, colsample_bytree=.85,
                           eval_metric="logloss", random_state=b)
    m2.fit(mb[XCOLS].astype(float), mb["y"].values)
    pb = premium(ml, m2)
    for c in CHAN_ORDER: boots[c].append(pb[c])
F["channel_premium_breakup_pct"] = {
    c: {"adj_pct": round(prem[c] * 100, 1),
        "ci95": [round(float(np.percentile(boots[c], 2.5)) * 100, 1),
                 round(float(np.percentile(boots[c], 97.5)) * 100, 1)]}
    for c in CHAN_ORDER if c != "other"}
raw_rate = {c: round(float(ml[ml.channel == c]["y"].mean() * 100), 1)
            for c in CHAN_ORDER if c != "other"}
F["channel_raw_breakup_pct_w1_to_2022"] = raw_rate

fig, ax = plt.subplots(figsize=(9, 4.8))
cs = [c for c in CHAN_ORDER if c in F["channel_premium_breakup_pct"]]
adj = [prem[c] * 100 for c in cs]
lo = [adj[i] - F["channel_premium_breakup_pct"][c]["ci95"][0] for i, c in enumerate(cs)]
hi = [F["channel_premium_breakup_pct"][c]["ci95"][1] - adj[i] for i, c in enumerate(cs)]
x_ = np.arange(len(cs))
ax.bar(x_ - .2, [raw_rate[c] for c in cs], .4, label="Raw breakup rate",
       color="#9aa0a6")
ax.bar(x_ + .2, adj, .4, label="Adjusted (channel premium)",
       color="#d1495b")
ax.errorbar(x_ + .2, adj, yerr=[lo, hi], fmt="none", color="k", capsize=3, lw=1)
ax.set_xticks(x_); ax.set_xticklabels([CHAN_LABEL[c] for c in cs], rotation=25, ha="right")
ax.set_ylabel("Broke up by 2022 (%)")
ax.set_title("Breakup risk by channel: raw vs. model-adjusted (same people, different door)")
ax.legend()
fig.savefig(CH / "channel_premium.png"); plt.close(fig)

# ============================================================ 5. site data grid
grid = {}
for c in CHAN_ORDER:
    for d0 in (1980, 1990, 2000, 2010):
        for age in (22, 30, 40, 52):
            row = {f: float(X[f].mean()) for f in XCOLS}
            row["age_at_start"], row["start_year"] = age, d0 + 5
            for cc in CHAN_ORDER:
                if f"ch_{cc}" in row: row[f"ch_{cc}"] = 1.0 if cc == c else 0.0
            row["met_online"] = 1.0 if c == "online" else 0.0
            row["met_via_app"] = 1.0 if c == "online" else 0.0
            row["met_thru_friends"] = 1.0 if c == "friends" else 0.0
            p = float(model.predict_proba(pd.DataFrame([row])[XCOLS])[:, 1][0])
            grid[f"{c}|{d0}|{age}"] = round((1 - p) * 100, 1)
site_data = {"grid": grid, "channels": CHAN_LABEL,
             "premium": F["channel_premium_breakup_pct"],
             "raw": raw_rate, "km": F["survival_by_channel"]}
(HERE / "site" / "data.js").write_text(
    "const SITE_DATA = " + json.dumps(site_data, indent=1) + ";\n")
F["site_grid_cells"] = len(grid)

(HERE / "data" / "findings.json").write_text(json.dumps(F, indent=1))
tab.round(2).to_csv(HERE / "data" / "channel_share_by_decade.csv")
print(json.dumps({k: F[k] for k in ["n_couples", "online_passes_friends_year",
      "online_passes_family_year", "logrank_online_vs_friends", "ml"]}, indent=1))
print("premium:", F["channel_premium_breakup_pct"])
print("DONE")
