#!/usr/bin/env python3
"""03_xgb_shap.py — XGBoost on log(comp) + SHAP explanations.

Confirms the hedonic premiums with a nonlinear model, ranks feature
importance, and exports SHAP plots.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import xgboost as xgb
import shap

CATS = ["remote_simple", "ai_freq", "Ed_simple", "Country_top30", "Org_simple", "Age"]
REF = {"remote_simple": "In-person", "ai_freq": "no_never", "Ed_simple": "bachelors"}

def build_X(d):
    parts, names = {}, []
    for cat in CATS:
        for v in sorted(d[cat].dropna().unique()):
            parts[f"{cat}={v}"] = (d[cat] == v).astype(int)
    top_ind = d["Industry"].value_counts().head(10).index
    for ind in [i for i in top_ind if i != "Other:" and pd.notna(i)]:
        parts[f"ind_{str(ind)[:24]}"] = (d["Industry"] == ind).astype(int)
    for c in [c for c in d.columns if c.startswith(("role_", "lang_"))]:
        parts[c] = d[c].astype(int)
    parts["manager"] = d["manager"].astype(int)
    parts["exp"] = d["WorkExpY"].astype(float)
    return pd.DataFrame(parts).fillna(0)

def main():
    d = pd.read_csv("data/sample.csv")
    X = build_X(d)
    y = d["log_comp"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=7)

    m = xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.6, n_jobs=-1, random_state=7)
    m.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
    r2 = r2_score(yte, m.predict(Xte))
    print(f"XGBoost test R^2 = {r2:.3f}  (train n={len(Xtr)}, features={X.shape[1]})")

    # --- SHAP ---
    expl = shap.TreeExplainer(m)
    sample = Xte.sample(min(3000, len(Xte)), random_state=7)
    sv = expl.shap_values(sample)
    shap.summary_plot(sv, sample, max_display=25, show=False)
    plt.tight_layout(); plt.savefig("charts/shap_beeswarm.png", dpi=110); plt.close()

    imp = pd.Series(np.abs(sv).mean(axis=0), index=sample.columns).sort_values()
    top = imp.tail(18)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top.index.str.replace("_", " ", 1), top.values, color="#2f6fde")
    ax.set_xlabel("mean |SHAP value| on log(comp)")
    ax.set_title("What moves developer pay most (XGBoost + SHAP)")
    fig.tight_layout(); fig.savefig("charts/shap_importance.png", dpi=110); plt.close()
    print("\ntop-18 SHAP drivers:\n", top.tail(18).round(4).to_string())

    # --- partial dependence: experience curve ---
    ref = Xte.median(numeric_only=True).to_frame().T
    exps = np.arange(0, 31)
    preds = [np.exp(m.predict(ref.assign(exp=e))[0]) for e in exps]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(exps, preds, lw=2.5, color="#2f6fde")
    ax.set_xlabel("years of professional experience"); ax.set_ylabel("predicted comp (USD)")
    ax.set_title("The experience curve: pay keeps climbing for ~25 years, then flattens")
    fig.tight_layout(); fig.savefig("charts/experience_curve.png", dpi=110); plt.close()

    # --- partial dependence: remote & AI (average prediction by category) ---
    def pd_by(cat, vals):
        out = {}
        for v in vals:
            Xt = Xte.copy()
            for c in [c for c in Xte.columns if c.startswith(cat + "=")]:
                Xt[c] = 0
            Xt[f"{cat}={v}"] = 1
            out[v] = np.exp(m.predict(Xt)).mean()
        return out
    pd_remote = {k: float(v) for k, v in pd_by("remote_simple", sorted(d["remote_simple"].unique())).items()}
    pd_ai = {k: float(v) for k, v in pd_by("ai_freq", ["no_never", "no_soon", "monthly", "weekly", "daily"]).items()}
    with open("data/partial_dependence.json", "w") as f:
        json.dump({"r2": r2, "pd_remote": pd_remote, "pd_ai": pd_ai}, f, indent=1)
    print("\npartial-dependence remote:", {k: f"${v:,.0f}" for k, v in pd_remote.items()})
    print("partial-dependence AI:", {k: f"${v:,.0f}" for k, v in pd_ai.items()})

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, series, title in [(axes[0], pd_remote, "Remote arrangement"),
                              (axes[1], pd_ai, "AI tool usage")]:
        base = series.get("In-person", series.get("no_never"))
        ks = list(series.keys()); vs = [series[k] / base - 1 for k in ks]
        ax.bar(ks, vs, color=["#2f6fde" if v >= 0 else "#c0392b" for v in vs])
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(title); ax.set_ylabel("premium vs baseline")
        ax.set_xticklabels(ks, rotation=18, ha="right")
        for i, v in enumerate(vs):
            ax.text(i, v + (0.004 if v >= 0 else -0.012), f"{v:+.1%}", ha="center", fontsize=9)
    fig.suptitle("XGBoost partial dependence: remote pays a premium; AI usage pays too")
    fig.tight_layout(); fig.savefig("charts/pd_remote_ai.png", dpi=110); plt.close()

if __name__ == "__main__":
    main()
