#!/usr/bin/env python3
"""
The Drop Doesn't Matter — does EDM's sound predict its popularity?

Data: maharshipandya/spotify-tracks-dataset (Hugging Face, ~114k tracks,
125 genre labels in source, 114 genres x 1000 tracks in the parquet snapshot).
Single-file download from Hugging Face parquet endpoint. No API hammering.

Analyses:
  1. Structure economics — EDM family vs pop / hip-hop / rock
  2. XGBoost popularity model within EDM (audio features only) + SHAP
  3. KMeans clustering of EDM archetypes
  4. Arbitrage table — predicted vs actual popularity gaps

Outputs: figures/*.png, results.json, findings.txt
Reproduce: python3 analysis.py
"""
import json
import os
import textwrap
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------- config
BASE = Path(__file__).resolve().parent
FIGDIR = BASE / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)
CACHE = BASE / "spotify_tracks.parquet"
URL = "https://huggingface.co/api/datasets/maharshipandya/spotify-tracks-dataset/parquet/default/train/0.parquet"

EDM_GENRES = [
    "edm", "house", "chicago-house", "deep-house", "progressive-house",
    "techno", "detroit-techno", "minimal-techno", "trance", "dubstep",
    "drum-and-bass", "electro", "electronic", "dance", "club",
    "breakbeat", "garage", "hardstyle", "idm",
]
AUDIO_FEATURES = [
    "danceability", "energy", "loudness", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "duration_ms",
    "key", "mode", "time_signature",
]
CLUSTER_FEATURES = [
    "danceability", "energy", "loudness", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "duration_ms",
]
RANDOM_STATE = 42

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
})

