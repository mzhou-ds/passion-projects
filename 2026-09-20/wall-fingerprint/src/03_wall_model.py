"""03_wall_model.py — predict the bonk from early-race signals.

Target: BONK = avg pace over 30-42.195k >= 12% slower than avg pace 0-30k.
Features: only information available at the 25k mark (rel0..rel4, sex, year,
early-overpacing metrics). Train on Berlin 2016-2018, test on 2019 (temporal split).
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xgboost as xgb
import shap
from sklearn.metrics import roc_auc_score, average_precision_score

df = pd.read_pickle("output/berlin_archetypes.pkl")
REL = [f"rel{i}" for i in range(9)]

# exact cumulative pace for first 30k and last 12.195k from segment paces
SEG_KM = np.array([5, 5, 5, 5, 5, 5, 5, 5, 2.195])
SEG = [f"seg{i}" for i in range(9)]
segm = df[SEG].values
t30 = (segm[:, :6] * SEG_KM[:6]).sum(axis=1)
tlast = (segm[:, 6:] * SEG_KM[6:]).sum(axis=1)
df["pace_first30"] = t30 / 30.0
df["pace_last12"] = tlast / 12.195
df["decay"] = df["pace_last12"] / df["pace_first30"] - 1.0   # + = slowed down
df["bonk"] = (df["decay"] >= 0.12).astype(int)
print(f"bonk rate overall: {df['bonk'].mean():.3f}")
print("bonk rate by tier:")
print(df.groupby("tier", observed=True)["bonk"].mean().round(3).to_string())

# features known at 25k — ABSOLUTE paces only (relative-to-average features leak:
# the denominator includes the late segments we're predicting)
df["start_aggro"] = df["seg0"] / df[["seg1", "seg2", "seg3"]].mean(axis=1)  # <1 = hot start
df["mid_drift"] = df[["seg3", "seg4"]].mean(axis=1)   # 15-25k absolute pace
df["sexM"] = (df["gender"] == "M").astype(int)
FEATS = ["seg0", "seg1", "seg2", "seg3", "seg4", "start_aggro", "mid_drift", "sexM", "year"]

tr = df[df["year"] < 2019]
te = df[df["year"] == 2019]
Xtr, ytr = tr[FEATS].values, tr["bonk"].values
Xte, yte = te[FEATS].values, te["bonk"].values

model = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
                          random_state=7, n_jobs=4, eval_metric="logloss")
model.fit(Xtr, ytr)
p = model.predict_proba(Xte)[:, 1]
print(f"\ntest AUC={roc_auc_score(yte, p):.3f}  AP={average_precision_score(yte, p):.3f} "
      f"(base rate {yte.mean():.3f})")

# SHAP
explainer = shap.TreeExplainer(model)
sv = explainer.shap_values(Xte[:8000])
shap.summary_plot(sv, Xte[:8000], feature_names=FEATS, show=False, max_display=9)
plt.tight_layout()
plt.savefig("charts/02_shap_bonk.png", dpi=130, bbox_inches="tight")
plt.close()
imp = pd.Series(np.abs(sv).mean(axis=0), index=FEATS).sort_values(ascending=False)
print("\nmean |SHAP|:"); print(imp.round(4).to_string())

# ---- chart 3: the tax on optimism
# match runners by ability = pace over 10-20k (segments 2,3); compare hot vs even starters
df["ability"] = df[["seg2", "seg3"]].mean(axis=1)
df["hot"] = df["start_aggro"] < 0.95
out = []
for lo, hi in [(240, 300), (300, 330), (330, 360), (360, 390), (390, 420), (420, 480)]:
    sub = df[df["ability"].between(lo, hi)]
    if len(sub) < 2000:
        continue
    hot = sub[sub["hot"]]["time_full_s"].median()
    even = sub[~sub["hot"]]["time_full_s"].median()
    out.append({"ability_pace": (lo + hi) / 2, "n": len(sub),
                "hot_share": sub["hot"].mean(),
                "median_hot_min": hot / 60, "median_even_min": even / 60,
                "tax_min": (hot - even) / 60})
tax = pd.DataFrame(out)
print("\ntax on optimism (matched on 10-20k pace):")
print(tax.round(2).to_string(index=False))
tax.to_csv("output/tax_on_optimism.csv", index=False)

fig, ax = plt.subplots(figsize=(9, 5.5))
x = tax["ability_pace"]
ax.bar(x - 6, tax["median_even_min"], width=12, label="Even starters")
ax.bar(x + 6, tax["median_hot_min"], width=12, label="Hot starters (first 5k ≥5% faster than 10–20k pace)")
for i, r in tax.iterrows():
    ax.text(r["ability_pace"], r["median_hot_min"] + 4, f"+{r['tax_min']:.0f} min",
            ha="center", fontsize=9, color="darkred")
ax.set_xlabel("Ability (avg pace 10–20k, sec/km)")
ax.set_ylabel("Median finish time (min)")
ax.set_title("The tax on optimism: same ability, hotter start, slower finish")
ax.legend()
plt.tight_layout()
plt.savefig("charts/03_tax_on_optimism.png", dpi=130)
plt.close()

# risk by predicted decile for README
te2 = te.copy(); te2["p"] = p
te2["dec"] = pd.qcut(te2["p"], 10, labels=False)
cal = te2.groupby("dec").agg(rate=("bonk", "mean"), pmean=("p", "mean"))
print("\nbonk rate by predicted-risk decile:")
print(cal.round(3).to_string())

json.dump({"auc": round(float(roc_auc_score(yte, p)), 3),
           "ap": round(float(average_precision_score(yte, p)), 3),
           "base_rate": round(float(yte.mean()), 3),
           "top_shap": imp.head(4).round(4).to_dict()},
          open("output/wall_model_metrics.json", "w"), indent=1)
