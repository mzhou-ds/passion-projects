"""
03_gss.py - what the microdata says, and what predicts having no kids.

A. Sibship by birth cohort (GSS `sibs`, top-coded at 6): mean siblings,
   only-child share, share with 4+ siblings. NOTE the textbook trap:
   respondent-reported sibship is CHILD-weighted - a mother of six
   contributes six potential respondents, a mother of one contributes
   one - so mean sibs overstates the average mother's family size.
   Levels carry that bias; cohort *contrasts* and the only-child share
   (a share of people, which is the quantity this build cares about)
   are the defensible reads.
B. Completed fertility by cohort (respondents aged 45+): mean children
   (`childs`) and the childless share, by birth cohort and sex.
C. Who ends up childless? XGBoost classifier on respondents aged 45-70
   (fertility effectively complete, recall still anchored in adult
   life): cohort, sex, race, education, degree, marital history,
   religious attendance, region, work status. AUC on a held-out split
   plus SHAP importances. The point is not prediction - it is showing
   that childlessness, the zero that deletes a whole branch of the
   next generation's kin tree, is sorted by life-course variables far
   more than by birth cohort alone.

Outputs: data/gss_cohorts.csv, data/childless_model.json,
         data/shap_importance.csv, data/findings.json (merged)
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
rng = np.random.default_rng(23)


def wshare(mask, w):
    m = mask.notna() & w.notna()
    return float(np.average(mask[m].astype(float), weights=w[m]))


def wmean(x, w):
    m = x.notna() & w.notna()
    return float(np.average(x[m], weights=w[m]))


def main():
    g = pd.read_csv(os.path.join(DATA, "gss_extract.csv"))
    findings = {}

    # ---- A. sibship by cohort decade
    rows = []
    gg = g[(g.cohort >= 1925) & (g.cohort <= 1999)].copy()
    gg["decade"] = (gg.cohort // 10 * 10).astype(int)
    for dec, sub in gg.groupby("decade"):
        rows.append({
            "decade": int(dec), "n": int(sub.sibs.notna().sum()),
            "mean_sibs": round(wmean(sub.sibs, sub.wtssall), 2),
            "only_child_pct": round(100 * wshare(sub.sibs == 0, sub.wtssall), 1),
            "four_plus_sibs_pct": round(100 * wshare(sub.sibs >= 4, sub.wtssall), 1),
        })
    sib = pd.DataFrame(rows)
    findings["sibs_by_decade"] = sib.to_dict("records")

    # ---- B. completed fertility, age 45+
    rows = []
    a = g[(g.age >= 45) & (g.cohort >= 1925) & (g.cohort <= 1974)].copy()
    a["decade"] = (a.cohort // 10 * 10).astype(int)
    for dec, sub in a.groupby("decade"):
        if len(sub) < 300:
            continue
        row = {"decade": int(dec), "n": int(sub.childs.notna().sum()),
               "mean_childs": round(wmean(sub.childs, sub.wtssall), 2),
               "childless_pct": round(100 * wshare(sub.childs == 0, sub.wtssall), 1)}
        for sex, lab in [(1, "men"), (2, "women")]:
            s2 = sub[sub.sex == sex]
            row[f"childless_{lab}_pct"] = round(100 * wshare(s2.childs == 0, s2.wtssall), 1)
        rows.append(row)
    fert = pd.DataFrame(rows)
    findings["completed_fertility_by_decade"] = fert.to_dict("records")

    cohorts = pd.concat([
        sib.assign(table="sibship"),
        fert.assign(table="completed_fertility"),
    ], ignore_index=True)
    cohorts.to_csv(os.path.join(DATA, "gss_cohorts.csv"), index=False)
    print(sib.to_string(index=False))
    print(fert.to_string(index=False))

    # ---- C. childlessness model
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split
    from xgboost import XGBClassifier
    import shap

    m = g[(g.age >= 45) & (g.age <= 70) & (g.cohort >= 1935)].copy()
    m["childless"] = (m.childs == 0).astype(float)
    m["ever_married"] = ((m.marital != 5) | (m.divorce == 1)).astype(float)
    m["female"] = (m.sex == 2).astype(float)
    feats = ["cohort", "female", "race", "educ", "degree", "ever_married",
             "attend", "relig", "region", "wrkstat"]
    m = m.dropna(subset=feats + ["childless"])
    X, y = m[feats], m.childless
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=23, stratify=y)
    clf = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05,
                        subsample=0.9, colsample_bytree=0.9,
                        eval_metric="logloss", random_state=23)
    clf.fit(X_tr, y_tr)
    auc = float(roc_auc_score(y_te, clf.predict_proba(X_te)[:, 1]))
    expl = shap.TreeExplainer(clf)
    sv = expl.shap_values(X_te)
    imp = pd.DataFrame({"feature": feats,
                        "mean_abs_shap": np.abs(sv).mean(axis=0).round(4),
                        "corr": [np.corrcoef(sv[:, i], X_te.iloc[:, i])[0, 1].round(3)
                                 for i in range(len(feats))]}).sort_values(
        "mean_abs_shap", ascending=False)
    imp.to_csv(os.path.join(DATA, "shap_importance.csv"), index=False)
    model_info = {"n": int(len(m)), "base_childless_pct": round(100 * float(y.mean()), 1),
                  "test_auc": round(auc, 3),
                  "top_features": imp.head(5).feature.tolist()}
    with open(os.path.join(DATA, "childless_model.json"), "w") as fh:
        json.dump(model_info, fh, indent=2)
    findings["childless_model"] = model_info
    print(model_info)
    print(imp.to_string(index=False))

    with open(os.path.join(DATA, "findings.json"), "w") as fh:
        json.dump(findings, fh, indent=2)


if __name__ == "__main__":
    main()
