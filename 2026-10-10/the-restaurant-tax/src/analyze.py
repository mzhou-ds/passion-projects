"""
The Restaurant Tax — you don't pay for the food, you pay in sodium.

Question: in NHANES 2015-2018, where do America's calories actually come from
(grocery store vs fast food vs full-service restaurant vs everything else),
and what does each source charge you nutritionally per calorie — sodium,
sugar, fiber, saturated fat per 1,000 kcal?

Data: NHANES 2015-16 (cycle I) + 2017-18 (cycle J), public CDC XPT files:
DEMO, DR1TOT (Day-1 total nutrients), DR1IFF (Day-1 individual foods with
food-source codes), BMX (measured BMI), GHB (HbA1c), DIQ (diabetes history).
Adults 20-65 with a reliable Day-1 recall (DR1DRSTZ == 1).

Population shares use pooled Day-1 dietary weights (WTDRD1 / 2). Person-level
models (GLM, XGBoost, clustering) are unweighted with HC1 robust SEs where
applicable; that choice is stated in the README, not hidden.

Run:  python src/analyze.py
Outputs: charts/*.png, output/results.json, output/explorer_model.json,
         data/nhanes_nutrition_pooled.csv, explorer.html
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
os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "charts"), exist_ok=True)

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{yr}/DataFiles/{name}_{sfx}.xpt"
CYCLES = [(2015, "I"), (2017, "J")]
FILES = ["DEMO", "DR1TOT", "DR1IFF", "BMX", "GHB", "DIQ"]
RNG = np.random.default_rng(20261010)

# NHANES DR1FS food-source codes -> analysis groups (CDC codebook for
# DR1TOT_I.htm, verified 2026-10-10): 1 = store grocery/supermarket,
# 27 = store convenience type, 28 = store with no additional information;
# 2 = restaurant with waiter/waitress (full-service); 3 = restaurant fast
# food/pizza. Codes 5 (restaurant, no additional information), 4 (bar),
# 6-26 (cafeterias, care centers, soup kitchens, vending, gifts, community
# programs, grown/caught, street vendors, fundraisers) and 91 (other) are
# grouped as "other" -- code 5 is left there deliberately because it cannot
# be split between fast food and full-service.
SOURCE_GROUPS = {1: "store", 27: "store", 28: "store",
                 2: "full_service", 3: "fast_food"}
SOURCE_LABEL = {"store": "Grocery store", "fast_food": "Fast food",
                "full_service": "Full-service restaurant", "other": "Other sources"}
SOURCE_ORDER = ["store", "fast_food", "full_service", "other"]

# DR1_030Z eating-occasion codes (CDC codebook), harmonized WWEIA-style:
# Spanish-language occasion names fold into their English equivalents, and
# snack + drink + extended consumption group together, as USDA's What We
# Eat in America tables do.
OCCASIONS = {1: "Breakfast", 10: "Breakfast", 11: "Breakfast",
             2: "Lunch", 5: "Lunch", 12: "Lunch",
             3: "Dinner/supper", 4: "Dinner/supper", 14: "Dinner/supper",
             6: "Snack", 7: "Snack", 9: "Snack", 13: "Snack", 15: "Snack",
             16: "Snack", 17: "Snack", 18: "Snack", 19: "Snack",
             8: "Other", 91: "Other"}

# FNDDS/WWEIA food codes: first digit is the top-level food group. These are
# the standard FNDDS major groups used across NHANES dietary files.
FNDDS_GROUPS = {"1": "Milk & milk products", "2": "Meat, poultry, fish & mixtures",
                "3": "Eggs", "4": "Legumes, nuts & seeds", "5": "Grain products",
                "6": "Fruits", "7": "Vegetables",
                "8": "Fats, oils & salad dressings",
                "9": "Sugars, sweets & beverages"}

NUTRIENTS = ["sodium_mg", "sugar_g", "fiber_g", "satfat_g"]
NUTRIENT_LABEL = {"sodium_mg": "Sodium (mg)", "sugar_g": "Total sugar (g)",
                  "fiber_g": "Fiber (g)", "satfat_g": "Saturated fat (g)"}

# ---------------------------------------------------------------- downloads
def download_all():
    for yr, sfx in CYCLES:
        for name in FILES:
            path = os.path.join(RAW, f"{name}_{sfx}.xpt")
            if os.path.exists(path) and os.path.getsize(path) > 10_000:
                continue
            url = BASE.format(yr=yr, name=name, sfx=sfx)
            print(f"  downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
                f.write(r.read())

def read_xpt(name, sfx):
    path = os.path.join(RAW, f"{name}_{sfx}.xpt")
    df = pd.read_sas(path, format="xport")
    df.columns = [str(c).upper() for c in df.columns]
    return df

def pick(df, *candidates, required=True):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"none of {candidates} in columns {list(df.columns)[:40]}")
    return None

# ---------------------------------------------------------------- loading
def load_people(sfx, cycle_label):
    demo = read_xpt("DEMO", sfx).set_index("SEQN")
    tot = read_xpt("DR1TOT", sfx).set_index("SEQN")
    bmx = read_xpt("BMX", sfx).set_index("SEQN")
    ghb = read_xpt("GHB", sfx).set_index("SEQN")
    diq = read_xpt("DIQ", sfx).set_index("SEQN")

    df = demo.join(tot, rsuffix="_tot").join(bmx, rsuffix="_bmx") \
             .join(ghb, rsuffix="_ghb").join(diq, rsuffix="_diq")
    df["cycle"] = cycle_label

    kcal_c = pick(df, "DR1TKCAL")
    sod_c = pick(df, "DR1TSODI")
    sug_c = pick(df, "DR1TSUGR")
    fib_c = pick(df, "DR1TFIBE")
    sat_c = pick(df, "DR1TSFAT")
    adds_c = pick(df, "DR1TADDS", "DR1T_ADD_SUG", required=False)
    df["kcal"] = df[kcal_c]
    df["sodium_mg"] = df[sod_c]
    df["sugar_g"] = df[sug_c]
    df["fiber_g"] = df[fib_c]
    df["satfat_g"] = df[sat_c]
    df["added_sugar_g"] = df[adds_c] if adds_c else np.nan
    df["recall_reliable"] = (df[pick(df, "DR1DRSTZ")] == 1)
    w_c = pick(df, "WTDRD1")
    df["wt"] = df[w_c] / 2.0  # pooled two-cycle Day-1 dietary weight

    df["hba1c"] = df["LBXGH"]
    df["diabetes"] = ((df["DIQ010"] == 1) | (df["hba1c"] >= 6.5)).astype(float)
    df.loc[df["DIQ010"].isna() & df["hba1c"].isna(), "diabetes"] = np.nan
    df["dysglycemia"] = ((df["hba1c"] >= 5.7) | (df["DIQ010"] == 1)).astype(float)
    df.loc[df["hba1c"].isna() & df["DIQ010"].isna(), "dysglycemia"] = np.nan
    df["bmi"] = df["BMXBMI"]
    df["obesity"] = (df["bmi"] >= 30).astype(float)
    df.loc[df["bmi"].isna(), "obesity"] = np.nan

    df["age"] = df["RIDAGEYR"]
    df["female"] = (df["RIAGENDR"] == 2).astype(float)
    df["fmpir"] = df["INDFMPIR"].where(df["INDFMPIR"] <= 5)
    educ_map = {1: "hs_or_less", 2: "hs_or_less", 3: "hs_or_less",
                4: "some_college", 5: "college_plus"}
    df["educ3"] = df["DMDEDUC2"].map(educ_map)
    race_map = {1: "Mexican American", 2: "Other Hispanic", 3: "NH White",
                4: "NH Black", 6: "NH Asian", 7: "Other/Multi"}
    df["race"] = df["RIDRETH3"].map(race_map)
    keep = ["cycle", "age", "female", "race", "educ3", "fmpir", "wt",
            "recall_reliable", "kcal", "sodium_mg", "sugar_g", "fiber_g",
            "satfat_g", "added_sugar_g", "bmi", "obesity", "hba1c",
            "diabetes", "dysglycemia"]
    return df[keep]

def load_foods(sfx):
    f = read_xpt("DR1IFF", sfx)
    src_c = pick(f, "DR1FS")
    occ_c = pick(f, "DR1_030Z", required=False)
    code_c = pick(f, "DR1IFDCD")
    kcal_c = pick(f, "DR1IKCAL")
    sod_c = pick(f, "DR1ISODI")
    sug_c = pick(f, "DR1ISUGR")
    fib_c = pick(f, "DR1IFIBE")
    sat_c = pick(f, "DR1ISFAT")
    out = pd.DataFrame({
        "SEQN": f["SEQN"],
        "source_code": pd.to_numeric(f[src_c], errors="coerce"),
        "occasion": (pd.to_numeric(f[occ_c], errors="coerce")
                     if occ_c else np.nan),
        "food_code": pd.to_numeric(f[code_c], errors="coerce"),
        "kcal": pd.to_numeric(f[kcal_c], errors="coerce"),
        "sodium_mg": pd.to_numeric(f[sod_c], errors="coerce"),
        "sugar_g": pd.to_numeric(f[sug_c], errors="coerce"),
        "fiber_g": pd.to_numeric(f[fib_c], errors="coerce"),
        "satfat_g": pd.to_numeric(f[sat_c], errors="coerce"),
    })
    out["source"] = out["source_code"].map(SOURCE_GROUPS).fillna("other")
    out["occasion_label"] = out["occasion"].map(OCCASIONS).fillna("Other")
    out["fndds_group"] = out["food_code"].apply(
        lambda c: FNDDS_GROUPS.get(str(int(c))[0], "Other")
        if pd.notna(c) and c >= 1000000 else "Other")
    return out

# ---------------------------------------------------------------- helpers
def wmean(x, w):
    m = pd.notna(x) & pd.notna(w)
    return float(np.average(np.asarray(x)[m], weights=np.asarray(w)[m]))

def wpct(num_w, den_w):
    return float(num_w / den_w) if den_w else float("nan")

# ---------------------------------------------------------------- main
def main():
    print("downloading NHANES files ...")
    download_all()
    people_frames, food_frames, flow = [], [], {}
    for yr, sfx in CYCLES:
        p = load_people(sfx, yr)
        flow[f"cycle_{yr}_total"] = int(len(p))
        p = p[(p["age"] >= 20) & (p["age"] <= 65)]
        flow[f"cycle_{yr}_age20_65"] = int(len(p))
        people_frames.append(p)
        f = load_foods(sfx)
        f = f[f["SEQN"].isin(p.index)]
        food_frames.append(f)
        print(f"cycle {yr}: people {len(p)}, food rows {len(f)}")
    people = pd.concat(people_frames)
    foods = pd.concat(food_frames)
    flow["pooled_age20_65"] = int(len(people))

    df = people[people["recall_reliable"]].copy()
    flow["reliable_recall"] = int(len(df))
    # implausible one-day energy: flag, don't silently keep
    flow["kcal_lt500_or_gt8000"] = int(((df["kcal"] < 500) | (df["kcal"] > 8000)).sum())
    df = df[(df["kcal"] >= 500) & (df["kcal"] <= 8000)]
    foods = foods[foods["SEQN"].isin(df.index)]
    flow["analytic_sample"] = int(len(df))
    print("flow:", flow)

    # ---- per-person x source aggregates (the spine of everything below)
    piv = foods.groupby(["SEQN", "source"])["kcal"].sum().unstack(fill_value=0.0)
    for g in SOURCE_ORDER:
        if g not in piv.columns:
            piv[g] = 0.0
    piv.columns = [f"kcal_{g}" for g in piv.columns]
    df = df.join(piv, how="left").fillna({c: 0.0 for c in piv.columns})
    tot_iff = foods.groupby("SEQN")["kcal"].sum().rename("kcal_iff")
    df = df.join(tot_iff)
    for g in SOURCE_ORDER:
        df[f"share_{g}"] = df[f"kcal_{g}"] / df["kcal_iff"]
    df["share_restaurant"] = df["share_fast_food"] + df["share_full_service"]
    for n in NUTRIENTS + ["added_sugar_g"]:
        df[f"{n}_per1000"] = df[n] / df["kcal"] * 1000.0

    out_cols = ["cycle", "age", "female", "race", "educ3", "fmpir", "wt",
                "kcal", "sodium_mg", "sugar_g", "fiber_g", "satfat_g",
                "added_sugar_g", "bmi", "obesity", "hba1c", "diabetes",
                "dysglycemia"] + [f"share_{g}" for g in SOURCE_ORDER] + \
               ["share_restaurant"] + [f"{n}_per1000" for n in NUTRIENTS]
    df[out_cols].to_csv(os.path.join(ROOT, "data", "nhanes_nutrition_pooled.csv"))

    results = {"flow": flow, "sample": {}, "concentration": {},
               "nutrient_pricing": {}, "models": {}, "xgb": {},
               "archetypes": {}, "counterfactual": {}}

    # ------------------------------------------------ sample description
    W = df["wt"].values
    results["sample"] = {
        "n": int(len(df)),
        "food_rows": int(len(foods)),
        "mean_age": float(df["age"].mean()),
        "pct_female": float(df["female"].mean()),
        "weighted_mean_kcal": wmean(df["kcal"], df["wt"]),
        "weighted_mean_sodium_mg": wmean(df["sodium_mg"], df["wt"]),
        "weighted_pct_obesity": wmean(df["obesity"], df["wt"]),
        "weighted_pct_dysglycemia": wmean(df["dysglycemia"], df["wt"]),
        "added_sugar_available": bool(df["added_sugar_g"].notna().any()),
        "note": ("Population shares weighted (WTDRD1/2). Person-level models "
                 "unweighted, HC1 SEs. One reliable Day-1 recall per person."),
    }

    # ------------------------------------------------ 1. concentration
    fw = foods.merge(df[["wt"]], left_on="SEQN", right_index=True, how="left")
    fw["wkcal"] = fw["kcal"] * fw["wt"]
    total_wkcal = fw["wkcal"].sum()
    by_source = {}
    for g in SOURCE_ORDER:
        s = fw.loc[fw["source"] == g, "wkcal"].sum()
        by_source[g] = {"label": SOURCE_LABEL[g],
                        "calorie_share": wpct(s, total_wkcal)}
    results["concentration"]["calorie_share_by_source"] = by_source

    by_occ = (fw.groupby("occasion_label")["wkcal"].sum() / total_wkcal)
    results["concentration"]["calorie_share_by_occasion"] = {
        k: float(v) for k, v in by_occ.sort_values(ascending=False).items()}

    by_src_occ = {}
    for g in SOURCE_ORDER:
        sub = fw[fw["source"] == g]
        den = sub["wkcal"].sum()
        by_src_occ[g] = {k: float(v) for k, v in
                         (sub.groupby("occasion_label")["wkcal"].sum() / den)
                         .sort_values(ascending=False).items()} if den else {}
    results["concentration"]["occasion_within_source"] = by_src_occ

    by_fndds = (fw.groupby("fndds_group")["wkcal"].sum() / total_wkcal)
    results["concentration"]["calorie_share_by_fndds_group"] = {
        k: float(v) for k, v in by_fndds.sort_values(ascending=False).items()}
    rest = fw[fw["source"].isin(["fast_food", "full_service"])]
    by_fndds_rest = (rest.groupby("fndds_group")["wkcal"].sum()
                     / rest["wkcal"].sum())
    results["concentration"]["fndds_group_within_restaurant"] = {
        k: float(v) for k, v in
        by_fndds_rest.sort_values(ascending=False).items()}
    # person-level prevalence: any restaurant calories at all?
    results["concentration"]["pct_any_restaurant_calories"] = wmean(
        (df["share_restaurant"] > 0).astype(float), df["wt"])
    results["concentration"]["mean_restaurant_share_among_consumers"] = wmean(
        df.loc[df["share_restaurant"] > 0, "share_restaurant"],
        df.loc[df["share_restaurant"] > 0, "wt"])
    print("calorie shares:", {k: round(v["calorie_share"], 3)
                              for k, v in by_source.items()})

    # ------------------------------------------------ 2. nutrient pricing
    persons = df.index.values
    pidx = {s: i for i, s in enumerate(persons)}
    ps = foods.groupby(["SEQN", "source"])[["kcal"] + NUTRIENTS].sum()
    M = {}  # group -> (n_persons x values) arrays aligned to df
    for g in SOURCE_ORDER:
        sub = ps.xs(g, level="source") if g in ps.index.get_level_values("source") else None
        arr = np.zeros((len(df), 1 + len(NUTRIENTS)))
        if sub is not None:
            rows = [pidx[s] for s in sub.index]
            arr[rows] = sub[["kcal"] + NUTRIENTS].values
        M[g] = arr
    wv = df["wt"].values

    def densities(idxs):
        out = {}
        for g in SOURCE_ORDER:
            a = M[g][idxs]
            wst = wv[idxs]
            kcal = float((a[:, 0] * wst).sum())
            row = {"kcal_weighted_sum": kcal}
            for j, n in enumerate(NUTRIENTS):
                row[n] = float((a[:, j + 1] * wst).sum() / kcal * 1000.0) if kcal else np.nan
            out[g] = row
        return out

    point = densities(np.arange(len(df)))
    boot = {g: {n: [] for n in NUTRIENTS} for g in SOURCE_ORDER}
    for b in range(200):
        idx = RNG.integers(0, len(df), len(df))
        d = densities(idx)
        for g in SOURCE_ORDER:
            for n in NUTRIENTS:
                boot[g][n].append(d[g][n])
    pricing = {}
    for g in SOURCE_ORDER:
        row = {}
        for n in NUTRIENTS:
            lo, hi = np.percentile(boot[g][n], [2.5, 97.5])
            row[n] = {"per1000kcal": point[g][n], "lo": float(lo), "hi": float(hi)}
        pricing[g] = row
    results["nutrient_pricing"]["by_source"] = pricing
    tax = {}
    for g in ["fast_food", "full_service"]:
        tax[g] = {n: float((pricing[g][n]["per1000kcal"]
                             / pricing["store"][n]["per1000kcal"] - 1) * 100)
                  for n in NUTRIENTS}
    results["nutrient_pricing"]["restaurant_tax_pct_vs_store"] = tax
    print("restaurant tax:", {g: {n: round(v, 1) for n, v in d.items()}
                              for g, d in tax.items()})

    # ------------------------------------------------ 3. adjusted models
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    md = df.dropna(subset=["bmi", "obesity", "hba1c", "dysglycemia",
                           "educ3", "race", "fmpir"]).copy()
    md["rest10"] = md["share_restaurant"] * 10.0
    md["fast10"] = md["share_fast_food"] * 10.0
    md["kcal1000"] = md["kcal"] / 1000.0
    md["rest_group"] = pd.cut(md["share_restaurant"],
                              bins=[-0.001, 0.0001, 0.15, 0.30, 1.0],
                              labels=["none", "1-15%", "15-30%", "30%+"])
    ctrl = "age + female + C(race) + C(educ3) + fmpir + C(cycle) + kcal1000"
    models = {"n": int(len(md))}
    for outcome, fam, label in [("bmi", None, "BMI (linear, HC1)"),
                                ("hba1c", None, "HbA1c (linear, HC1)"),
                                ("obesity", "binom", "Obesity (logit, HC1)"),
                                ("dysglycemia", "binom", "Dysglycemia (logit, HC1)")]:
        if fam is None:
            m = smf.ols(f"{outcome} ~ rest10 + {ctrl}", data=md).fit(cov_type="HC1")
            e = {"coef_per10pp": float(m.params["rest10"]),
                 "lo": float(m.conf_int().loc["rest10", 0]),
                 "hi": float(m.conf_int().loc["rest10", 1]),
                 "p": float(m.pvalues["rest10"])}
        else:
            m = smf.glm(f"{outcome} ~ rest10 + {ctrl}", data=md,
                        family=sm.families.Binomial()).fit(cov_type="HC1")
            lo, hi = np.exp(m.conf_int().loc["rest10"].values)
            e = {"or_per10pp": float(np.exp(m.params["rest10"])),
                 "lo": float(lo), "hi": float(hi),
                 "p": float(m.pvalues["rest10"])}
        models[outcome] = {"model": label, **e}
        print(outcome, e)
    mg = smf.glm(f"obesity ~ C(rest_group, Treatment(reference='none')) + {ctrl}",
                 data=md, family=sm.families.Binomial()).fit(cov_type="HC1")
    grp = {}
    for term in mg.params.index:
        if "rest_group" in term:
            lo, hi = np.exp(mg.conf_int().loc[term].values)
            grp[term.split("]")[-1].strip("T.[]") or term] = {
                "or": float(np.exp(mg.params[term])), "lo": float(lo),
                "hi": float(hi), "p": float(mg.pvalues[term])}
    models["obesity_by_restaurant_share_group"] = grp
    results["models"] = models

    # ------------------------------------------------ 4. XGBoost + SHAP
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from xgboost import XGBClassifier
    import shap

    xd = md.copy()
    feats = ["age", "female", "fmpir", "kcal1000"] + \
            [f"{n}_per1000" for n in NUTRIENTS] + \
            [f"share_{g}" for g in SOURCE_ORDER]
    X = pd.get_dummies(xd[feats + ["race", "educ3"]],
                       columns=["race", "educ3"], drop_first=True).astype(float)
    y = xd["obesity"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=7, stratify=y)
    lr = make_pipeline(StandardScaler(),
                       LogisticRegression(max_iter=1000, C=1.0))
    lr.fit(Xtr, ytr)
    auc_lr = roc_auc_score(yte, lr.predict_proba(Xte)[:, 1])
    xgb = XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                        subsample=0.9, colsample_bytree=0.9,
                        eval_metric="logloss", random_state=7)
    xgb.fit(Xtr, ytr)
    auc_xgb = roc_auc_score(yte, xgb.predict_proba(Xte)[:, 1])
    explainer = shap.TreeExplainer(xgb)
    sv = explainer(Xte)
    mean_abs = np.abs(sv.values).mean(axis=0)
    imp = sorted(zip(X.columns, mean_abs), key=lambda t: -t[1])
    results["xgb"] = {"outcome": "obesity", "auc_xgboost": float(auc_xgb),
                      "auc_logistic": float(auc_lr),
                      "shap_ranking": [(k, float(v)) for k, v in imp]}
    print(f"XGB AUC {auc_xgb:.3f} vs logistic {auc_lr:.3f}; top SHAP: {imp[:5]}")

    # ------------------------------------------------ 5. dietary archetypes
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    cd = md.copy()
    cfeats = [f"{n}_per1000" for n in NUTRIENTS] + \
             ["share_store", "share_fast_food", "share_full_service"]
    Z = StandardScaler().fit_transform(cd[cfeats].values)
    sil = {}
    sample_i = RNG.choice(len(Z), size=min(2500, len(Z)), replace=False)
    for k in range(2, 8):
        lab = KMeans(n_clusters=k, n_init=10, random_state=7).fit_predict(Z)
        sil[k] = float(silhouette_score(Z[sample_i], lab[sample_i]))
    k_best = int(max([k for k in sil if 4 <= k <= 6], key=lambda k: sil[k]))
    km = KMeans(n_clusters=k_best, n_init=25, random_state=7).fit(Z)
    cd["cluster"] = km.labels_
    print("silhouette:", sil, "| chosen k =", k_best)

    prof_raw = []
    for c in range(k_best):
        d = cd[cd["cluster"] == c]
        prof_raw.append({
            "cluster": int(c), "n": int(len(d)),
            "pct_of_sample": float(len(d) / len(cd)),
            "mean_age": float(d["age"].mean()),
            "mean_fmpir": float(d["fmpir"].mean()),
            "mean_bmi": float(d["bmi"].mean()),
            "pct_obesity": float(d["obesity"].mean()),
            "mean_hba1c": float(d["hba1c"].mean()),
            "share_store": float(d["share_store"].mean()),
            "share_fast_food": float(d["share_fast_food"].mean()),
            "share_full_service": float(d["share_full_service"].mean()),
            "share_restaurant": float(d["share_restaurant"].mean()),
            **{n: float(d[n].mean()) for n in
               [f"{x}_per1000" for x in NUTRIENTS]},
        })
    # Name the segments the way a market researcher would: sharpest trait
    # first, every label used once, assigned in a fixed priority order.
    named = {}
    def claim(rank_key, label, exclude=()):
        cand = [r for r in prof_raw if r["cluster"] not in named
                and r["cluster"] not in exclude]
        best = max(cand, key=rank_key)
        named[best["cluster"]] = label
    claim(lambda r: r["share_fast_food"], "Drive-Thru Regulars")
    claim(lambda r: r["share_full_service"], "Sit-Down Splurgers")
    claim(lambda r: r["fiber_g_per1000"], "Home-Base Cooks")
    claim(lambda r: r["sugar_g_per1000"], "Grocery Sweet Tooths")
    leftover = [r for r in prof_raw if r["cluster"] not in named]
    if leftover:
        r = leftover[0]
        r["name_fallback"] = True
        named[r["cluster"]] = ("Pantry Salt Loaders"
                               if r["sodium_mg_per1000"] > 1650
                               else "Mixed-Basket Moderates")
    for r in prof_raw:
        r["name"] = named.get(r["cluster"], "Mixed-Basket Moderates")
    results["archetypes"] = {"k_chosen": k_best, "silhouette_by_k": sil,
                             "features": cfeats, "profiles": prof_raw}

    # ------------------------------------------------ 6. counterfactual
    dens = {g: {n: pricing[g][n]["per1000kcal"] for n in NUTRIENTS}
            for g in ["store", "fast_food"]}
    cf = {}
    for n in NUTRIENTS:
        delta_pp = (df["kcal_fast_food"] * (dens["store"][n] - dens["fast_food"][n])
                    / 1000.0)
        cf[n] = {
            "mean_change_per_person_day": float(np.average(delta_pp, weights=W)),
            "unit": "mg" if n == "sodium_mg" else "g",
            "note": ("Same calories, store-food nutrient density. Assumes the "
                     "swap is nutritionally complete and behavior does not "
                     "compensate; a pricing identity, not a causal forecast.")}
    base = {n: float(np.average(df[n], weights=W)) for n in NUTRIENTS}
    for n in NUTRIENTS:
        cf[n]["pct_of_mean_daily_intake"] = float(
            cf[n]["mean_change_per_person_day"] / base[n] * 100)
    results["counterfactual"] = {
        "intervention": "Move all fast-food calories to the store-food nutrient profile, calories held fixed.",
        "baseline_weighted_mean_intake": base, "deltas": cf}

    with open(os.path.join(ROOT, "output", "results.json"), "w") as fjson:
        json.dump(results, fjson, indent=1, default=str)
    print("results written")

    # ------------------------------------------------ explorer model
    em = smf.glm("obesity ~ age + female + fmpir + rest10 + kcal1000", data=md,
                 family=sm.families.Binomial()).fit()
    arch_js = [{"name": r["name"], "restaurant_share": r["share_restaurant"],
                "fast_share": r["share_fast_food"], "pct_obesity": r["pct_obesity"],
                "mean_bmi": r["mean_bmi"],
                "blurb": (f"{r['pct_of_sample']*100:.0f}% of adults · BMI "
                          f"{r['mean_bmi']:.1f} · {r['pct_obesity']*100:.0f}% obesity"
                          f" · {r['share_restaurant']*100:.0f}% restaurant calories")}
               for r in prof_raw]
    explorer = {
        "coef": {k: float(v) for k, v in em.params.items()},
        "features": ["Intercept", "age", "female", "fmpir", "rest10", "kcal1000"],
        "age_midpoints": {"20-34": 27, "35-49": 42, "50-65": 57},
        "income_midpoints": {"low": 0.9, "middle": 2.2, "high": 4.2},
        "archetypes": arch_js,
        "population_obesity": float(md["obesity"].mean()),
        "outcome": "predicted probability of obesity (BMI >= 30)",
        "note": ("Logistic fit on NHANES 2015-2018 adults 20-65 with reliable "
                 "Day-1 recall at 2,200 kcal. Cross-sectional association, "
                 "not a diagnosis and not destiny.")}
    with open(os.path.join(ROOT, "output", "explorer_model.json"), "w") as fjson:
        json.dump(explorer, fjson, indent=1)
    write_explorer(explorer)

    # ------------------------------------------------ charts
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150})
    C = {"store": "#1b7f5a", "fast_food": "#c1502e",
         "full_service": "#5b6abf", "other": "#9aa3ad"}

    # 01 concentration
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    gs = SOURCE_ORDER
    a1.bar([SOURCE_LABEL[g] for g in gs],
           [by_source[g]["calorie_share"] * 100 for g in gs],
           color=[C[g] for g in gs])
    a1.set_ylabel("% of national calories")
    a1.set_title("Where the calories come from")
    for i, g in enumerate(gs):
        a1.text(i, by_source[g]["calorie_share"] * 100 + 0.7,
                f'{by_source[g]["calorie_share"]*100:.1f}%', ha="center", fontsize=9)
    occ = results["concentration"]["calorie_share_by_occasion"]
    top_occ = list(occ.items())[:6]
    a2.barh([k for k, _ in top_occ][::-1], [v * 100 for _, v in top_occ][::-1],
            color="#33608c")
    a2.set_xlabel("% of national calories")
    a2.set_title("When they are eaten")
    fig.suptitle("America eats at home on paper; restaurants punch above their weight", y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "01_concentration.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 02 restaurant tax
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), sharey=False)
    for ax, n in zip(axes, NUTRIENTS):
        vals = [pricing[g][n]["per1000kcal"] for g in gs]
        errs = [[pricing[g][n]["per1000kcal"] - pricing[g][n]["lo"] for g in gs],
                [pricing[g][n]["hi"] - pricing[g][n]["per1000kcal"] for g in gs]]
        ax.bar([SOURCE_LABEL[g].replace(" restaurant", "").replace("Grocery ", "")
                for g in gs], vals, yerr=errs, capsize=3,
               color=[C[g] for g in gs])
        ax.set_title(NUTRIENT_LABEL[n] + " / 1,000 kcal", fontsize=10)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    fig.suptitle("The menu price is dollars. The real price is per-calorie.", y=1.04)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "02_restaurant_tax.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 03 model forest (obesity + dysglycemia per 10pp + share groups)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, oc, title in [(a1, "obesity", "Obesity"), (a2, "dysglycemia", "Dysglycemia")]:
        r = results["models"][oc]
        ax.errorbar(r["or_per10pp"], 0,
                    xerr=[[r["or_per10pp"] - r["lo"]], [r["hi"] - r["or_per10pp"]]],
                    fmt="o", color="#c1502e", capsize=4, ms=7)
        ax.axvline(1, color="#999", ls="--", lw=0.8)
        ax.set_yticks([])
        ax.set_xlabel("Adjusted OR per +10pp restaurant calorie share")
        ax.set_title(f"{title}: OR {r['or_per10pp']:.2f} (p={r['p']:.3f})")
    fig.suptitle("More restaurant share, worse receipts — after controls", y=1.03)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "03_model_forest.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 04 SHAP
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    top = imp[:10][::-1]
    nice = {"sodium_mg_per1000": "sodium density", "sugar_g_per1000": "sugar density",
            "fiber_g_per1000": "fiber density", "satfat_g_per1000": "sat-fat density",
            "share_store": "store share", "share_fast_food": "fast-food share",
            "share_full_service": "full-service share", "share_other": "other share",
            "fmpir": "income (FMPIR)", "kcal1000": "total kcal", "age": "age",
            "female": "female"}
    labels = [nice.get(k, k.replace("race_", "race: ").replace("educ3_", "educ: "))
              for k, _ in top]
    ax.barh(labels, [v for _, v in top], color="#33608c")
    ax.set_xlabel("mean |SHAP| (obesity model)")
    ax.set_title(f"What the model hears (XGBoost AUC {auc_xgb:.2f} vs logistic {auc_lr:.2f})")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "04_shap.png"),
                                    bbox_inches="tight"); plt.close(fig)
    # full SHAP summary (beeswarm) as supporting chart
    try:
        shap.summary_plot(sv, Xte, show=False, max_display=12)
        plt.tight_layout()
        plt.savefig(os.path.join(ROOT, "charts", "04b_shap_summary.png"),
                    bbox_inches="tight", dpi=150)
        plt.close("all")
    except Exception as e:
        print("shap summary skipped:", e)

    # 05 archetypes
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    names = [r["name"] for r in prof_raw]
    a1.barh(names, [r["share_restaurant"] * 100 for r in prof_raw], color="#c1502e")
    a1.set_xlabel("restaurant share of calories (%)")
    a1.set_title("Archetypes by restaurant exposure")
    a2.barh(names, [r["pct_obesity"] * 100 for r in prof_raw], color="#5b6abf")
    a2.set_xlabel("obesity prevalence (%)")
    a2.set_title("...and by who pays for it")
    fig.suptitle(f"America's eating archetypes (k={k_best}, picked by silhouette)", y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "05_archetypes.png"),
                                    bbox_inches="tight"); plt.close(fig)

    # 06 counterfactual
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    labs = ["Sodium (mg)", "Sugar (g)", "Fiber (g)", "Sat fat (g)"]
    vals = [cf[n]["mean_change_per_person_day"] for n in NUTRIENTS]
    cols = ["#c1502e" if v < 0 else "#1b7f5a" for v in vals]
    ax.bar(labs, vals, color=cols)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("change per person per day")
    ax.set_title("Same calories, store profile: the fast-food swap")
    for i, v in enumerate(vals):
        ax.text(i, v + (8 if v >= 0 else -8), f"{v:+.0f}" if abs(v) >= 10 else f"{v:+.1f}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "charts", "06_counterfactual.png"),
                                    bbox_inches="tight"); plt.close(fig)
    print("charts done")

# ---------------------------------------------------------------- explorer
def write_explorer(model):
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Restaurant Tax — what does eating out charge you?</title>
<style>
  :root { --ink:#1c2430; --mut:#5a6a7a; --store:#1b7f5a; --fast:#c1502e; --line:#d8dee5; }
  * { box-sizing: border-box; }
  body { font-family: Georgia, 'Times New Roman', serif; color: var(--ink); margin: 0; background:#faf8f4; }
  main { max-width: 720px; margin: 0 auto; padding: 32px 20px 64px; }
  h1 { font-size: 30px; line-height: 1.15; margin: 0 0 6px; }
  .sub { color: var(--mut); font-size: 16px; margin-bottom: 28px; }
  .card { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 20px 22px; margin-bottom: 18px; }
  label { display: block; font-size: 14px; color: var(--mut); margin: 14px 0 4px; }
  label b { color: var(--ink); float: right; font-variant-numeric: tabular-nums; }
  input[type=range] { width: 100%; accent-color: var(--fast); }
  select { font: inherit; font-size: 15px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; width: 100%; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .big { font-size: 42px; font-weight: bold; margin: 4px 0; }
  .verdict { font-size: 17px; line-height: 1.45; }
  .fine { font-size: 12.5px; color: var(--mut); line-height: 1.5; }
  .bar { height: 10px; background: #eee7db; border-radius: 5px; position: relative; margin: 10px 0 4px; }
  .bar > div { position: absolute; inset: 0 auto 0 0; background: var(--fast); border-radius: 5px; }
</style>
</head>
<body>
<main>
  <h1>You don't pay for the food. You pay in sodium.</h1>
  <p class="sub">NHANES 2015–2018, working-age adults, one measured day of eating. Tell this page how much of your plate comes from restaurants — it answers with the model-predicted probability of obesity and the eating archetype you most resemble.</p>

  <div class="card">
    <div class="row">
      <div><label>Age band</label><select id="age">
        <option value="20-34">20–34</option><option value="35-49" selected>35–49</option><option value="50-65">50–65</option></select></div>
      <div><label>Sex</label><select id="sex"><option value="0">Male</option><option value="1">Female</option></select></div>
    </div>
    <div><label>Household income</label><select id="income">
      <option value="low">Low (under 1.3× poverty line)</option>
      <option value="middle" selected>Middle (1.3–3.5×)</option>
      <option value="high">High (over 3.5×)</option></select></div>
    <label>Calories from fast food + restaurants <b><span id="restV">20</span>%</b></label>
    <input type="range" id="rest" min="0" max="60" step="1" value="20">
  </div>

  <div class="card">
    <div class="fine">Predicted probability of obesity (BMI ≥ 30), at a 2,200 kcal day:</div>
    <div class="big" id="prob">–</div>
    <div class="bar"><div id="probBar"></div></div>
    <p class="verdict" id="arch"></p>
    <p class="verdict" id="verdict"></p>
  </div>

  <p class="fine">The probability comes from a logistic model fitted on the NHANES sample (age, sex, income, total calories, restaurant calorie share). Cross-sectional associations in one measured day of eating — people carrying more weight may also eat out differently, and no slider untangles that. Full method, charts, and code: see the README in this directory. Data: CDC NHANES 2015–2016 and 2017–2018 public dietary files.</p>
</main>

<script>
const MODEL = __MODEL_JSON__;
const $ = id => document.getElementById(id);
function pct(x) { return Math.round(x * 100); }
function update() {
  const age = MODEL.age_midpoints[$('age').value], female = +$('sex').value;
  const fmpir = MODEL.income_midpoints[$('income').value];
  const restPct = +$('rest').value; $('restV').textContent = restPct;
  const rest10 = (restPct / 100) * 10;
  const c = MODEL.coef;
  const eta = c.Intercept + c.age * age + c.female * female + c.fmpir * fmpir
            + c.rest10 * rest10 + c.kcal1000 * 2.2;
  const p = 1 / (1 + Math.exp(-eta));
  $('prob').textContent = pct(p) + '%';
  $('probBar').style.width = pct(p) + '%';
  let best = null, bd = 1e9;
  for (const a of MODEL.archetypes) {
    const d = Math.abs(a.restaurant_share * 100 - restPct);
    if (d < bd) { bd = d; best = a; }
  }
  $('arch').textContent = "Closest archetype: " + best.name + " — " + best.blurb + ".";
  let v;
  if (restPct === 0) v = "Zero restaurant calories. In this data that is the grocery-store profile: the cheapest sodium, the most fiber per calorie.";
  else if (restPct < 15) v = "A light restaurant habit. The tax is real but small at this dose — the model moves on share, not on your last meal.";
  else if (restPct < 30) v = "A quarter of the plate, give or take. This is where the sodium bill stops being rounding error.";
  else v = "A third or more from restaurants. The per-calorie pricing — not the calorie count — is doing the damage in the model.";
  $('verdict').textContent = v;
}
['age','sex','income','rest'].forEach(id => $(id).addEventListener('input', update));
update();
</script>
</body>
</html>
"""
    html = html.replace("__MODEL_JSON__", json.dumps(model, indent=1))
    with open(os.path.join(ROOT, "explorer.html"), "w") as fh:
        fh.write(html)

if __name__ == "__main__":
    main()