# ---------------------------------------------------------------- helpers
def download_data() -> Path:
    if CACHE.exists() and CACHE.stat().st_size > 1_000_000:
        print(f"[data] using cached {CACHE} ({CACHE.stat().st_size/1e6:.1f} MB)")
        return CACHE
    print(f"[data] downloading {URL} -> {CACHE}")
    import urllib.request
    req = urllib.request.Request(URL, headers={"User-Agent": "passion-projects/1.0"})
    with urllib.request.urlopen(req) as r, open(CACHE, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    print(f"[data] saved {CACHE.stat().st_size/1e6:.1f} MB")
    return CACHE


def fmt(x, nd=1):
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    try:
        return f"{float(x):,.{nd}f}"
    except Exception:
        return str(x)


# ---------------------------------------------------------------- main
def main():
    path = download_data()
    df = pd.read_parquet(path)
    print(f"[data] loaded {len(df):,} tracks, {df['track_genre'].nunique()} genres")
    print(f"[data] columns: {list(df.columns)}")

    # clean: drop extreme duration outliers (>15 min) for structure stats robustness
    df["duration_sec"] = df["duration_ms"] / 1000.0
    df_clean = df[(df["duration_sec"] > 20) & (df["duration_sec"] < 900)].copy()
    print(f"[data] after duration filter 20-900s: {len(df_clean):,} tracks")

    results = {}
    results["dataset"] = {
        "rows_total": int(len(df)),
        "rows_clean": int(len(df_clean)),
        "genres_total": int(df["track_genre"].nunique()),
        "source_url": URL,
        "edm_genres": EDM_GENRES,
        "edm_n": int(df_clean["track_genre"].isin(EDM_GENRES).sum()),
    }

    # ============================================================ 1. STRUCTURE
    print("\n=== 1. STRUCTURE ECONOMICS ===")
    groups = {
        "EDM family": df_clean[df_clean["track_genre"].isin(EDM_GENRES)],
        "pop": df_clean[df_clean["track_genre"] == "pop"],
        "hip-hop": df_clean[df_clean["track_genre"] == "hip-hop"],
        "rock": df_clean[df_clean["track_genre"] == "rock"],
    }
    for name, sub in groups.items():
        print(f"  {name}: n={len(sub):,}")

    struct_metrics = ["duration_sec", "tempo", "energy", "instrumentalness", "danceability", "loudness", "valence"]
    medians = {}
    for name, sub in groups.items():
        medians[name] = {m: float(sub[m].median()) for m in struct_metrics}
        medians[name]["popularity_median"] = float(sub["popularity"].median())
        medians[name]["popularity_mean"] = float(sub["popularity"].mean())
        medians[name]["n"] = int(len(sub))
    results["structure_medians"] = medians

    for m in struct_metrics + ["popularity_median"]:
        row = " | ".join(f"{name}={medians[name][m]:.2f}" for name in groups)
        print(f"  {m}: {row}")

    # --- figure 1: distributions (violin-ish via box + strip logic, use violins)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Structure economics: EDM is built differently\n(114k Spotify tracks; EDM family = 19 genres)", fontsize=13, fontweight="bold")
    plot_cfg = [
        ("duration_sec", "Duration (seconds)", axes[0, 0]),
        ("tempo", "Tempo (BPM)", axes[0, 1]),
        ("energy", "Energy (0-1, Spotify)", axes[1, 0]),
        ("instrumentalness", "Instrumentalness (0-1, Spotify)", axes[1, 1]),
    ]
    colors = {"EDM family": "#1DB954", "pop": "#E91E63", "hip-hop": "#FF9800", "rock": "#607D8B"}
    for col, label, ax in plot_cfg:
        data = [groups[g][col].values for g in groups]
        labels = list(groups.keys())
        parts = ax.violinplot(data, showmedians=True, showmeans=False)
        for pc, lab in zip(parts["bodies"], labels):
            pc.set_facecolor(colors[lab]); pc.set_alpha(0.65); pc.set_edgecolor("black"); pc.set_linewidth(0.6)
        parts["cmedians"].set_color("black"); parts["cmedians"].set_linewidth(1.2)
        ax.set_xticks(range(1, len(labels) + 1)); ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel(label); ax.set_title(label)
        ax.grid(axis="y", alpha=0.3)
        if col == "duration_sec":
            ax.set_ylim(0, 600)
        if col == "instrumentalness":
            ax.set_ylim(-0.05, 1.05)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    f1 = FIGDIR / "fig1_structure_distributions.png"
    plt.savefig(f1, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f1.name}")

    # median comparison bar for README traceability
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(struct_metrics))
    w = 0.19
    for i, (gname, gmed) in enumerate(medians.items()):
        vals = []
        # normalize: duration/tempo scaled for visual only — use raw with twin note instead
        # Instead plot standardized median differences: just raw per-metric grouped bars on separate scales is messy.
        # Use popularity + energy/danceability/instrumentalness (0-1) + tempo/200 + duration/400 as scaled.
        pass
    # Simpler: two-panel median chart
    plt.close()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [1.4, 1]})
    metrics_01 = ["energy", "danceability", "instrumentalness", "valence"]
    x = np.arange(len(metrics_01)); w = 0.18
    for i, (gname, gmed) in enumerate(medians.items()):
        vals = [gmed[m] for m in metrics_01]
        ax1.bar(x + (i - 1.5) * w, vals, w, label=gname, color=colors[gname], edgecolor="black", linewidth=0.5)
    ax1.set_xticks(x); ax1.set_xticklabels(metrics_01, rotation=15)
    ax1.set_ylabel("Median (0-1 scale)"); ax1.set_title("Audio-feature medians (0-1 features)")
    ax1.legend(fontsize=8); ax1.grid(axis="y", alpha=0.3); ax1.set_ylim(0, 1.05)
    metrics_scaled = ["duration_sec", "tempo"]
    x2 = np.arange(len(metrics_scaled))
    for i, (gname, gmed) in enumerate(medians.items()):
        vals = [gmed["duration_sec"], gmed["tempo"]]
        ax2.bar(x2 + (i - 1.5) * w, vals, w, label=gname, color=colors[gname], edgecolor="black", linewidth=0.5)
    ax2.set_xticks(x2); ax2.set_xticklabels(["duration (s)", "tempo (BPM)"])
    ax2.set_title("Duration & tempo medians"); ax2.grid(axis="y", alpha=0.3)
    fig.suptitle("Median structure: EDM vs pop vs hip-hop vs rock", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    f1b = FIGDIR / "fig1b_median_bars.png"
    plt.savefig(f1b, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f1b.name}")

    # ============================================================ 2. POPULARITY MODEL
    print("\n=== 2. POPULARITY MODEL (within EDM family) ===")
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
    import xgboost as xgb

    edm = df_clean[df_clean["track_genre"].isin(EDM_GENRES)].copy()
    print(f"  EDM family n={len(edm):,}, popularity mean={edm['popularity'].mean():.1f} median={edm['popularity'].median():.0f}")
    X = edm[AUDIO_FEATURES].copy()
    # duration in seconds is more interpretable; keep ms for model but also add sec copy for SHAP readability
    X = X.rename(columns={"duration_ms": "duration_sec"})
    X["duration_sec"] = X["duration_sec"] / 1000.0
    feature_names = list(X.columns)
    y = edm["popularity"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
    print(f"  train={len(X_train):,} test={len(X_test):,} features={feature_names}")

    # baseline: predict train median
    baseline_pred = np.full_like(y_test.values, y_train.median(), dtype=float)
    baseline_r2 = r2_score(y_test, baseline_pred)
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    print(f"  baseline (median) R2={baseline_r2:.4f} MAE={baseline_mae:.2f}")

    model = xgb.XGBRegressor(
        n_estimators=600, max_depth=5, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, reg_lambda=1.0,
        random_state=RANDOM_STATE, n_jobs=4, verbosity=0,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    # also train R2 to show overfit gap
    y_pred_train = model.predict(X_train)
    r2_train = r2_score(y_train, y_pred_train)
    print(f"  XGBoost test R2={r2:.4f} MAE={mae:.2f} RMSE={rmse:.2f} | train R2={r2_train:.4f}")

    results["model"] = {
        "n_edm": int(len(edm)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "features": feature_names,
        "test_r2": float(r2),
        "test_mae": float(mae),
        "test_rmse": float(rmse),
        "train_r2": float(r2_train),
        "baseline_r2": float(baseline_r2),
        "baseline_mae": float(baseline_mae),
        "popularity_mean_edm": float(edm["popularity"].mean()),
        "popularity_median_edm": float(edm["popularity"].median()),
        "popularity_std_edm": float(edm["popularity"].std()),
    }

    # feature importance (gain)
    imp = model.feature_importances_
    imp_order = np.argsort(imp)[::-1]
    print("  XGBoost gain importance:")
    for idx in imp_order:
        print(f"    {feature_names[idx]}: {imp[idx]:.4f}")
    results["model"]["xgb_importance"] = {feature_names[i]: float(imp[i]) for i in range(len(feature_names))}

    # correlations for honest framing
    corrs = {}
    for f in feature_names:
        corrs[f] = float(np.corrcoef(edm.assign(duration_sec=edm["duration_ms"]/1000)[f] if f=="duration_sec" else edm[f], edm["popularity"])[0,1]) if f in edm.columns or f=="duration_sec" else 0
    # recompute cleanly
    edm_tmp = edm.copy(); edm_tmp["duration_sec"] = edm_tmp["duration_ms"]/1000
    for f in feature_names:
        corrs[f] = float(edm_tmp[f].corr(edm_tmp["popularity"]))
    print("  Pearson r with popularity (EDM family):")
    for f, v in sorted(corrs.items(), key=lambda kv: abs(kv[1]), reverse=True):
        print(f"    {f}: {v:+.3f}")
    results["model"]["pearson_r"] = corrs

    # SHAP
    print("  computing SHAP...")
    import shap
    explainer = shap.TreeExplainer(model)
    # sample for speed on summary (max 2000)
    shap_sample_idx = np.random.RandomState(RANDOM_STATE).choice(len(X_test), size=min(2000, len(X_test)), replace=False)
    X_shap = X_test.iloc[shap_sample_idx]
    shap_values = explainer.shap_values(X_shap)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_order = np.argsort(mean_abs_shap)[::-1]
    print("  SHAP mean |value| ranking:")
    for idx in shap_order:
        print(f"    {feature_names[idx]}: {mean_abs_shap[idx]:.3f}")
    results["model"]["shap_mean_abs"] = {feature_names[i]: float(mean_abs_shap[i]) for i in range(len(feature_names))}
    results["model"]["shap_ranking"] = [feature_names[i] for i in shap_order]

    # SHAP summary (beeswarm)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_shap, feature_names=feature_names, show=False, plot_size=(10, 6))
    plt.title("SHAP summary: what moves predicted popularity in EDM?\n(each dot = one track; color = feature value)", fontsize=11)
    plt.tight_layout()
    f2 = FIGDIR / "fig2_shap_summary.png"
    plt.savefig(f2, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f2.name}")

    # SHAP dependence for top 3
    top3 = [feature_names[i] for i in shap_order[:3]]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    fig.suptitle(f"SHAP dependence: top drivers ({', '.join(top3)})", fontweight="bold")
    for ax, feat in zip(axes, top3):
        fidx = feature_names.index(feat)
        # scatter: feature value vs SHAP value, colored low alpha
        xv = X_shap[feat].values
        sv = shap_values[:, fidx]
        ax.scatter(xv, sv, s=6, alpha=0.35, color="#1DB954", edgecolors="none")
        # binned mean line
        bins = np.quantile(xv, np.linspace(0, 1, 16))
        bins = np.unique(bins)
        centers, means = [], []
        for b in range(len(bins)-1):
            mask = (xv >= bins[b]) & (xv <= bins[b+1] if b==len(bins)-2 else xv < bins[b+1])
            if mask.sum() > 5:
                centers.append(xv[mask].mean()); means.append(sv[mask].mean())
        ax.plot(centers, means, color="black", linewidth=1.6)
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.set_xlabel(feat); ax.set_title(feat)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("SHAP value (impact on predicted popularity)")
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    f3 = FIGDIR / "fig3_shap_dependence.png"
    plt.savefig(f3, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f3.name}")

    # predicted vs actual scatter (test set)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_test, y_pred, s=6, alpha=0.25, color="#1DB954", edgecolors="none")
    ax.plot([0, 100], [0, 100], "k--", linewidth=1, label="perfect prediction")
    ax.set_xlabel("Actual popularity (Spotify 0-100)")
    ax.set_ylabel("Predicted popularity (audio features only)")
    ax.set_title(f"Audio features barely predict EDM popularity\nTest R² = {r2:.3f}, MAE = {mae:.1f} points (n={len(X_test):,})")
    ax.set_xlim(-3, 103); ax.set_ylim(-3, 103)
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    f3b = FIGDIR / "fig3b_pred_vs_actual.png"
    plt.savefig(f3b, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f3b.name}")

    # ============================================================ 3. CLUSTERING
    print("\n=== 3. CLUSTERING EDM ARCHETYPES ===")
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    edm_c = edm.copy()
    edm_c["duration_sec"] = edm_c["duration_ms"] / 1000.0
    Xc = edm_c[CLUSTER_FEATURES].copy()
    # duration_ms -> sec for clustering scale sanity
    Xc = Xc.rename(columns={"duration_ms": "duration_sec"})
    Xc["duration_sec"] = edm_c["duration_sec"]
    cluster_feats = list(Xc.columns)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(Xc)

    # choose k via silhouette on subsample
    sil_scores = {}
    rng = np.random.RandomState(RANDOM_STATE)
    sub_idx = rng.choice(len(Xs), size=min(4000, len(Xs)), replace=False)
    for k in [3, 4, 5, 6, 7]:
        km_tmp = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels_tmp = km_tmp.fit_predict(Xs)
        sil = silhouette_score(Xs[sub_idx], labels_tmp[sub_idx])
        sil_scores[k] = float(sil)
        print(f"  k={k} silhouette={sil:.4f}")
    results["clustering_silhouette"] = sil_scores
    # task says 4-6; pick best in 4-6
    best_k = max([4, 5, 6], key=lambda k: sil_scores[k])
    print(f"  chosen k={best_k} (best silhouette in 4-6)")

    km = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=20)
    edm_c["cluster"] = km.fit_predict(Xs)

    # cluster profiles: means in original units + standardized for naming
    profiles = edm_c.groupby("cluster")[cluster_feats + ["popularity"]].mean()
    counts = edm_c["cluster"].value_counts().sort_index()
    med_pop = edm_c.groupby("cluster")["popularity"].median()
    # dominant genres per cluster
    dom_genres = {}
    for c in range(best_k):
        vc = edm_c[edm_c["cluster"] == c]["track_genre"].value_counts(normalize=True).head(4)
        dom_genres[int(c)] = {str(k): float(v) for k, v in vc.items()}
    print(profiles.round(3).to_string())
    print("  cluster sizes:", dict(counts))
    print("  median popularity by cluster:", dict(med_pop.round(1)))

    # name clusters by profile heuristics
    overall = edm_c[cluster_feats].mean()
    def name_cluster(row):
        tags = []
        if row["instrumentalness"] > overall["instrumentalness"] + 0.12:
            tags.append("instrumental")
        if row["energy"] > overall["energy"] + 0.05:
            tags.append("high-energy")
        if row["energy"] < overall["energy"] - 0.05:
            tags.append("low-energy")
        if row["danceability"] > overall["danceability"] + 0.05:
            tags.append("groove-led")
        if row["tempo"] > overall["tempo"] + 8:
            tags.append("fast")
        if row["tempo"] < overall["tempo"] - 8:
            tags.append("slow")
        if row["acousticness"] > overall["acousticness"] + 0.08:
            tags.append("acoustic-leaning")
        if row["speechiness"] > overall["speechiness"] + 0.03:
            tags.append("vocal/talk")
        if row["duration_sec"] > overall["duration_sec"] + 30:
            tags.append("long-form")
        if row["duration_sec"] < overall["duration_sec"] - 30:
            tags.append("short-form")
        if row["valence"] > overall["valence"] + 0.08:
            tags.append("euphoric")
        if row["valence"] < overall["valence"] - 0.08:
            tags.append("dark")
        return ", ".join(tags) if tags else "mainstream middle"

    cluster_names = {}
    for c in range(best_k):
        cluster_names[int(c)] = name_cluster(profiles.loc[c])
    print("  cluster names:")
    for c, n in cluster_names.items():
        print(f"    cluster {c}: {n} | top genres: {list(dom_genres[c].keys())}")

    results["clustering"] = {
        "k": int(best_k),
        "features": cluster_feats,
        "sizes": {int(k): int(v) for k, v in counts.items()},
        "names": cluster_names,
        "mean_popularity": {int(k): float(v) for k, v in profiles["popularity"].items()},
        "median_popularity": {int(k): float(v) for k, v in med_pop.items()},
        "profiles_mean": {int(c): {f: float(profiles.loc[c, f]) for f in cluster_feats + ["popularity"]} for c in range(best_k)},
        "dominant_genres": dom_genres,
    }

    # figure: cluster profile heatmap (z-scored) + popularity bars
    prof_z = (profiles[cluster_feats] - profiles[cluster_feats].mean()) / profiles[cluster_feats].std()
    fig, (axh, axb) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [2.2, 1]})
    im = axh.imshow(prof_z.values, cmap="RdYlGn", vmin=-1.6, vmax=1.6, aspect="auto")
    axh.set_xticks(range(len(cluster_feats))); axh.set_xticklabels(cluster_feats, rotation=30, ha="left", fontsize=8)
    axh.set_yticks(range(best_k))
    axh.set_yticklabels([f"C{c}: {cluster_names[c][:38]}" for c in range(best_k)], fontsize=8)
    axh.set_title("Cluster profiles (z-scored means; green = above EDM average)")
    for i in range(best_k):
        for j in range(len(cluster_feats)):
            axh.text(j, i, f"{prof_z.values[i, j]:+.1f}", ha="center", va="center", fontsize=7, color="black")
    plt.colorbar(im, ax=axh, shrink=0.85, label="z-score")
    pops = [profiles.loc[c, "popularity"] for c in range(best_k)]
    bars = axb.barh(range(best_k), pops, color="#1DB954", edgecolor="black")
    axb.set_yticks(range(best_k)); axb.set_yticklabels([f"C{c}" for c in range(best_k)])
    axb.set_xlabel("Mean popularity")
    axb.set_title("Mean popularity by archetype")
    axb.grid(axis="x", alpha=0.3)
    for i, v in enumerate(pops):
        axb.text(v + 0.4, i, f"{v:.1f}", va="center", fontsize=9)
    axb.set_xlim(0, max(pops) * 1.25)
    fig.suptitle(f"EDM archetypes (KMeans k={best_k}): sound clusters, popularity doesn't follow", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    f4 = FIGDIR / "fig4_cluster_profiles.png"
    plt.savefig(f4, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f4.name}")

    # PCA scatter colored by cluster + popularity
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    Xp = pca.fit_transform(Xs)
    print(f"  PCA explained variance: PC1={pca.explained_variance_ratio_[0]:.3f} PC2={pca.explained_variance_ratio_[1]:.3f}")
    results["clustering"]["pca_var"] = [float(v) for v in pca.explained_variance_ratio_]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    sc1 = ax1.scatter(Xp[:, 0], Xp[:, 1], c=edm_c["cluster"].values, cmap="tab10", s=4, alpha=0.5)
    ax1.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)"); ax1.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax1.set_title("EDM tracks by sound (color = cluster)"); ax1.grid(alpha=0.3)
    # legend
    for c in range(best_k):
        ax1.scatter([], [], c=plt.cm.tab10(c / max(1, best_k - 1)), label=f"C{c} {cluster_names[c][:26]}", s=30)
    ax1.legend(fontsize=7, loc="best")
    sc2 = ax2.scatter(Xp[:, 0], Xp[:, 1], c=edm_c["popularity"].values, cmap="viridis", s=4, alpha=0.6, vmin=0, vmax=100)
    ax2.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)"); ax2.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax2.set_title("Same map, color = actual popularity"); ax2.grid(alpha=0.3)
    plt.colorbar(sc2, ax=ax2, label="Popularity")
    fig.suptitle("Sound space vs popularity space: popularity is smeared everywhere", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    f4b = FIGDIR / "fig4b_pca_clusters.png"
    plt.savefig(f4b, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f4b.name}")

    # ============================================================ 4. ARBITRAGE
    print("\n=== 4. ARBITRAGE TABLE ===")
    # Use test-set predictions (out-of-sample) joined back to track metadata
    test_meta = edm.loc[X_test.index, ["artists", "track_name", "track_genre", "popularity"]].copy()
    test_meta["predicted"] = y_pred
    test_meta["gap"] = test_meta["predicted"] - test_meta["popularity"]  # + = underexposed (sound predicts more)
    test_meta = test_meta.sort_values("gap", ascending=False)

    underexposed = test_meta.head(15)
    overexposed = test_meta.tail(15).iloc[::-1]  # most negative gap first
    print("  UNDEREXPOSED (predicted >> actual) — top 15:")
    for _, r in underexposed.iterrows():
        print(f"    {r['artists']} — {r['track_name']} [{r['track_genre']}] actual={r['popularity']:.0f} pred={r['predicted']:.1f} gap={r['gap']:+.1f}")
    print("  OVEREXPOSED (actual >> predicted) — top 15:")
    for _, r in overexposed.iterrows():
        print(f"    {r['artists']} — {r['track_name']} [{r['track_genre']}] actual={r['popularity']:.0f} pred={r['predicted']:.1f} gap={r['gap']:+.1f}")

    def rows_to_list(df_):
        out = []
        for _, r in df_.iterrows():
            out.append({
                "artists": str(r["artists"]), "track_name": str(r["track_name"]),
                "genre": str(r["track_genre"]), "actual": float(r["popularity"]),
                "predicted": float(r["predicted"]), "gap": float(r["gap"]),
            })
        return out

    results["arbitrage"] = {
        "note": "Gap = predicted (audio-only XGBoost, test set) minus actual Spotify popularity. Positive gap = sound predicts more popularity than the track has (underexposed by sound). Negative = popularity exceeds what sound predicts (fame/catalog effects dominate). Test-set only, out-of-sample.",
        "underexposed_top15": rows_to_list(underexposed),
        "overexposed_top15": rows_to_list(overexposed),
        "test_gap_mean": float(test_meta["gap"].mean()),
        "test_gap_std": float(test_meta["gap"].std()),
    }

    # arbitrage scatter with highlights
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(test_meta["popularity"], test_meta["predicted"], s=6, alpha=0.2, color="grey", label="all test tracks")
    ax.scatter(underexposed["popularity"], underexposed["predicted"], s=55, color="#1DB954", edgecolors="black", label="underexposed (pred >> actual)", zorder=5)
    ax.scatter(overexposed["popularity"], overexposed["predicted"], s=55, color="#E91E63", edgecolors="black", label="overexposed (actual >> pred)", zorder=5)
    ax.plot([0, 100], [0, 100], "k--", linewidth=1)
    ax.set_xlabel("Actual popularity"); ax.set_ylabel("Predicted (audio only)")
    ax.set_title("The arbitrage map: sound vs score\n(green = sound says bigger than it is; pink = fame says bigger than sound)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3); ax.set_xlim(-3, 103); ax.set_ylim(-3, 103)
    plt.tight_layout()
    f5 = FIGDIR / "fig5_arbitrage_scatter.png"
    plt.savefig(f5, bbox_inches="tight"); plt.close()
    print(f"  [fig] {f5.name}")

    # genre-level: mean popularity within EDM by genre (context)
    genre_pop = edm.groupby("track_genre")["popularity"].agg(["mean", "median", "count"]).sort_values("mean", ascending=True)
    print("\n  EDM subgenre popularity (mean):")
    print(genre_pop.round(1).to_string())
    results["edm_subgenre_popularity"] = {
        str(k): {"mean": float(v["mean"]), "median": float(v["median"]), "n": int(v["count"])}
        for k, v in genre_pop.iterrows()
    }

    # ============================================================ write outputs
    out_json = BASE / "results.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[write] {out_json}")

    # findings.txt — human traceable summary
    lines = []
    lines.append("THE DROP DOESN'T MATTER — findings trace (all numbers from this run)")
    lines.append("=" * 70)
    lines.append(f"Dataset: {results['dataset']['rows_total']} tracks, {results['dataset']['genres_total']} genres, EDM n={results['dataset']['edm_n']}")
    lines.append("")
    lines.append("STRUCTURE MEDIANS:")
    for g, m in medians.items():
        lines.append(f"  {g} (n={m['n']}): dur={m['duration_sec']:.0f}s tempo={m['tempo']:.1f} energy={m['energy']:.3f} instr={m['instrumentalness']:.3f} dance={m['danceability']:.3f} pop_med={m['popularity_median']:.0f} pop_mean={m['popularity_mean']:.1f}")
    lines.append("")
    lines.append(f"MODEL (EDM only, audio features): test R2={r2:.4f} MAE={mae:.2f} RMSE={rmse:.2f} train R2={r2_train:.4f} baseline MAE={baseline_mae:.2f}")
    lines.append(f"  SHAP ranking: {', '.join(results['model']['shap_ranking'])}")
    lines.append(f"  Pearson r: " + ", ".join(f"{k}={v:+.3f}" for k, v in sorted(corrs.items(), key=lambda kv: abs(kv[1]), reverse=True)))
    lines.append("")
    lines.append(f"CLUSTERING k={best_k} silhouettes={sil_scores} names={cluster_names}")
    for c in range(best_k):
        lines.append(f"  C{c} '{cluster_names[c]}' n={results['clustering']['sizes'][c]} mean_pop={results['clustering']['mean_popularity'][c]:.1f} median_pop={results['clustering']['median_popularity'][c]:.1f} genres={list(dom_genres[c].keys())}")
    lines.append("")
    lines.append("ARBITRAGE (test set, gap = predicted - actual):")
    lines.append("  UNDEREXPOSED top 5:")
    for r in results["arbitrage"]["underexposed_top15"][:5]:
        lines.append(f"    {r['artists']} — {r['track_name']} [{r['genre']}] actual={r['actual']:.0f} pred={r['predicted']:.1f} gap={r['gap']:+.1f}")
    lines.append("  OVEREXPOSED top 5:")
    for r in results["arbitrage"]["overexposed_top15"][:5]:
        lines.append(f"    {r['artists']} — {r['track_name']} [{r['genre']}] actual={r['actual']:.0f} pred={r['predicted']:.1f} gap={r['gap']:+.1f}")
    lines.append("")
    lines.append("FIGURES: " + ", ".join(sorted(p.name for p in FIGDIR.glob("*.png"))))
    txt = "\n".join(lines)
    (BASE / "findings.txt").write_text(txt)
    print(txt)
    print(f"\n[write] {BASE/'findings.txt'}")
    print("\nDone.")


if __name__ == "__main__":
    main()
