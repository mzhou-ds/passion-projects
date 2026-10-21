"""What predicts a model's last-30-day downloads? XGBoost regression on
log1p(downloads) over the union sample, with SHAP importances, against
two baselines: (a) likes alone in a linear model, (b) the full linear
model. The point is structural: does coming from a big family tree, and
which tree, move downloads once human attention (likes) is accounted for?
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

HERE = Path(__file__).resolve().parent.parent
df = pd.read_csv(HERE / "data" / "models_genealogy.csv", low_memory=False)
# Demand universe only: on the union sample, age mechanically separates
# the newest-cohort firehose from everything else and the model just
# learns sample membership. Among models people actually pull, the
# question is what separates 10K downloads a month from 10M.
df = df[df["samples"].str.contains("downloads")].copy()
OUT = HERE / "data" / "model.json"
CHART = HERE / "charts" / "shap_downloads.png"

df["created"] = pd.to_datetime(df["createdAt"], errors="coerce", utc=True)
now = df["created"].max()
df["age_days"] = (now - df["created"]).dt.days.clip(lower=0)
df["log_likes"] = np.log1p(df["likes"])
df["log_params"] = np.log10(df["params"].fillna(0) + 1)
df["has_params"] = df["params"].notna().astype(int)
df["root_downloads"] = df.groupby("root")["downloads"].transform("sum")
own = df.set_index("id")["downloads"]
df["parent_downloads"] = df["parent"].map(own).fillna(0)
df["log_parent_downloads"] = np.log1p(df["parent_downloads"])
df["family_size"] = df.groupby("family")["id"].transform("count")
df["log_family_size"] = np.log1p(df["family_size"])

top_tasks = df["pipeline_tag"].value_counts().head(8).index
for t in top_tasks:
    df[f"task_{t}"] = (df["pipeline_tag"] == t).astype(int)

FEATURES = [
    "log_likes", "age_days", "is_derivative", "depth", "log_parent_downloads",
    "log_family_size", "log_params", "has_params", "gated",
] + [f"task_{t}" for t in top_tasks]
df["is_derivative"] = df["is_derivative"].astype(int)
df["gated"] = df["gated"].astype(str).isin(["True", "true", "1"]).astype(int)

X = df[FEATURES].fillna(0)
y = np.log1p(df["downloads"])
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=7)

res = {}
lin1 = LinearRegression().fit(Xtr[["log_likes"]], ytr)
res["r2_likes_only_linear"] = float(r2_score(yte, lin1.predict(Xte[["log_likes"]])))
lin = LinearRegression().fit(Xtr, ytr)
res["r2_full_linear"] = float(r2_score(yte, lin.predict(Xte)))

model = XGBRegressor(
    n_estimators=500, max_depth=5, learning_rate=0.05,
    subsample=0.85, colsample_bytree=0.85, random_state=7, n_jobs=4,
)
model.fit(Xtr, ytr)
res["r2_xgboost"] = float(r2_score(yte, model.predict(Xte)))
res["n"] = int(len(df))
res["features"] = FEATURES

explainer = shap.TreeExplainer(model)
sv = explainer.shap_values(Xte)
mean_abs = np.abs(sv).mean(axis=0)
res["shap_mean_abs"] = {
    f: float(v) for f, v in sorted(zip(FEATURES, mean_abs), key=lambda kv: -kv[1])
}

plt.figure(figsize=(8, 5.5))
shap.summary_plot(sv, Xte, show=False, max_display=14)
plt.tight_layout()
plt.savefig(CHART, dpi=150, bbox_inches="tight")
print(json.dumps(res, indent=2))
with open(OUT, "w") as fh:
    json.dump(res, fh, indent=2)
print(f"wrote {OUT} and {CHART}")
