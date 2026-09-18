"""Part 3: P(Stanley Cup Final | regular-season profile), 2008-2025 seasons.

Features from MoneyPuck teams.csv; labels = Cup winner + runner-up.
Model: XGBoost, leave-one-season-out CV for honest evaluation, SHAP for drivers.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score

RAW = "data/raw"

# season label (MoneyPuck start-year) -> (winner, runner_up), Cup decided that spring
FINALS = {
    2008: ("PIT", "DET"), 2009: ("CHI", "PHI"), 2010: ("BOS", "VAN"),
    2011: ("LAK", "NJD"), 2012: ("CHI", "BOS"), 2013: ("LAK", "NYR"),
    2014: ("CHI", "TBL"), 2015: ("PIT", "SJS"), 2016: ("PIT", "NSH"),
    2017: ("WSH", "VGK"), 2018: ("STL", "BOS"), 2019: ("TBL", "DAL"),
    2020: ("TBL", "MTL"), 2021: ("COL", "TBL"), 2022: ("VGK", "FLA"),
    2023: ("FLA", "EDM"), 2024: ("FLA", "EDM"), 2025: ("CAR", "VGK"),
}

ABBR = {"L.A": "LAK", "T.B": "TBL", "N.J": "NJD", "S.J": "SJS"}

def team_features(season):
    df = pd.read_csv(f"{RAW}/mp_{season}_teams.csv")
    df["name"] = df["name"].replace(ABBR)  # older seasons use dotted abbrs
    out = {}
    for sit in ["5on5", "5on4", "4on5", "all"]:
        sub = df[df["situation"] == sit].set_index("name")
        out[sit] = sub
    rows = []
    for team in out["5on5"].index:
        r = {"season": season, "team": team}
        f = out["5on5"].loc[team]
        hrs = f["iceTime"] / 3600.0
        r["xGF60"] = f["xGoalsFor"] / hrs
        r["xGA60"] = f["xGoalsAgainst"] / hrs
        r["xGshare"] = f["xGoalsPercentage"]
        r["corsi"] = f["corsiPercentage"]
        r["GSAA60"] = (f["xGoalsAgainst"] - f["goalsAgainst"]) / hrs  # goalie, + = good
        r["finish5v5"] = f["goalsFor"] / f["xGoalsFor"]
        p = out["5on4"].loc[team]; ph = p["iceTime"] / 3600.0
        r["PPxGF60"] = p["xGoalsFor"] / ph if ph > 0 else np.nan
        k = out["4on5"].loc[team]; kh = k["iceTime"] / 3600.0
        r["PKxGA60"] = k["xGoalsAgainst"] / kh if kh > 0 else np.nan
        a = out["all"].loc[team]; ah = a["iceTime"] / 3600.0
        r["GD60"] = (a["goalsFor"] - a["goalsAgainst"]) / ah
        rows.append(r)
    return pd.DataFrame(rows)

def main():
    df = pd.concat([team_features(s) for s in range(2008, 2026)], ignore_index=True)
    df["finalist"] = df.apply(
        lambda r: 1 if r["team"] in FINALS.get(r["season"], ()) else 0, axis=1)
    print(f"team-seasons={len(df)} finalists={df['finalist'].sum()}")
    feats = ["xGF60","xGA60","xGshare","corsi","GSAA60","finish5v5","PPxGF60","PKxGA60","GD60"]
    df = df.dropna(subset=feats)
    X = df[feats].values; y = df["finalist"].values

    # leave-one-season-out CV
    aucs, preds = [], np.zeros(len(df))
    for s in sorted(df["season"].unique()):
        tr = df["season"] != s; te = df["season"] == s
        m = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8,
                          scale_pos_weight=(y[tr]==0).sum()/(y[tr]==1).sum(),
                          random_state=7, n_jobs=4)
        m.fit(X[tr], y[tr])
        p = m.predict_proba(X[te])[:, 1]
        preds[te] = p
        aucs.append(roc_auc_score(y[te], p))
    aucs = np.array(aucs)
    print(f"LOSO AUC: mean={np.nanmean(aucs):.3f} min={np.nanmin(aucs):.3f} max={np.nanmax(aucs):.3f}")
    df["p_finalist_loo"] = preds

    # how did finalists rank by model each year?
    chk = df[df["finalist"]==1].copy()
    chk["rank_in_season"] = chk.groupby("season")["p_finalist_loo"]\
        .rank(ascending=False, method="min").astype(int)
    nteams = df.groupby("season")["team"].transform("count")
    print(chk[["season","team","p_finalist_loo","rank_in_season"]]
          .sort_values("season").to_string(index=False))
    print(f"\nmedian finalist rank by model: {chk['rank_in_season'].median():.0f} of ~32")

    # final model on all data
    model = XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8,
                          scale_pos_weight=(y==0).sum()/(y==1).sum(),
                          random_state=7, n_jobs=4)
    model.fit(X, y)
    import pickle
    pickle.dump({"model": model, "feats": feats}, open("data/processed/cup_model.pkl","wb"))
    df.to_csv("data/processed/cup_model_scored.csv", index=False)

    # SHAP (fallback: permutation importance)
    try:
        import shap
        ex = shap.TreeExplainer(model)
        sv = ex.shap_values(X)
        imp = pd.Series(np.abs(sv).mean(0), index=feats).sort_values(ascending=False)
        print("\nmean |SHAP|:"); print(imp.round(4).to_string())
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.summary_plot(sv, X, feature_names=feats, show=False, plot_size=(8,5))
        fig.tight_layout(); fig.savefig("figures/03_shap.png", dpi=130)
        print("saved figures/03_shap.png")
    except Exception as e:
        print("SHAP unavailable:", e)
        from sklearn.inspection import permutation_importance
        pi = permutation_importance(model, X, y, n_repeats=10, random_state=7)
        imp = pd.Series(pi.importances_mean, index=feats).sort_values(ascending=False)
        print(imp.round(4).to_string())
    imp.to_csv("data/processed/cup_feature_importance.csv")

    # calibration-ish: finalist rate by predicted decile
    df["dec"] = pd.qcut(df["p_finalist_loo"], 10, labels=False, duplicates="drop")
    cal = df.groupby("dec").agg(n=("finalist","size"), rate=("finalist","mean"),
                                p=("p_finalist_loo","mean"))
    print("\ncalibration by decile:"); print(cal.round(3).to_string())

if __name__ == "__main__":
    main()
