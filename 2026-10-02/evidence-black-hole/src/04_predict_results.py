"""
Part 2 — can we predict which finished trials will ever report results?

Cohort: trials that started <= 2020 and reached a finished status
(COMPLETED/TERMINATED/WITHDRAWN/SUSPENDED) — old enough that 'no results
yet' really means 'no results'. Target: has_results on ClinicalTrials.gov.

Features are all knowable at registration time (sponsor class, phase,
enrollment, randomization/masking, sites, countries, FDA-regulated flag,
DMC, start year, intervention). XGBoost + SHAP, logistic-regression
baseline, stratified 80/20 split.

Outputs: output/model_results.json, output/shap_importance.csv,
         charts/shap_importance.png, charts/model_by_cohort.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
OUT, CH = ROOT / "output", ROOT / "charts"
FINISHED = ["COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"]


def build_features(df):
    d = df.copy()
    d["start_year"] = pd.to_datetime(d["start_date"], errors="coerce", format="mixed").dt.year
    d["log_enrollment"] = np.log1p(d["enrollment_count"].fillna(d["enrollment_count"].median()))
    d["log_sites"] = np.log1p(d["n_locations"].fillna(0))
    d["is_industry"] = (d["lead_sponsor_class"] == "INDUSTRY").astype(int)
    d["is_federal"] = (d["lead_sponsor_class"] == "FED").astype(int)
    d["is_randomized"] = (d["allocation"] == "RANDOMIZED").astype(int)
    d["is_masked"] = (~d["masking"].isin(["NONE", np.nan])).astype(int)
    d["is_fda_drug"] = (d["is_fda_regulated_drug"] == True).astype(int)  # noqa: E712
    d["has_dmc"] = (d["has_dmc"] == True).astype(int)  # noqa: E712
    d["phase_early"] = d["phases"].fillna("").str.contains("PHASE1|EARLY_PHASE1").astype(int)
    d["phase_late"] = d["phases"].fillna("").str.contains("PHASE3|PHASE4").astype(int)
    d["was_terminated"] = d["overall_status"].isin(["TERMINATED", "WITHDRAWN", "SUSPENDED"]).astype(int)
    feats = ["start_year", "log_enrollment", "log_sites", "n_countries", "is_industry",
             "is_federal", "is_randomized", "is_masked", "is_fda_drug", "has_dmc",
             "phase_early", "phase_late", "was_terminated", "n_primary_outcomes"]
    return d, feats


def main():
    OUT.mkdir(exist_ok=True)
    CH.mkdir(exist_ok=True)
    df = pd.read_csv(ROOT / "data" / "trials.csv")
    d, feats = build_features(df)
    cohort = d[(d["start_year"] <= 2020) & (d["overall_status"].isin(FINISHED))].dropna(subset=["start_year"])
    X, y = cohort[feats].fillna(0), cohort["has_results"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    lr.fit(Xtr, ytr)
    lr_pred = lr.predict_proba(Xte)[:, 1]

    xgb = XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.06,
                        subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
                        random_state=42)
    xgb.fit(Xtr, ytr)
    xgb_pred = xgb.predict_proba(Xte)[:, 1]

    results = {
        "cohort_n": int(len(cohort)),
        "base_rate_has_results": round(float(y.mean()), 4),
        "logreg_auc": round(float(roc_auc_score(yte, lr_pred)), 4),
        "logreg_acc": round(float(accuracy_score(yte, lr_pred > 0.5)), 4),
        "xgb_auc": round(float(roc_auc_score(yte, xgb_pred)), 4),
        "xgb_acc": round(float(accuracy_score(yte, xgb_pred > 0.5)), 4),
        "note": "Cohort: started <=2020, finished status. Target: results posted on registry.",
    }
    # Supplement-only refit: benchmarks dominate the pooled cohort, so check
    # the signal survives inside the supplement universe alone.
    BENCH = {"Metformin (benchmark)", "Sirolimus/rapamycin (benchmark)"}
    supp = cohort[~cohort["intervention"].isin(BENCH)]
    Xs, ys = supp[feats].fillna(0), supp["has_results"].astype(int)
    Xtr_s, Xte_s, ytr_s, yte_s = train_test_split(Xs, ys, test_size=0.2, random_state=42, stratify=ys)
    xgb_s = XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.06,
                          subsample=0.9, colsample_bytree=0.9, eval_metric="logloss", random_state=42)
    xgb_s.fit(Xtr_s, ytr_s)
    pred_s = xgb_s.predict_proba(Xte_s)[:, 1]
    results["supplement_only"] = {
        "cohort_n": int(len(supp)),
        "base_rate_has_results": round(float(ys.mean()), 4),
        "xgb_auc": round(float(roc_auc_score(yte_s, pred_s)), 4),
        "xgb_acc": round(float(accuracy_score(yte_s, pred_s > 0.5)), 4),
    }
    (OUT / "model_results.json").write_text(json.dumps(results, indent=2))
    print(results)

    explainer = shap.TreeExplainer(xgb)
    sv = explainer.shap_values(Xte)
    imp = pd.DataFrame({"feature": feats, "mean_abs_shap": np.abs(sv).mean(axis=0)}).sort_values("mean_abs_shap", ascending=True)
    imp.to_csv(OUT / "shap_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(imp["feature"], imp["mean_abs_shap"], color="#2b6cb0")
    ax.set_xlabel("mean |SHAP|")
    ax.set_title("What predicts a finished trial actually reporting results?")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CH / "shap_importance.png", dpi=160)
    plt.close(fig)

    # reporting rate by sponsor class & by cohort year (descriptive, full cohort)
    cohort2 = cohort.copy()
    cohort2["pred"] = xgb.predict_proba(X)[:, 1]
    by_year = cohort2.groupby("start_year")["has_results"].agg(["mean", "count"])
    by_year.to_csv(OUT / "results_rate_by_year.csv")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(by_year.index, by_year["mean"] * 100, marker="o", color="#2b6cb0")
    ax.set_ylabel("% finished trials posting results")
    ax.set_xlabel("Trial start year")
    ax.set_title("Results-posting by start cohort (trials started ≤2020, finished)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(CH / "model_by_cohort.png", dpi=160)
    plt.close(fig)

    # sponsor-class table for the README
    tab = cohort.groupby("lead_sponsor_class")["has_results"].agg(["mean", "count"]).sort_values("count", ascending=False)
    tab.to_csv(OUT / "results_by_sponsor.csv")
    print(tab)


if __name__ == "__main__":
    main()
