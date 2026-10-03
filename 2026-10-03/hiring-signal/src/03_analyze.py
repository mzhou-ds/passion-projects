"""
Analysis + ML:

1. Monthly trends: post volume, remote share, AI-post share, salary-
   disclosure rate, median disclosed salary.
2. Tech demand leaderboard 2023 vs 2025-26: share change per technology.
3. KMeans clustering (k=5) of posts on their tech-mention profile ->
   hiring archetypes, named from their top terms.
4. XGBoost + SHAP: predict whether a post discloses a salary from
   work mode, AI flag, seniority, tech profile, thread month. Logistic
   baseline. Question: is salary transparency a company trait we can
   see in how the post is written?

Outputs: output/*.csv/json, charts/*.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT, CH = ROOT / "data", ROOT / "output", ROOT / "charts"


def main():
    OUT.mkdir(exist_ok=True); CH.mkdir(exist_ok=True)
    df = pd.read_csv(DATA / "posts_parsed.csv", parse_dates=["thread_dt"])
    tech_cols = [c for c in df.columns if c.startswith("tech_")]
    tech_names = [c[5:] for c in tech_cols]

    # ---- 1. monthly trends ----
    g = df.groupby("thread_month")
    trends = pd.DataFrame({
        "posts": g.size(),
        "remote_share": g.apply(lambda x: (x["work_mode"] == "remote").mean(), include_groups=False),
        "ai_share": g["is_ai_post"].mean(),
        "salary_share": g["has_salary"].mean(),
        "median_salary": g["salary_mid"].median(),
        "senior_share": g["is_senior"].mean(),
    }).reset_index()
    trends.to_csv(OUT / "monthly_trends.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    x = pd.to_datetime(trends["thread_month"])
    axes[0, 0].plot(x, trends["posts"], marker="o", ms=3); axes[0, 0].set_title("Job posts per Who-is-Hiring thread")
    axes[0, 0].grid(alpha=0.25)
    axes[0, 1].plot(x, trends["ai_share"] * 100, marker="o", ms=3, color="#b5651d"); axes[0, 1].set_title("% of posts mentioning AI/ML/LLM (%)")
    axes[0, 1].grid(alpha=0.25)
    axes[1, 0].plot(x, trends["remote_share"] * 100, marker="o", ms=3, color="#2b6cb0"); axes[1, 0].set_title("% remote (first-line) (%)")
    axes[1, 0].grid(alpha=0.25)
    axes[1, 1].plot(x, trends["salary_share"] * 100, marker="o", ms=3, color="#276749", label="disclose salary %")
    ax2 = axes[1, 1].twinx(); ax2.plot(x, trends["median_salary"] / 1000, color="#9b2c2c", marker="s", ms=3, label="median $k")
    axes[1, 1].set_title("Salary transparency % and median disclosed $k")
    axes[1, 1].grid(alpha=0.25)
    fig.autofmt_xdate(rotation=30); fig.tight_layout()
    fig.savefig(CH / "trends.png", dpi=160); plt.close(fig)

    # ---- 2. tech leaderboard: early vs late ----
    early = df[df["thread_dt"] < "2024-01-01"]; late = df[df["thread_dt"] >= "2025-01-01"]
    rows = []
    for c, name in zip(tech_cols, tech_names):
        rows.append({"tech": name, "share_2023": early[c].mean(), "share_2025_26": late[c].mean(),
                     "n_late": int(late[c].sum())})
    board = pd.DataFrame(rows)
    board["delta_pp"] = (board["share_2025_26"] - board["share_2023"]) * 100
    board = board.sort_values("delta_pp")
    board.to_csv(OUT / "tech_leaderboard.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 8))
    colors = ["#9b2c2c" if v < 0 else "#276749" for v in board["delta_pp"]]
    ax.barh(board["tech"], board["delta_pp"], color=colors)
    ax.set_xlabel("Change in % of posts mentioning (pp): 2023 → 2025–26")
    ax.set_title("Which stacks gained / lost hiring demand"); ax.grid(axis="x", alpha=0.25)
    fig.tight_layout(); fig.savefig(CH / "tech_leaderboard.png", dpi=160); plt.close(fig)

    # current top-15 chart
    top = board.sort_values("share_2025_26", ascending=True).tail(15)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["tech"], top["share_2025_26"] * 100, color="#2b6cb0")
    ax.set_xlabel("% of posts mentioning, 2025–26"); ax.set_title("Most-mentioned technologies, 2025–26")
    ax.grid(axis="x", alpha=0.25); fig.tight_layout(); fig.savefig(CH / "top_tech.png", dpi=160); plt.close(fig)

    # ---- 3. clustering ----
    X = df[tech_cols].astype(float)
    km = KMeans(n_clusters=5, n_init=20, random_state=42)
    df["cluster"] = km.fit_predict(X)
    prof = df.groupby("cluster")[tech_cols].mean()
    prof.columns = tech_names
    names = {}
    for cid, row in prof.iterrows():
        top3 = ", ".join(row.sort_values(ascending=False).head(3).index)
        names[cid] = top3
    cluster_summary = pd.DataFrame({
        "cluster": list(names.keys()),
        "top_terms": list(names.values()),
        "n_posts": df.groupby("cluster").size().values,
        "ai_share": df.groupby("cluster")["is_ai_post"].mean().values,
        "remote_share": df.groupby("cluster").apply(lambda x: (x["work_mode"] == "remote").mean(), include_groups=False).values,
        "salary_share": df.groupby("cluster")["has_salary"].mean().values,
        "median_salary": df.groupby("cluster")["salary_mid"].median().values,
    })
    cluster_summary.to_csv(OUT / "clusters.csv", index=False)
    prof.to_csv(OUT / "cluster_profiles.csv")

    # archetype share over time (yearly)
    df["year"] = df["thread_dt"].dt.year
    ct = pd.crosstab(df["year"], df["cluster"], normalize="index") * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    for cid in ct.columns:
        ax.plot(ct.index, ct[cid], marker="o", label=f"C{cid}: {names[cid][:38]}")
    ax.set_ylabel("% of posts"); ax.set_title("Hiring archetype mix by year")
    ax.legend(fontsize=7); ax.grid(alpha=0.25); fig.tight_layout()
    fig.savefig(CH / "archetypes.png", dpi=160); plt.close(fig)

    # ---- 4. salary-disclosure model ----
    feats_df = df.copy()
    feats_df["is_remote"] = (feats_df["work_mode"] == "remote").astype(int)
    feats_df["is_hybrid"] = (feats_df["work_mode"] == "hybrid").astype(int)
    feats_df["month_num"] = feats_df["thread_dt"].dt.year * 12 + feats_df["thread_dt"].dt.month
    feats = ["is_ai_post", "is_senior", "is_remote", "is_hybrid", "n_tech", "month_num"] + tech_cols
    X = feats_df[feats].astype(float).fillna(0); y = feats_df["has_salary"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    lr.fit(Xtr, ytr); lr_p = lr.predict_proba(Xte)[:, 1]
    xgb = XGBClassifier(n_estimators=350, max_depth=4, learning_rate=0.06, subsample=0.9,
                        colsample_bytree=0.9, eval_metric="logloss", random_state=42)
    xgb.fit(Xtr, ytr); xgb_p = xgb.predict_proba(Xte)[:, 1]
    results = {
        "n_posts": int(len(df)), "n_threads": int(df["story_id"].nunique()),
        "date_range": [str(df["thread_dt"].min().date()), str(df["thread_dt"].max().date())],
        "salary_base_rate": round(float(y.mean()), 4),
        "logreg_auc": round(float(roc_auc_score(yte, lr_p)), 4),
        "xgb_auc": round(float(roc_auc_score(yte, xgb_p)), 4),
        "xgb_acc": round(float(accuracy_score(yte, xgb_p > 0.5)), 4),
    }
    (OUT / "model_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

    expl = shap.TreeExplainer(xgb); sv = expl.shap_values(Xte)
    imp = pd.DataFrame({"feature": feats, "mean_abs_shap": np.abs(sv).mean(axis=0)}).sort_values("mean_abs_shap", ascending=True)
    imp.to_csv(OUT / "shap_importance.csv", index=False)
    fig, ax = plt.subplots(figsize=(8.5, 6))
    tail = imp.tail(15)
    ax.barh(tail["feature"], tail["mean_abs_shap"], color="#2b6cb0")
    ax.set_xlabel("mean |SHAP|"); ax.set_title("What predicts a post disclosing salary?")
    ax.grid(axis="x", alpha=0.25); fig.tight_layout(); fig.savefig(CH / "shap_importance.png", dpi=160); plt.close(fig)

    # AI vs non-AI salary gap (descriptive, disclosed only)
    sal = df[df["has_salary"]]
    gap = sal.groupby("is_ai_post")["salary_mid"].agg(["count", "median", "mean"])
    gap.to_csv(OUT / "ai_salary_gap.csv")
    print("\nAI salary gap:\n", gap.to_string())
    print("\nclusters:\n", cluster_summary.to_string(index=False))
    print("\nleaderboard:\n", board.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
