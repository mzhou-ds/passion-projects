"""Analysis for The One-Person Internet (npm census, 2026-11-28).

Reads data/packages.csv + data/deps_top200.json and computes:
 1. Download-weighted share by maintainer-count bucket (1, 2, 3-5, 6-10, 11+)
    for the top 1000 packages by weekly downloads, plus the unweighted
    (package-count) shares for contrast.
 2. Abandonment: share of downloads flowing through packages with no publish
    in 24+ months, by maintainer bucket.
 3. Concentration: cumulative download share of top 10 / 50 / 100 / 500.
 4. Blast radius: among the top 200 packages' direct dependencies, the share
    (unweighted and download-weighted where known) that are single-maintainer.
 5. Abandonment model: logistic regression (scipy) predicting P(abandoned)
    from log downloads, log dependents, maintainer count, scoped flag;
    odds ratios + permutation importance. A Kaplan-Meier-style "still alive"
    curve by maintainer bucket is also computed from last-publish ages.

Writes output/findings.json and prints a findings summary.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc)
ABANDON_DAYS = 730  # 24 months without a publish


def bucket(n):
    if n <= 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    return "11+"


def main():
    df = pd.read_csv(DATA / "packages.csv")
    df = df.dropna(subset=["name"])
    df["name"] = df["name"].astype(str)
    df["last_publish"] = pd.to_datetime(df["last_publish"], utc=True, errors="coerce")
    df["age_days"] = (NOW - df["last_publish"]).dt.days
    df["abandoned"] = df["age_days"] > ABANDON_DAYS
    df["maint_bucket"] = df["n_maintainers"].apply(bucket)
    df["scoped"] = df["name"].str.startswith("@").astype(int)
    df = df.sort_values("weekly_downloads", ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)

    top = df.head(1000).copy()
    total_dl = top["weekly_downloads"].sum()

    findings = {"n_packages_pool": len(df), "top1000_weekly_downloads": int(total_dl)}

    # 1. Download-weighted vs package-count shares by maintainer bucket
    order = ["1", "2", "3-5", "6-10", "11+"]
    g = top.groupby("maint_bucket").agg(
        n=("name", "count"),
        downloads=("weekly_downloads", "sum"),
    ).reindex(order)
    g["pkg_share"] = g["n"] / len(top)
    g["dl_share"] = g["downloads"] / total_dl
    findings["maintainer_buckets_top1000"] = {
        b: {"n": int(g.loc[b, "n"]), "pkg_share": round(float(g.loc[b, "pkg_share"]), 4),
            "dl_share": round(float(g.loc[b, "dl_share"]), 4)}
        for b in order
    }

    # Single-maintainer headline numbers
    solo = top[top["n_maintainers"] <= 1]
    findings["solo_top1000"] = {
        "n": int(len(solo)),
        "dl_share": round(float(solo["weekly_downloads"].sum() / total_dl), 4),
        "median_weekly_downloads": int(solo["weekly_downloads"].median()),
    }

    # 2. Abandonment
    ab = top[top["abandoned"]]
    findings["abandoned_top1000"] = {
        "n": int(len(ab)),
        "pkg_share": round(float(len(ab) / len(top)), 4),
        "dl_share": round(float(ab["weekly_downloads"].sum() / total_dl), 4),
    }
    ab_by = top.groupby("maint_bucket").apply(
        lambda x: pd.Series({
            "n": len(x), "n_abandoned": int(x["abandoned"].sum()),
            "abandon_rate": round(float(x["abandoned"].mean()), 4),
            "abandoned_dl_share": round(float(
                x.loc[x["abandoned"], "weekly_downloads"].sum() / x["weekly_downloads"].sum()), 4),
        })).reindex(order)
    findings["abandonment_by_bucket"] = {
        b: {k: (int(v) if isinstance(v, (np.integer, int)) else float(v))
            for k, v in ab_by.loc[b].items()} for b in order
    }
    solo_ab = top[(top["n_maintainers"] <= 1) & (top["abandoned"])]
    findings["solo_and_abandoned"] = {
        "n": int(len(solo_ab)),
        "dl_share": round(float(solo_ab["weekly_downloads"].sum() / total_dl), 4),
    }
    # Most-downloaded abandoned packages (the "zombie core")
    findings["top_abandoned_packages"] = [
        {"name": r["name"], "weekly_downloads": int(r["weekly_downloads"]),
         "n_maintainers": int(r["n_maintainers"]),
         "last_publish": str(r["last_publish"].date()) if pd.notna(r["last_publish"]) else None}
        for _, r in ab.head(15).iterrows()
    ]

    # 3. Concentration
    cum = top["weekly_downloads"].cumsum() / total_dl
    findings["concentration"] = {
        f"top_{k}": round(float(cum.iloc[k - 1]), 4) for k in (10, 50, 100, 250, 500)
    }
    findings["top10_packages"] = [
        {"name": r["name"], "weekly_downloads": int(r["weekly_downloads"]),
         "n_maintainers": int(r["n_maintainers"])}
        for _, r in top.head(10).iterrows()
    ]

    # 4. Blast radius: direct deps of the top 200 (deps file may also hold
    # parents from the pre-repair top-200 set; restrict to the current top 200)
    with open(DATA / "deps_top200.json") as f:
        deps_all = json.load(f)
    top200_names = set(df.head(200)["name"])
    deps = {k: v for k, v in deps_all.items() if k in top200_names}
    pool = df.set_index("name")
    dep_rows = []
    for parent, children in deps.items():
        for child in children:
            dep_rows.append({"parent": parent, "dep": child})
    dep_df = pd.DataFrame(dep_rows)
    dep_df["dep_in_pool"] = dep_df["dep"].isin(pool.index)
    known = dep_df[dep_df["dep_in_pool"]].copy()
    known["dep_maintainers"] = known["dep"].map(pool["n_maintainers"])
    known["dep_downloads"] = known["dep"].map(pool["weekly_downloads"])
    known["dep_solo"] = known["dep_maintainers"] <= 1
    known["dep_abandoned"] = known["dep"].map(pool["abandoned"])
    findings["blast_radius"] = {
        "top_parents": len(deps),
        "dep_edges": int(len(dep_df)),
        "unique_deps": int(dep_df["dep"].nunique()),
        "deps_resolved_in_pool": int(dep_df["dep_in_pool"].sum()),
        "solo_share_of_known_dep_edges": round(float(known["dep_solo"].mean()), 4),
        "solo_share_of_unique_known_deps": round(float(
            known.drop_duplicates("dep")["dep_solo"].mean()), 4),
        "abandoned_share_of_known_dep_edges": round(float(known["dep_abandoned"].mean()), 4),
    }
    # Which top packages depend most heavily on solo-maintained deps?
    per_parent = known.groupby("parent").agg(
        n_deps=("dep", "count"), n_solo=("dep_solo", "sum"))
    per_parent["solo_frac"] = per_parent["n_solo"] / per_parent["n_deps"]
    per_parent = per_parent.sort_values("solo_frac", ascending=False)
    findings["most_solo_dependent_top_packages"] = [
        {"name": idx, "n_deps": int(r["n_deps"]), "n_solo": int(r["n_solo"]),
         "solo_frac": round(float(r["solo_frac"]), 3)}
        for idx, r in per_parent.head(12).iterrows()
    ]
    # How many of the top 200 have at least one solo dep / one abandoned dep?
    has_solo = per_parent[per_parent["n_solo"] > 0].index
    has_ab = known[known["dep_abandoned"]].groupby("parent").size().index
    findings["blast_radius"]["parents_with_solo_dep"] = int(len(has_solo))
    findings["blast_radius"]["parents_with_abandoned_dep"] = int(len(has_ab))
    findings["blast_radius"]["parents_with_solo_dep_share"] = round(len(has_solo) / len(deps), 4)

    # 5. Abandonment model (logistic regression, scipy)
    # Target: abandoned (no publish in 24m). Features: log downloads,
    # log dependents, maintainer count, scoped flag. Fit on top 1000.
    m = top.dropna(subset=["age_days"]).copy()
    X = np.column_stack([
        np.ones(len(m)),
        np.log1p(m["weekly_downloads"].values),
        np.log1p(m["dependents"].values),
        m["n_maintainers"].values,
        m["scoped"].values,
    ])
    y = m["abandoned"].values.astype(float)
    names = ["intercept", "log_downloads", "log_dependents", "n_maintainers", "scoped"]

    def nll(beta):
        z = X @ beta
        return float(np.sum(np.logaddexp(0, z) - y * z) + 1e-6 * np.sum(beta ** 2))

    def grad(beta):
        p = expit(X @ beta)
        return X.T @ (p - y) + 2e-6 * beta

    res = minimize(nll, np.zeros(X.shape[1]), jac=grad, method="BFGS")
    beta = res.x
    # Standard errors from the Hessian (BFGS inverse approx)
    try:
        cov = res.hess_inv
        se = np.sqrt(np.diag(cov))
    except Exception:
        se = np.full_like(beta, np.nan)
    p_hat = expit(X @ beta)
    ll = -nll(beta)
    ll0 = float(np.sum(y * np.log(y.mean()) + (1 - y) * np.log(1 - y.mean())))
    mcfadden = 1 - ll / ll0
    # Baseline accuracy vs model accuracy at 0.5 threshold
    acc = float(np.mean((p_hat > 0.5) == (y == 1)))
    base_acc = float(max(y.mean(), 1 - y.mean()))
    # Permutation importance (increase in NLL when a column is shuffled:
    # positive = the feature carries signal)
    rng = np.random.default_rng(7)
    perm = {}
    base_nll = nll(beta)
    for j in range(1, X.shape[1]):
        increases = []
        for _ in range(20):
            Xp = X.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            increases.append(float(np.sum(
                np.logaddexp(0, Xp @ beta) - y * (Xp @ beta))) - base_nll)
        perm[names[j]] = round(float(np.mean(increases)), 1)
    findings["abandonment_model"] = {
        "n": int(len(m)), "abandoned_rate": round(float(y.mean()), 4),
        "mcfadden_r2": round(mcfadden, 4),
        "accuracy": round(acc, 4), "baseline_accuracy": round(base_acc, 4),
        "coefficients": [
            {"feature": names[i], "beta": round(float(beta[i]), 4),
             "se": round(float(se[i]), 4) if np.isfinite(se[i]) else None,
             "odds_ratio": round(float(np.exp(beta[i])), 4)}
            for i in range(len(names))
        ],
        "permutation_importance_nll_increase": perm,
    }
    # Predicted abandonment probability for a solo package at median downloads
    med_dl = float(np.median(m["weekly_downloads"]))
    med_dep = float(np.median(m["dependents"]))
    for nm, nm_val in [("solo_maintainer", 1), ("five_maintainers", 5)]:
        xb = beta[0] + beta[1] * np.log1p(med_dl) + beta[2] * np.log1p(med_dep) \
            + beta[3] * nm_val + beta[4] * 0
        findings["abandonment_model"][f"pred_abandoned_p_{nm}"] = round(float(expit(xb)), 4)

    # Survival-style table: share still "alive" (published within 24m) by bucket
    surv = top.groupby("maint_bucket")["abandoned"].agg(["mean", "count"]).reindex(order)
    findings["alive_share_by_bucket"] = {
        b: round(float(1 - surv.loc[b, "mean"]), 4) for b in order
    }

    with open(OUT / "findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
