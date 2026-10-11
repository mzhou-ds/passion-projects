"""Two ML pieces:
1) TF-IDF + KMeans clustering of trial conditions/titles.
2) XGBoost + SHAP predicting whether a trial is an expansion indication.
"""
import pandas as pd, numpy as np, json, pathlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT/"data/trials_categorised.csv")
# --- clustering ---
text = df["conditions"].fillna("").str.replace("|"," ", regex=False)
STOP = list(TfidfVectorizer(stop_words="english").get_stop_words()) + ["diabetes","type","mellitus","patients","patient","study","disease","syndrome","glp","receptor","agonists","agonist","semaglutide","tirzepatide","liraglutide","dulaglutide","exenatide","disorder","disorders","chronic","treatment","using","subjects","participants","people","research","clinical","adult","adults","obese"]
vec = TfidfVectorizer(max_features=800, stop_words=STOP, ngram_range=(1,2), min_df=3)
X = vec.fit_transform(text)
km = KMeans(n_clusters=6, n_init=10, random_state=42)
df["cluster"] = km.fit_predict(X)
terms = vec.get_feature_names_out()
clusters={}
for c in range(6):
    top = km.cluster_centers_[c].argsort()[-8:][::-1]
    clusters[str(c)] = {"top_terms":[terms[i] for i in top], "n": int((df["cluster"]==c).sum()),
                        "expansion_share": float(df.loc[df["cluster"]==c,"is_expansion"].mean()),
                        "top_category": str(df.loc[df["cluster"]==c,"category"].mode().iloc[0])}
df.to_csv(ROOT/"data/trials_clustered.csv", index=False)
# --- XGBoost expansion classifier ---
d = df.dropna(subset=["start_year"]).copy()
d["log_enroll"] = np.log1p(pd.to_numeric(d["enrollment"], errors="coerce").fillna(0))
d["n_conditions"] = d["conditions"].fillna("").str.count(r"\|")+1
d["phase_max"] = d["phases"].fillna("").apply(lambda s: max([{"PHASE1":1,"PHASE2":2,"PHASE3":3,"PHASE4":4}.get(p,0) for p in str(s).split("|")] or [0]))
d["is_industry"] = (d["sponsor_class"]=="INDUSTRY").astype(int)
d["is_nih"] = (d["sponsor_class"]=="NIH").astype(int)
d["primary_molecule"] = d["molecules"].str.split("|").str[0]
mol_d = pd.get_dummies(d["primary_molecule"], prefix="mol")
feats = pd.concat([d[["start_year","log_enroll","n_conditions","n_primary_outcomes","phase_max","is_industry","is_nih"]].reset_index(drop=True), mol_d.reset_index(drop=True)], axis=1)
y = d["is_expansion"].values
Xtr, Xte, ytr, yte = train_test_split(feats, y, test_size=0.25, random_state=42, stratify=y)
from xgboost import XGBClassifier
xgb = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.06, subsample=0.9, colsample_bytree=0.9, eval_metric="logloss", random_state=42)
xgb.fit(Xtr, ytr)
auc_xgb = roc_auc_score(yte, xgb.predict_proba(Xte)[:,1])
lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
lr.fit(Xtr, ytr); auc_lr = roc_auc_score(yte, lr.predict_proba(Xte)[:,1])
import shap
expl = shap.TreeExplainer(xgb)
sv = expl.shap_values(Xte)
mean_abs = np.abs(sv).mean(axis=0)
importance = sorted(zip(feats.columns, mean_abs), key=lambda x:-x[1])
plt.figure(figsize=(8,5))
names=[i[0] for i in importance][::-1]; vals=[i[1] for i in importance][::-1]
plt.barh(names, vals, color="#7c3aed"); plt.xlabel("mean |SHAP|"); plt.title("What makes a GLP-1 trial an expansion bet? (XGBoost + SHAP)")
plt.tight_layout(); plt.savefig(ROOT/"charts/shap_expansion.png", dpi=160); plt.close()
out={"auc_xgboost": float(auc_xgb), "auc_logistic": float(auc_lr), "n_model": int(len(d)), "expansion_rate": float(y.mean()), "clusters": clusters, "shap_importance": [(str(a), float(b)) for a,b in importance]}
(ROOT/"data/model.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
