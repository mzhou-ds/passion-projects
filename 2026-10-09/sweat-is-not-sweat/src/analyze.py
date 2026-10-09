"""
Sweat Is Not Sweat — the physical-activity paradox in NHANES 2015-2018.

Question: does exercise count the same when it's your job vs. your choice?
Data: NHANES 2015-16 (cycle I) + 2017-18 (cycle J), public CDC downloads.
Activity from the GPAQ-style PAQ module; MET-min/week: vigorous=8, moderate=4.
Outcomes: diabetes / dysglycemia (HbA1c + questionnaire), obesity (measured BMI),
self-rated fair/poor health.

Run:  python src/analyze.py
Outputs: charts/*.png, output/results.json, output/explorer_model.json,
         data/nhanes_pooled.csv
"""
import json
import os
import urllib.request

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{yr}/DataFiles/{name}_{sfx}.xpt"
CYCLES = [(2015, "I", 2015), (2017, "J", 2017)]  # (first year, suffix, url year)
FILES = ["DEMO", "PAQ", "BMX", "HSQ", "DIQ", "GHB", "HDL"]

RNG = np.random.default_rng(20261009)

# ---------------------------------------------------------------- downloads
def download_all():
    for yr, sfx, _ in CYCLES:
        for name in FILES:
            path = os.path.join(RAW, f"{name}_{sfx}.xpt")
            if os.path.exists(path) and os.path.getsize(path) > 10_000:
                continue
            url = BASE.format(yr=yr, name=name, sfx=sfx)
            print(f"  downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())

def read_xpt(name, sfx):
    path = os.path.join(RAW, f"{name}_{sfx}.xpt")
    df = pd.read_sas(path, format="xport")
    df.columns = [c.upper() for c in df.columns]
    return df.set_index("SEQN")

# ---------------------------------------------------------------- cleaning
BAD = {7, 9, 77, 99, 777, 999, 7777, 9999, 77777, 99999}

def clean_special(s):
    return s.where(~s.isin(BAD), np.nan)

def domain_met(df, screen, days, mins, met):
    """MET-min/week for one GPAQ domain. screen==2 (No) -> 0; missing pieces -> NaN."""
    out = pd.Series(np.nan, index=df.index, dtype=float)
    no = df[screen] == 2
    out[no] = 0.0
    yes = df[screen] == 1
    d = clean_special(df[days]); m = clean_special(df[mins])
    ok = yes & d.between(1, 7) & m.between(1, 960)
    out[ok] = d[ok] * m[ok] * met
    return out

def domain_min(df, screen, days, mins):
    out = pd.Series(np.nan, index=df.index, dtype=float)
    out[df[screen] == 2] = 0.0
    d = clean_special(df[days]); m = clean_special(df[mins])
    ok = (df[screen] == 1) & d.between(1, 7) & m.between(1, 960)
    out[ok] = d[ok] * m[ok]
    return out

def load_cycle(sfx, cycle_label):
    demo = read_xpt("DEMO", sfx)
    paq = read_xpt("PAQ", sfx)
    bmx = read_xpt("BMX", sfx)
    hsq = read_xpt("HSQ", sfx)
    diq = read_xpt("DIQ", sfx)
    ghb = read_xpt("GHB", sfx)
    try:
        hdl = read_xpt("HDL", sfx)
        hdl_col = hdl["LBDHDD"] if "LBDHDD" in hdl else hdl.iloc[:, 0]
    except Exception:
        hdl_col = pd.Series(dtype=float)

    df = demo.join(paq, rsuffix="_paq").join(bmx, rsuffix="_bmx") \
             .join(hsq, rsuffix="_hsq").join(diq, rsuffix="_diq") \
             .join(ghb, rsuffix="_ghb")
    df["HDL"] = hdl_col
    df["cycle"] = cycle_label

    # --- activity domains (MET-min/week; vigorous 8 METs, moderate 4 METs)
    df["work_vig_met"]  = domain_met(df, "PAQ605", "PAQ610", "PAD615", 8)
    df["work_mod_met"]  = domain_met(df, "PAQ620", "PAQ625", "PAD630", 4)
    df["trans_met"]     = domain_met(df, "PAQ635", "PAQ640", "PAD645", 4)
    df["leis_vig_met"]  = domain_met(df, "PAQ650", "PAQ655", "PAD660", 8)
    df["leis_mod_met"]  = domain_met(df, "PAQ665", "PAQ670", "PAD675", 4)
    df["work_met"]  = df["work_vig_met"] + df["work_mod_met"]
    df["leisure_met"] = df["leis_vig_met"] + df["leis_mod_met"]
    df["work_min"]  = domain_min(df, "PAQ605", "PAQ610", "PAD615") + \
                      domain_min(df, "PAQ620", "PAQ625", "PAD630")
    df["leisure_min"] = domain_min(df, "PAQ650", "PAQ655", "PAD660") + \
                        domain_min(df, "PAQ665", "PAQ670", "PAD675")

    # recreational days/week (proxy: sum of vigorous + moderate days, capped 7)
    vd = clean_special(df["PAQ655"]).where(df["PAQ650"] == 1, 0)
    md = clean_special(df["PAQ670"]).where(df["PAQ665"] == 1, 0)
    df["rec_days"] = (vd.fillna(0) + md.fillna(0)).clip(upper=7)
    df.loc[vd.isna() & md.isna(), "rec_days"] = np.nan

    # sitting
    df["sitting_hrs"] = clean_special(df["PAD680"]) / 60.0
    df.loc[df["sitting_hrs"] > 20, "sitting_hrs"] = np.nan

    # GPAQ plausibility screen: >16h/day of reported activity is not credible
    daily_min = (df["work_min"].fillna(0) + df["leisure_min"].fillna(0)) / 7.0
    df["implausible"] = daily_min > 960

    # --- outcomes
    df["hba1c"] = df["LBXGH"]
    df["diabetes"] = ((df["DIQ010"] == 1) | (df["hba1c"] >= 6.5)).astype(float)
    df.loc[df["DIQ010"].isna() & df["hba1c"].isna(), "diabetes"] = np.nan
    df["dysglycemia"] = ((df["hba1c"] >= 5.7) | (df["DIQ010"] == 1)).astype(float)
    df.loc[df["hba1c"].isna() & df["DIQ010"].isna(), "dysglycemia"] = np.nan
    df["bmi"] = df["BMXBMI"]
    df["obesity"] = (df["bmi"] >= 30).astype(float)
    df.loc[df["bmi"].isna(), "obesity"] = np.nan
    df["poor_health"] = clean_special(df["HSD010"]).isin([4, 5]).astype(float)
    df.loc[clean_special(df["HSD010"]).isna(), "poor_health"] = np.nan

    # --- covariates
    df["age"] = df["RIDAGEYR"]
    df["female"] = (df["RIAGENDR"] == 2).astype(float)
    df["fmpir"] = df["INDFMPIR"].where(df["INDFMPIR"] <= 5)
    educ_map = {1: "hs_or_less", 2: "hs_or_less", 3: "hs_or_less",
                4: "some_college", 5: "college_plus"}
    df["educ3"] = df["DMDEDUC2"].map(educ_map)
    race_map = {1: "Mexican American", 2: "Other Hispanic", 3: "NH White",
                4: "NH Black", 6: "NH Asian", 7: "Other/Multi"}
    df["race"] = df["RIDRETH3"].map(race_map)
    df["wt"] = df["WTMEC2YR"] / 2.0  # pooled 2-cycle MEC weight

    def inc_group(x):
        if pd.isna(x): return np.nan
        if x < 1.3: return "low (<1.3x poverty)"
        if x <= 3.5: return "middle (1.3-3.5x)"
        return "high (>3.5x)"
    df["income_group"] = df["fmpir"].map(inc_group)
    return df

# ---------------------------------------------------------------- helpers
def wmean(x, w):
    m = x.notna() & w.notna()
    return np.average(x[m], weights=w[m])

def wquantile(x, w, q):
    m = x.notna() & w.notna()
    x, w = np.asarray(x[m]), np.asarray(w[m])
    i = np.argsort(x)
    x, w = x[i], w[i]
    cw = np.cumsum(w) - 0.5 * w
    return np.interp(q * w.sum(), cw, x)

def wprev(df, outcome, mask=None):
    d = df if mask is None else df[mask]
    m = d[outcome].notna() & d["wt"].notna()
    p = np.average(d.loc[m, outcome], weights=d.loc[m, "wt"])
    neff = (d.loc[m, "wt"].sum() ** 2) / (d.loc[m, "wt"] ** 2).sum()
    se = np.sqrt(p * (1 - p) / max(neff, 1))
    return p, p - 1.96 * se, p + 1.96 * se, int(m.sum())

# ---------------------------------------------------------------- main
def main():
    print("downloading NHANES files ...")
    download_all()
    frames, flow = [], {}
    for _, sfx, yr in CYCLES:
        d = load_cycle(sfx, yr)
        flow[f"cycle_{yr}_total"] = int(len(d))
        d = d[(d["age"] >= 20) & (d["age"] <= 65)]
        flow[f"cycle_{yr}_age20_65"] = int(len(d))
        frames.append(d)
    df = pd.concat(frames)
    flow["pooled_age20_65"] = int(len(df))

    need = ["leisure_met", "work_met", "trans_met", "sitting_hrs", "bmi", "hba1c"]
    df = df.dropna(subset=need)
    df = df[~df["implausible"]]
    df = df[df["diabetes"].notna() & df["poor_health"].notna()]
    df = df[df["educ3"].notna() & df["race"].notna() & df["fmpir"].notna()]
    flow["analytic_sample"] = int(len(df))
    flow["asian_n"] = int((df["race"] == "NH Asian").sum())
    print("flow:", flow)

    df["leisure600"] = df["leisure_met"] / 600.0
    df["work600"] = df["work_met"] / 600.0
    df["trans600"] = df["trans_met"] / 600.0
    df["sitting2"] = df["sitting_hrs"] / 2.0
    df["meets"] = (df["leisure_met"] >= 600).astype(int)
    df["any_work_pa"] = (df["work_met"] > 0).astype(int)

    out_cols = ["cycle", "age", "female", "race", "educ3", "income_group", "fmpir",
                "leisure_met", "work_met", "trans_met", "leisure_min", "work_min",
                "rec_days", "sitting_hrs", "bmi", "hba1c", "HDL", "diabetes",
                "dysglycemia", "obesity", "poor_health", "meets", "wt"]
    df[out_cols].to_csv(os.path.join(ROOT, "data", "nhanes_pooled.csv"), index=False)

    results = {"flow": flow, "sample": {}, "paradox": {}, "inequality": {},
               "dose_response": {}, "xgb": {}, "weekend_warrior": {},
               "counterfactual": {}, "asian": {}}
    results["sample"] = {
        "n": int(len(df)),
        "pct_female": float(df["female"].mean()),
        "mean_age": float(df["age"].mean()),
        "pct_meets_guidelines_leisure": float(wmean(df["meets"], df["wt"])),
        "pct_any_work_activity": float(wmean(df["any_work_pa"], df["wt"])),
        "median_leisure_met": float(wquantile(df["leisure_met"], df["wt"], 0.5)),
        "median_work_met": float(wquantile(df["work_met"], df["wt"], 0.5)),
        "prev_diabetes": float(wmean(df["diabetes"], df["wt"])),
        "prev_dysglycemia": float(wmean(df["dysglycemia"], df["wt"])),
        "prev_obesity": float(wmean(df["obesity"], df["wt"])),
        "prev_poor_health": float(wmean(df["poor_health"], df["wt"])),
    }

    # ------------------------------------------------ A. the paradox (logits)
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    outcomes = ["dysglycemia", "diabetes", "obesity", "poor_health"]
    f_terms = ("leisure600 + work600 + trans600 + sitting2 + age + female + "
               "C(race) + C(educ3) + fmpir + C(cycle)")
    fig_rows = []
    for oc in outcomes:
        m = smf.glm(f"{oc} ~ {f_terms}", data=df,
                    family=sm.families.Binomial()).fit(cov_type="HC1")
        row = {"outcome": oc, "n": int(m.nobs)}
        for v in ["leisure600", "work600", "trans600", "sitting2"]:
            lo, hi = np.exp(m.conf_int().loc[v].values)
            row[v] = {"or": float(np.exp(m.params[v])), "lo": float(lo),
                      "hi": float(hi), "p": float(m.pvalues[v])}
        results["paradox"][oc] = row
        fig_rows.append(row)
        print(oc, {k: round(v["or"], 3) for k, v in row.items()
                   if isinstance(v, dict)})

    # weighted sensitivity for the headline outcome
    d2 = df.copy(); d2["wt_n"] = d2["wt"] / d2["wt"].mean()
    mw = smf.glm(f"dysglycemia ~ {f_terms}", data=d2,
                 family=sm.families.Binomial(),
                 freq_weights=d2["wt_n"]).fit(cov_type="HC1")
    results["paradox"]["dysglycemia_weighted"] = {
        v: {"or": float(np.exp(mw.params[v])),
            "p": float(mw.pvalues[v])} for v in ["leisure600", "work600"]}

    # ------------------------------------------------ B. inequality
    inc_order = ["low (<1.3x poverty)", "middle (1.3-3.5x)", "high (>3.5x)"]
    ineq = {}
    for g in inc_order:
        d = df[df["income_group"] == g]
        ineq[g] = {
            "n": int(len(d)),
            "pct_meets": float(wmean(d["meets"], d["wt"])),
            "median_leisure_met": float(wquantile(d["leisure_met"], d["wt"], .5)),
            "median_work_met": float(wquantile(d["work_met"], d["wt"], .5)),
            "p75_leisure_met": float(wquantile(d["leisure_met"], d["wt"], .75)),
            "mean_sitting_hrs": float(wmean(d["sitting_hrs"], d["wt"])),
        }
    results["inequality"]["by_income"] = ineq
    by_race = {}
    for g, d in df.groupby("race"):
        by_race[g] = {"n": int(len(d)),
                      "pct_meets": float(wmean(d["meets"], d["wt"])),
                      "median_leisure_met": float(wquantile(d["leisure_met"], d["wt"], .5)),
                      "median_work_met": float(wquantile(d["work_met"], d["wt"], .5)),
                      "prev_poor_health": float(wmean(d["poor_health"], d["wt"]))}
    results["inequality"]["by_race"] = by_race
    by_educ = {}
    for g, d in df.groupby("educ3"):
        by_educ[g] = {"n": int(len(d)),
                      "pct_meets": float(wmean(d["meets"], d["wt"]))}
    results["inequality"]["by_education"] = by_educ

    asian = df[df["race"] == "NH Asian"]
    results["asian"] = {
        "n": int(len(asian)),
        "pct_meets": float(wmean(asian["meets"], asian["wt"])),
        "median_leisure_met": float(wquantile(asian["leisure_met"], asian["wt"], .5)),
        "median_work_met": float(wquantile(asian["work_met"], asian["wt"], .5)),
        "pct_meets_low_income": float(wmean(
            asian.loc[asian["income_group"] == inc_order[0], "meets"],
            asian.loc[asian["income_group"] == inc_order[0], "wt"])),
        "pct_meets_high_income": float(wmean(
            asian.loc[asian["income_group"] == inc_order[2], "meets"],
            asian.loc[asian["income_group"] == inc_order[2], "wt"])),
    }

    # ------------------------------------------------ C. dose-response
    bins = [(-1, "0"), (0, "1-299"), (300, "300-599"), (600, "600-1199"),
            (1200, "1200-2399"), (2400, "2400+")]
    def dose(var):
        cats = pd.cut(df[var], bins=[b[0] for b in bins] + [np.inf],
                      labels=[b[1] for b in bins])
        rows = []
        for lab in [b[1] for b in bins]:
            p, lo, hi, n = wprev(df, "dysglycemia", cats == lab)
            p2, lo2, hi2, _ = wprev(df, "poor_health", cats == lab)
            rows.append({"bin": lab, "n": n, "dysglycemia": p, "lo": lo,
                         "hi": hi, "poor_health": p2, "lo2": lo2, "hi2": hi2})
        return rows
    results["dose_response"]["leisure"] = dose("leisure_met")
    results["dose_response"]["work"] = dose("work_met")

    # ------------------------------------------------ D. XGBoost + SHAP
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score
    from xgboost import XGBClassifier
    import shap
    X = pd.get_dummies(df[["age", "female", "fmpir", "bmi", "leisure_met",
                           "work_met", "trans_met", "sitting_hrs", "race",
                           "educ3"]], columns=["race", "educ3"], drop_first=True)
    X = X.astype(float)
    y = df["poor_health"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=7, stratify=y)
    model = XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                          subsample=0.9, colsample_bytree=0.9,
                          eval_metric="logloss", random_state=7)
    model.fit(Xtr, ytr)
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
    explainer = shap.TreeExplainer(model)
    sv = explainer(Xte)
    mean_abs = np.abs(sv.values).mean(axis=0)
    imp = sorted(zip(X.columns, mean_abs), key=lambda t: -t[1])
    results["xgb"] = {"auc_poor_health": float(auc),
                      "shap_ranking": [(k, float(v)) for k, v in imp]}
    # SHAP direction: mean SHAP among zero vs 1200+ leisure / work
    def shap_by_level(feat, levels):
        vals = Xte[feat].values; svals = sv.values[:, list(X.columns).index(feat)]
        out = {}
        for name, cond in levels.items():
            out[name] = float(svals[cond(vals)].mean()) if cond(vals).any() else None
        return out
    results["xgb"]["shap_leisure_levels"] = shap_by_level(
        "leisure_met", {"0": lambda v: v == 0, "600-1199": lambda v: (v >= 600) & (v < 1200),
                        "2400+": lambda v: v >= 2400})
    results["xgb"]["shap_work_levels"] = shap_by_level(
        "work_met", {"0": lambda v: v == 0, "600-1199": lambda v: (v >= 600) & (v < 1200),
                     "2400+": lambda v: v >= 2400})
    print("XGB AUC:", round(auc, 3), "| top SHAP:", imp[:5])

    # ------------------------------------------------ E. weekend warrior
    meeters = df[df["meets"] == 1].copy()
    meeters["warrior"] = (meeters["rec_days"] <= 2).astype(float)
    meeters.loc[meeters["rec_days"].isna(), "warrior"] = np.nan
    ww = {"n_meeters": int(len(meeters)),
          "pct_warrior": float(meeters["warrior"].mean())}
    for oc in ["dysglycemia", "obesity", "poor_health"]:
        d = meeters.dropna(subset=["warrior"])
        m = smf.glm(f"{oc} ~ warrior + age + female + C(race) + C(educ3) + fmpir + "
                    f"C(cycle)", data=d, family=sm.families.Binomial()).fit(cov_type="HC1")
        lo, hi = np.exp(m.conf_int().loc["warrior"].values)
        ww[oc] = {"or_warrior_vs_spread": float(np.exp(m.params["warrior"])),
                  "lo": float(lo), "hi": float(hi), "p": float(m.pvalues["warrior"])}
    results["weekend_warrior"] = ww
    print("weekend warrior:", ww)

    # ------------------------------------------------ F. counterfactual
    m = smf.glm(f"diabetes ~ {f_terms}", data=df,
                family=sm.families.Binomial()).fit()
    low = df[df["income_group"] == inc_order[0]].copy()
    high = df[df["income_group"] == inc_order[2]]
    base_pred = float(m.predict(low).mean())
    draws = []
    low_idx = low.copy()
    for s in range(20):
        cf = low.copy()
        # quantile-map leisure within sex x age-band strata from the high group
        for (sex, band), idx in cf.groupby(["female", pd.cut(cf["age"], [19, 34, 49, 65])]).groups.items():
            pool = high[(high["female"] == sex) &
                        (pd.cut(high["age"], [19, 34, 49, 65]) == band)]["leisure_met"]
            if len(pool) > 20:
                cf.loc[idx, "leisure_met"] = RNG.choice(pool.values, size=len(idx))
        cf["leisure600"] = cf["leisure_met"] / 600.0
        draws.append(float(m.predict(cf).mean()))
    results["counterfactual"] = {
        "group": "low-income adults (FMPIR<1.3)",
        "n": int(len(low)),
        "pred_diabetes_at_own_leisure": base_pred,
        "pred_diabetes_at_high_income_leisure": float(np.mean(draws)),
        "draw_sd": float(np.std(draws)),
        "relative_change": float(np.mean(draws) / base_pred - 1),
    }
    print("counterfactual:", results["counterfactual"])

    # ------------------------------------------------ explorer model
    em = smf.glm("poor_health ~ age + female + fmpir + leisure600 + work600 + sitting2",
                 data=df, family=sm.families.Binomial()).fit()
    grid_min = [0, 30, 60, 90, 120, 150, 180, 240, 300, 420, 600]
    cdf = {}
    for g in inc_order:
        d = df[df["income_group"] == g]
        cdf[g] = [float(wmean((d["leisure_min"] <= gm).astype(float), d["wt"]))
                  for gm in grid_min]
    explorer = {"coef": {k: float(v) for k, v in em.params.items()},
                "features": ["Intercept", "age", "female", "fmpir",
                             "leisure600", "work600", "sitting2"],
                "income_midpoints": {inc_order[0]: 0.9, inc_order[1]: 2.2,
                                     inc_order[2]: 4.2},
                "grid_min": grid_min, "leisure_cdf_by_income": cdf,
                "outcome": "probability of fair/poor self-rated health",
                "note": "Logistic fit on NHANES 2015-2018 adults 20-65; association, not destiny."}
    with open(os.path.join(ROOT, "output", "explorer_model.json"), "w") as f:
        json.dump(explorer, f, indent=1)

    with open(os.path.join(ROOT, "output", "results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("results written")

    # ------------------------------------------------ charts
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150})
    C_LEIS, C_WORK, C_SIT = "#1b7f5a", "#c1502e", "#5b6abf"

    # 01 paradox forest
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), sharex=False)
    labels = {"dysglycemia": "Dysglycemia\n(HbA1c>=5.7)", "diabetes": "Diabetes",
              "obesity": "Obesity", "poor_health": "Fair/poor\nhealth"}
    for ax, oc in zip(axes, outcomes):
        r = results["paradox"][oc]
        for j, (v, c, lab) in enumerate([("leisure600", C_LEIS, "leisure"),
                                         ("work600", C_WORK, "work"),
                                         ("sitting2", C_SIT, "sitting/2h")]):
            d = r[v]; y = 2 - j
            ax.errorbar(d["or"], y, xerr=[[d["or"] - d["lo"]], [d["hi"] - d["or"]]],
                        fmt="o", color=c, capsize=3, ms=5)
            ax.text(d["hi"] * 1.04, y, f'{d["or"]:.2f}', va="center", fontsize=8, color=c)
        ax.axvline(1, color="#999", lw=0.8, ls="--")
        ax.set_yticks([2, 1, 0]); ax.set_yticklabels(["leisure", "work", "sitting"])
        ax.set_title(labels[oc], fontsize=10); ax.set_xlim(0.55, 1.75)
        ax.set_xlabel("OR per 600 MET-min (sitting: per 2h)")
    fig.suptitle("Same sweat, different receipt: leisure protects, work doesn't",
                 fontsize=12, y=1.04)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "01_paradox_forest.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 02 inequality
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    xs = np.arange(3)
    a1.bar(xs - 0.2, [ineq[g]["pct_meets"] * 100 for g in inc_order], 0.4,
           color=C_LEIS, label="% meeting guidelines (leisure)")
    a1.bar(xs + 0.2, [wmean(df.loc[df["income_group"] == g, "any_work_pa"],
                            df.loc[df["income_group"] == g, "wt"]) * 100
                       for g in inc_order], 0.4, color=C_WORK,
           label="% with any occupational activity")
    a1.set_xticks(xs); a1.set_xticklabels(["Low\n<1.3x poverty", "Middle", "High\n>3.5x"])
    a1.set_ylabel("% of adults"); a1.legend(fontsize=8)
    a1.set_title("Who gets to exercise on purpose?")
    a2.bar(xs - 0.2, [ineq[g]["median_leisure_met"] for g in inc_order], 0.4,
           color=C_LEIS, label="median leisure MET-min/wk")
    a2.bar(xs + 0.2, [ineq[g]["median_work_met"] for g in inc_order], 0.4,
           color=C_WORK, label="median work MET-min/wk")
    a2.set_xticks(xs); a2.set_xticklabels(["Low", "Middle", "High"])
    a2.set_ylabel("MET-min/week"); a2.legend(fontsize=8)
    a2.set_title("The sweat swap by income")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "02_inequality.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 03 dose-response
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, key, c, title in [(a1, "leisure", C_LEIS, "Leisure MET-min/week"),
                              (a2, "work", C_WORK, "Work MET-min/week")]:
        rows = results["dose_response"][key]
        x = np.arange(len(rows))
        ax.errorbar(x, [r["dysglycemia"] * 100 for r in rows],
                    yerr=[[ (r["dysglycemia"] - r["lo"]) * 100 for r in rows],
                          [ (r["hi"] - r["dysglycemia"]) * 100 for r in rows]],
                    fmt="o-", color=c, capsize=3, label="dysglycemia")
        ax.errorbar(x, [r["poor_health"] * 100 for r in rows],
                    yerr=[[ (r["poor_health"] - r["lo2"]) * 100 for r in rows],
                          [ (r["hi2"] - r["poor_health"]) * 100 for r in rows]],
                    fmt="s--", color="#444", capsize=3, label="fair/poor health")
        ax.set_xticks(x); ax.set_xticklabels([r["bin"] for r in rows], fontsize=8)
        ax.set_title(title); ax.set_xlabel("MET-min/week bin")
        ax.legend(fontsize=8)
    a1.set_ylabel("weighted prevalence (%)")
    fig.suptitle("Dose-response: one curve falls, the other doesn't", y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "03_dose_response.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 04 SHAP
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8),
                                 gridspec_kw={"width_ratios": [1.2, 1]})
    top = imp[:9][::-1]
    nice = {"leisure_met": "leisure exercise", "work_met": "work activity",
            "trans_met": "transport activity", "sitting_hrs": "sitting hrs",
            "fmpir": "income (FMPIR)", "bmi": "BMI", "age": "age",
            "female": "female"}
    a1.barh([nice.get(k.split("_")[0] + "_" + k.split("_")[1], k) if False else
             nice.get(k, k.replace("race_", "race: ").replace("educ3_", "educ: "))
             for k, _ in top], [v for _, v in top], color="#33608c")
    a1.set_xlabel("mean |SHAP| (fair/poor health model)")
    a1.set_title(f"What the model listens to (AUC {auc:.2f})")
    bin_edges = np.array([0, 1, 300, 600, 1200, 2400, 4001, np.inf])
    bin_centers = np.array([0, 150, 450, 900, 1800, 3200, 5000])
    for feat, c, lab in [("leisure_met", C_LEIS, "leisure"), ("work_met", C_WORK, "work")]:
        j = list(X.columns).index(feat)
        xv, yv = Xte[feat].values, sv.values[:, j]
        keep = RNG.choice(len(xv), size=min(1500, len(xv)), replace=False)
        a2.scatter(np.clip(xv[keep], 0, 4000), yv[keep], s=4, alpha=0.18, color=c)
        binned = pd.cut(xv, bins=bin_edges, labels=False)
        means = [yv[binned == b].mean() if (binned == b).any() else np.nan
                 for b in range(len(bin_centers))]
        a2.plot(np.clip(bin_centers, 0, 4000), means, "o-", color=c, lw=2,
                ms=5, label=f"{lab} (binned mean)")
    a2.axhline(0, color="#999", lw=0.8)
    a2.set_xlabel("MET-min/week (clipped 4000)"); a2.set_ylabel("SHAP value")
    a2.set_title("SHAP: leisure bends down, work sits flat"); a2.legend()
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "04_shap.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 05 weekend warrior
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ocs = ["dysglycemia", "obesity", "poor_health"]
    labs = ["Dysglycemia", "Obesity", "Fair/poor health"]
    for j, oc in enumerate(ocs):
        d = ww[oc]
        ax.errorbar(d["or_warrior_vs_spread"], j,
                    xerr=[[d["or_warrior_vs_spread"] - d["lo"]],
                          [d["hi"] - d["or_warrior_vs_spread"]]],
                    fmt="o", capsize=3, color="#33608c")
        ax.text(d["hi"] * 1.03, j, f'{d["or_warrior_vs_spread"]:.2f}', va="center", fontsize=9)
    ax.axvline(1, color="#999", ls="--", lw=0.8)
    ax.set_yticks(range(3)); ax.set_yticklabels(labs)
    ax.set_xlabel("OR: weekend warrior (<=2 days) vs spread (>=3 days), among guideline-meeters")
    ax.set_title("Compressed exercise isn't penalized")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "05_weekend_warrior.png"),
                                    bbox_inches="tight"); plt.close(fig)
    print("charts done")

if __name__ == "__main__":
    main()
