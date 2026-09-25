#!/usr/bin/env python3
"""
SWIPE ECONOMICS: the San Francisco dating market as a two-sided marketplace.

Analyzes ~60k OKCupid profiles (San Francisco 25-mile radius, June 2012) through a
marketplace lens: supply/demand imbalance, costly signaling (height, income
disclosure), liquidity by age cohort, and persona segmentation.

Data: Kim & Escobedo-Land (2015), Journal of Statistics Education;
      revised dataset via rudeboybert/JSE_OkCupid.

Reproducible end-to-end: reads data/profiles_revised.csv, writes charts/*.png
and findings.json. Run:  python3 analysis.py
Requires: pandas, numpy, matplotlib, scikit-learn, xgboost, shap.
Falls back to sklearn GradientBoostingClassifier + permutation importance if
xgboost/shap are unavailable (flagged in findings.json).
"""

import html
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SEED = 42
rng = np.random.default_rng(SEED)

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "data" / "profiles_revised.csv"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)
FINDINGS_PATH = BASE / "findings.json"

CAPTION = "Source: OKCupid profiles, SF 25mi, June 2012 (n≈60k)"
DPI = 150
MALE_C = "#2b7bb9"
FEM_C = "#e2547a"
NEUT_C = "#5a5a5a"
ACCENT_C = "#e8a13c"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update(
    {
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "font.family": "DejaVu Sans",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
    }
)

findings = {
    "citation": "Kim & Escobedo-Land (2015), Journal of Statistics Education; "
    "revised dataset via rudeboybert/JSE_OkCupid",
    "sample": "OKCupid profiles, San Francisco 25-mile radius, June 2012, "
    "active accounts with photos",
}


def jclean(o):
    """Make an object JSON-serializable."""
    if isinstance(o, dict):
        return {str(k): jclean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jclean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    return o


def caption(ax):
    ax.figure.text(
        0.01, 0.005, CAPTION, fontsize=7, color="#777777", ha="left", va="bottom"
    )


# ---------------------------------------------------------------- load & clean
df = pd.read_csv(DATA_PATH)
for c in df.select_dtypes(include="object").columns:
    df[c] = df[c].map(
        lambda x: html.unescape(str(x)).strip().replace("’", "'") if pd.notna(x) else x
    )
    df[c] = df[c].replace({"": np.nan, "nan": np.nan})

for c in ["age", "height", "income"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

n_total = len(df)
n_male = int((df["sex"] == "m").sum())
n_female = int((df["sex"] == "f").sum())

missingness = {c: round(float(df[c].isna().mean() * 100), 2) for c in df.columns}

age_min, age_max = float(df["age"].min()), float(df["age"].max())
n_age_outside_18_69 = int(((df["age"] < 18) | (df["age"] > 69)).sum())
age_med_m = float(df.loc[df["sex"] == "m", "age"].median())
age_med_f = float(df.loc[df["sex"] == "f", "age"].median())

orientation = df["orientation"].value_counts(normalize=True).mul(100).round(2)

findings["n_total"] = n_total
findings["n_male"] = n_male
findings["n_female"] = n_female
findings["pct_male"] = round(n_male / n_total * 100, 2)
findings["sex_ratio_m_per_100_f"] = round(n_male / n_female * 100, 1)
findings["missingness_pct"] = missingness
findings["age"] = {
    "min": age_min,
    "max": age_max,
    "n_outside_18_69": n_age_outside_18_69,
    "pct_outside_18_69": round(n_age_outside_18_69 / n_total * 100, 2),
    "median_male": age_med_m,
    "median_female": age_med_f,
}
findings["orientation_pct"] = orientation.to_dict()


def age_bucket(a):
    """5-year bucket label for an age."""
    if pd.isna(a):
        return np.nan
    a = int(a)
    if a < 20:
        return "18-19"
    if a >= 70:
        return "70+"
    lo = (a // 5) * 5
    return f"{lo}-{lo + 4}"


BUCKET_ORDER = ["18-19"] + [f"{lo}-{lo+4}" for lo in range(20, 70, 5)] + ["70+"]
df["bucket"] = df["age"].map(age_bucket)
df["bucket"] = pd.Categorical(df["bucket"], categories=BUCKET_ORDER, ordered=True)

# analysis population: adult market, drop joke ages for bucket charts
adult = df[(df["age"] >= 18) & (df["age"] <= 69)].copy()
findings["n_adult_18_69"] = len(adult)


# ------------------------------------------------------------- collapse maps
def edu_level(e):
    if pd.isna(e):
        return "missing"
    e = str(e).lower()
    if "ph.d" in e:
        return "PhD"
    if "law school" in e or "med school" in e or "business school" in e:
        return "Professional (JD/MD/MBA)"
    if "masters" in e:
        return "Master's"
    if "college/university" in e:
        return "College"
    if "two-year" in e:
        return "2-year college"
    if "high school" in e:
        return "HS or less"
    if "space camp" in e:
        return "Space camp (joke)"
    return "Other"


EDU_ORDER = [
    "HS or less",
    "2-year college",
    "College",
    "Master's",
    "Professional (JD/MD/MBA)",
    "PhD",
    "Space camp (joke)",
    "Other",
    "missing",
]
df["edu_level"] = df["education"].map(edu_level)
adult["edu_level"] = adult["education"].map(edu_level)

GRAD_COLLEGE = {
    "College",
    "Master's",
    "Professional (JD/MD/MBA)",
    "PhD",
}


def religion_main(r):
    if pd.isna(r):
        return "missing"
    r = str(r).lower()
    for k in ["atheism", "agnosticism", "catholicism", "christianity", "judaism",
              "buddhism", "hinduism", "islam", "mormonism", "scientology"]:
        if r.startswith(k):
            return k
    return "other"


df["religion_main"] = df["religion"].map(religion_main)


def diet_group(d):
    if pd.isna(d):
        return "missing"
    d = str(d).lower()
    if "vegan" in d:
        return "vegan"
    if "vegetarian" in d:
        return "vegetarian"
    if "kosher" in d:
        return "kosher"
    if "halal" in d:
        return "halal"
    if "anything" in d:
        return "anything"
    return "other"


df["diet_group"] = df["diet"].map(diet_group)


def offspring_group(o):
    if pd.isna(o):
        return "missing"
    o = str(o).lower()
    if "has kid" in o or "has a kid" in o:
        return "has kids"
    if o.strip() == "wants kids":  # has kids and wants more (shortened label)
        return "has kids"
    if "but wants them" in o:
        return "wants kids"
    if "might want" in o:
        return "might want kids"
    if "doesn't want" in o:
        return "doesn't want kids"
    if "doesn't have kids" in o:
        return "no kids, no stated preference"
    return "other"


df["offspring_group"] = df["offspring"].map(offspring_group)
adult["offspring_group"] = adult["offspring"].map(offspring_group)


def eth_flags(eth):
    s = str(eth).lower() if pd.notna(eth) else ""
    return {
        "eth_white": int("white" in s),
        "eth_asian": int("asian" in s),
        "eth_black": int("black" in s),
        "eth_hispanic": int("hispanic" in s or "latin" in s),
    }


eth_df = pd.DataFrame([eth_flags(e) for e in df["ethnicity"]], index=df.index)
df = pd.concat([df, eth_df], axis=1)
adult = pd.concat([adult, eth_df.loc[adult.index]], axis=1)

df["income_disclosed"] = (df["income"] != -1).astype(int)
adult["income_disclosed"] = (adult["income"] != -1).astype(int)

JOB_TOP = df["job"].value_counts().head(8).index.tolist()
df["job_top"] = df["job"].where(df["job"].isin(JOB_TOP), "other")
df.loc[df["job"].isna(), "job_top"] = "missing"
# adult was copied before these columns existed; sync them over
for _c in ["religion_main", "diet_group", "job_top"]:
    adult[_c] = df.loc[adult.index, _c]

# ------------------------------------------- a. population pyramid (18-69)
pyr = (
    adult.groupby(["bucket", "sex"], observed=True)
    .size()
    .unstack(fill_value=0)
    .reindex([b for b in BUCKET_ORDER if b != "70+"])
)
fig, ax = plt.subplots(figsize=(9, 7))
ys = np.arange(len(pyr))
ax.barh(ys, -pyr["m"], height=0.8, color=MALE_C, label="Men")
ax.barh(ys, pyr["f"], height=0.8, color=FEM_C, label="Women")
ax.set_yticks(ys)
ax.set_yticklabels(pyr.index)
ax.set_xlabel("Profiles")
ax.set_title("The SF dating pool skews young and male")
xt = ax.get_xticks()
ax.set_xticks(xt)
ax.set_xticklabels([f"{abs(int(x)):,}" for x in xt])
ax.legend(frameon=False)
ax.text(
    0.02,
    0.96,
    f"{n_male:,} men vs {n_female:,} women overall\n({findings['pct_male']:.1f}% male)",
    transform=ax.transAxes,
    fontsize=10,
    va="top",
    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc"),
)
caption(ax)
fig.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(CHARTS / "population_pyramid.png")
plt.close(fig)

# ------------------------------------------- b. sex ratio by age (straight)
straight = adult[adult["orientation"] == "straight"].copy()
sr = straight.groupby("bucket", observed=True)["sex"].agg(
    male_share=lambda s: (s == "m").mean() * 100, n="size"
)
sr = sr.reindex([b for b in BUCKET_ORDER if b != "70+"])
overall_straight_male_share = float((straight["sex"] == "m").mean() * 100)

fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(sr.index, sr["male_share"], marker="o", color=NEUT_C, lw=2.2, label="Male share of straight profiles")
ax.axhline(
    overall_straight_male_share,
    color=MALE_C,
    ls="--",
    lw=1.5,
    label=f"Overall straight pool: {overall_straight_male_share:.1f}% male",
)
ax.fill_between(sr.index, 50, sr["male_share"], alpha=0.12, color=MALE_C)
ax.set_ylim(40, 78)
ax.set_ylabel("Male share of straight profiles (%)")
ax.set_xlabel("Age bucket")
ax.set_title("Male skew peaks at 25-29 — then reverses: women outnumber men after 55")
ax.legend(frameon=False, loc="lower right")
for b in ["25-29", "60-64"]:
    ax.annotate(
        f"{sr.loc[b, 'male_share']:.1f}%",
        (b, sr.loc[b, "male_share"]),
        textcoords="offset points",
        xytext=(0, 12),
        ha="center",
        fontsize=9,
        weight="bold",
    )
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
caption(ax)
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(CHARTS / "sex_ratio_by_age.png")
plt.close(fig)

n_sm = int((straight["sex"] == "m").sum())
n_sf = int((straight["sex"] == "f").sum())
findings["straight"] = {
    "n": len(straight),
    "n_male": n_sm,
    "n_female": n_sf,
    "male_share_pct": round(overall_straight_male_share, 2),
    "m_per_100_f": round(n_sm / n_sf * 100, 1),
    "male_share_by_bucket": sr["male_share"].round(2).to_dict(),
    "n_by_bucket": sr["n"].astype(int).to_dict(),
}

# ------------------------------------------------------- c. height economics
h_m = adult.loc[adult["sex"] == "m", "height"].dropna()
h_f = adult.loc[adult["sex"] == "f", "height"].dropna()

fig, ax = plt.subplots(figsize=(9, 5.5))
bins = np.arange(56, 83, 1)
ax.hist(h_m, bins=bins, alpha=0.55, color=MALE_C, label="Men", density=True)
ax.hist(h_f, bins=bins, alpha=0.55, color=FEM_C, label="Women", density=True)
for h, lab, yy in [(70, "5'10\"", 0.205), (72, "6'0\"", 0.180)]:
    cnt = int((h_m == h).sum())
    ax.annotate(
        f"{lab}\n{cnt:,} men",
        xy=(h, 0.02),
        xytext=(h, yy),
        ha="center",
        fontsize=9,
        weight="bold",
        color=MALE_C,
        arrowprops=dict(arrowstyle="->", color=MALE_C, lw=1.2),
    )
ax.set_xlabel("Reported height (inches)")
ax.set_ylabel("Density")
ax.set_ylim(0, 0.235)
ax.set_title("Men's heights spike at 6'0\" and 5'10\" — digit preference is real")
ax.legend(frameon=False)
caption(ax)
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(CHARTS / "height_dist.png")
plt.close(fig)


def spike_stats(series, h):
    n_h = int((series == h).sum())
    n_lo = int((series == h - 1).sum())
    n_hi = int((series == h + 1).sum())
    expected = (n_lo + n_hi) / 2
    excess_pct = (n_h / expected - 1) * 100 if expected else None
    return {
        "n_at": n_h,
        "pct_at": round(n_h / len(series) * 100, 2),
        "n_neighbors": (n_lo, n_hi),
        "expected": round(expected, 1),
        "excess_pct_vs_neighbors": round(excess_pct, 1) if excess_pct is not None else None,
    }


height_findings = {
    "mean_m": round(float(h_m.mean()), 2),
    "mean_f": round(float(h_f.mean()), 2),
    "median_m": float(h_m.median()),
    "median_f": float(h_f.median()),
    "pct_men_ge_72": round(float((h_m >= 72).mean() * 100), 2),
    "pct_women_ge_66": round(float((h_f >= 66).mean() * 100), 2),
    "men_spike_72": spike_stats(h_m, 72),
    "men_spike_70": spike_stats(h_m, 70),
    "women_spike_66": spike_stats(h_f, 66),
    "women_spike_64": spike_stats(h_f, 64),
    "mean_height_men_20s": round(float(h_m[adult.loc[h_m.index, "age"].between(20, 29)].mean()), 2),
    "mean_height_men_50s": round(float(h_m[adult.loc[h_m.index, "age"].between(50, 59)].mean()), 2),
    "mean_height_women_20s": round(float(h_f[adult.loc[h_f.index, "age"].between(20, 29)].mean()), 2),
    "mean_height_women_50s": round(float(h_f[adult.loc[h_f.index, "age"].between(50, 59)].mean()), 2),
}
findings["height"] = height_findings

# ------------------------------------------------- d. income disclosure
discl = (
    adult.groupby(["edu_level", "sex"], observed=True)["income_disclosed"]
    .mean()
    .mul(100)
    .unstack()
    .reindex([e for e in EDU_ORDER if e != "missing"])
)
fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(discl))
w = 0.38
ax.bar(x - w / 2, discl["m"], width=w, color=MALE_C, label="Men")
ax.bar(x + w / 2, discl["f"], width=w, color=FEM_C, label="Women")
ax.set_xticks(x)
ax.set_xticklabels(discl.index, rotation=28, ha="right")
ax.set_ylabel("Share reporting income (%)")
ax.set_title("Income disclosure: men report more at every education level")
ax.legend(frameon=False)
med_m = float(adult.loc[(adult["sex"] == "m") & (adult["income"] != -1), "income"].median())
med_f = float(adult.loc[(adult["sex"] == "f") & (adult["income"] != -1), "income"].median())
ax.text(
    0.98,
    0.96,
    f"Median reported income — men \${med_m:,.0f} vs women \${med_f:,.0f}",
    transform=ax.transAxes,
    fontsize=10,
    ha="right",
    va="top",
    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc"),
)
caption(ax)
fig.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(CHARTS / "income_disclosure.png")
plt.close(fig)

rep = adult[adult["income"] != -1]
cred_premium = rep.groupby("edu_level", observed=True)["income"].median().round(0)
disc_by_sex = adult.groupby("sex", observed=True)["income_disclosed"].mean().mul(100).round(2)
disc_by_sex_edu = (
    adult.groupby(["edu_level", "sex"], observed=True)["income_disclosed"]
    .mean().mul(100).round(2).unstack()
)
findings["income"] = {
    "n_reported": int((adult["income"] != -1).sum()),
    "pct_disclosed_overall": round(float(adult["income_disclosed"].mean() * 100), 2),
    "pct_disclosed_m": float(disc_by_sex["m"]),
    "pct_disclosed_f": float(disc_by_sex["f"]),
    "median_income_m": med_m,
    "median_income_f": med_f,
    "income_max_reported": float(adult.loc[adult["income"] != -1, "income"].max()),
    "disclosure_by_sex_edu_pct": jclean(disc_by_sex_edu.to_dict()),
    "median_income_by_edu": jclean(cred_premium.to_dict()),
}

# -------------------------------------- e. income disclosure model + SHAP
MODEL_COLS_NUM = ["age", "height", "eth_white", "eth_asian", "eth_black", "eth_hispanic"]
MODEL_COLS_CAT = {
    "sex": 2,
    "orientation": 3,
    "body_type": 8,
    "diet_group": 7,
    "drinks": 6,
    "drugs": 3,
    "edu_level": 9,
    "offspring_group": 7,
    "pets": 8,
    "religion_main": 8,
    "smokes": 5,
    "status": 5,
    "job_top": 9,
}


def build_model_features(frame):
    X = frame[MODEL_COLS_NUM].copy()
    for c in ["age", "height"]:  # 3 heights are non-numeric in the raw CSV -> median impute
        X[c] = X[c].fillna(X[c].median())
    for col, topn in MODEL_COLS_CAT.items():
        vals = frame[col].fillna("missing")
        top = vals.value_counts().head(topn).index
        vals = vals.where(vals.isin(top), "other_cat")
        d = pd.get_dummies(vals, prefix=col, dtype=np.float32)
        X = pd.concat([X, d], axis=1)
    return X


mf = adult[adult["age"].between(18, 69)].copy()
X_all = build_model_features(mf)
y_all = mf["income_disclosed"].values

model_info = {"fallback": False}
try:
    import xgboost as xgb
    import shap

    HAVE_XGB, HAVE_SHAP = True, True
except Exception as e:  # noqa: BLE001
    HAVE_XGB, HAVE_SHAP = False, False
    model_info["import_error"] = str(e)[:200]

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

Xtr, Xte, ytr, yte = train_test_split(
    X_all, y_all, test_size=0.2, random_state=SEED, stratify=y_all
)

if HAVE_XGB:
    clf = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        n_jobs=-1,
        random_state=SEED,
        eval_metric="logloss",
    )
    clf.fit(Xtr, ytr)
    model_info["used"] = "xgboost"
else:
    from sklearn.ensemble import GradientBoostingClassifier

    clf = GradientBoostingClassifier(random_state=SEED)
    clf.fit(Xtr, ytr)
    model_info["used"] = "sklearn GradientBoostingClassifier (xgboost unavailable)"
    model_info["fallback"] = True

proba = clf.predict_proba(Xte)[:, 1]
auc = float(roc_auc_score(yte, proba))
model_info["auc"] = round(auc, 4)
model_info["n_train"] = len(Xtr)
model_info["n_test"] = len(Xte)
model_info["n_features"] = X_all.shape[1]

if HAVE_SHAP:
    samp = Xte.sample(min(3000, len(Xte)), random_state=SEED)
    explainer = shap.TreeExplainer(clf)
    sv = explainer.shap_values(samp)
    if isinstance(sv, list):
        sv = sv[1]
    sv = np.asarray(sv)
    mean_abs = np.abs(sv).mean(axis=0)
    order = np.argsort(mean_abs)[::-1]
    top5 = [(samp.columns[i], round(float(mean_abs[i]), 5)) for i in order[:5]]
    model_info["top5_shap_features"] = top5
    model_info["shap_sample_n"] = len(samp)

    fig, ax = plt.subplots(figsize=(9, 6))
    shap.summary_plot(sv, samp, show=False, max_display=15, plot_size=None)
    fig = plt.gcf()
    fig.set_size_inches(9, 6)
    ax = plt.gca()
    ax.set_title("What predicts income disclosure? (SHAP, XGBoost)")
    fig.text(0.01, 0.005, CAPTION + " — model AUC {:.3f}".format(auc),
             fontsize=7, color="#777777", ha="left", va="bottom")
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(CHARTS / "income_shap.png")
    plt.close(fig)
else:
    from sklearn.inspection import permutation_importance

    pi = permutation_importance(clf, Xte, yte, n_repeats=3, random_state=SEED, n_jobs=-1)
    order = np.argsort(pi.importances_mean)[::-1]
    top5 = [(Xte.columns[i], round(float(pi.importances_mean[i]), 5)) for i in order[:5]]
    model_info["top5_permutation_importance"] = top5
    model_info["fallback"] = True

    fig, ax = plt.subplots(figsize=(9, 5.5))
    idx = order[:15][::-1]
    ax.barh([Xte.columns[i] for i in idx], pi.importances_mean[idx], color=ACCENT_C)
    ax.set_title("What predicts income disclosure? (permutation importance)")
    ax.set_xlabel("Mean decrease in accuracy")
    caption(ax)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(CHARTS / "income_shap.png")
    plt.close(fig)

findings["income"]["model"] = jclean(model_info)

# ---------------------------------------------------------- f. personas
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

Xp = build_model_features(adult)
scaler = StandardScaler()
Xp[["age", "height"]] = scaler.fit_transform(Xp[["age", "height"]])

sil_sample = Xp.sample(min(8000, len(Xp)), random_state=SEED)
sil_scores = {}
for k in range(5, 10):
    km = KMeans(n_clusters=k, n_init=10, random_state=SEED)
    lab = km.fit_predict(sil_sample)
    sil_scores[k] = float(silhouette_score(sil_sample, lab))
best_k = max(sil_scores, key=sil_scores.get)

km = KMeans(n_clusters=best_k, n_init=10, random_state=SEED)
clusters = km.fit_predict(Xp)
adult["persona"] = clusters

global_rate = Xp.mean(axis=0)
sizes = pd.Series(clusters).value_counts().sort_index()

CAT_PREFIXES = sorted(list(MODEL_COLS_CAT.keys()) + ["sex", "income_disclosed"],
                      key=len, reverse=True)


def strip_col(col):
    """Remove the longest matching feature-column prefix from a dummy name."""
    for p in CAT_PREFIXES:
        if col.startswith(p + "_"):
            return col[len(p) + 1:]
    return col


def vague_trait(col):
    s = strip_col(col).lower()
    return s in ("missing", "other", "other_cat") or s.startswith("other ")


PRETTY_OVERRIDES = {
    "sex_m": "Men",
    "sex_f": "Women",
    "income_disclosed_1": "Income disclosers",
    "income_disclosed_0": "Income hiders",
}


def pretty_trait(col):
    if col in PRETTY_OVERRIDES:
        return PRETTY_OVERRIDES[col]
    name = strip_col(col)
    short = {
        "computer / hardware / software": "Tech workers",
        "artistic / musical / writer": "Creatives",
        "student": "Students",
        "education / academia": "Academics",
        "science / tech / engineering": "Engineers/scientists",
        "medicine / health": "Health workers",
        "sales / marketing / biz dev": "Sales/marketing",
        "executive / management": "Managers",
        "atheism": "Atheists",
        "agnosticism": "Agnostics",
        "catholicism": "Catholics",
        "christianity": "Christians",
        "judaism": "Jewish",
        "buddhism": "Buddhists",
        "hinduism": "Hindus",
        "islam": "Muslim",
        "socially": "Social drinkers",
        "not at all": "Non-drinkers",
        "often": "Frequent drinkers",
        "rarely": "Rare drinkers",
        "very often": "Heavy drinkers",
        "desperately": "Heavy drinkers",
        "never": "Drug-free",
        "sometimes": "Occasional users",
        "no": "Non-smokers",
        "yes": "Smokers",
        "when drinking": "Smoke-when-drinking",
        "trying to quit": "Quitting smoking",
        "single": "Singles",
        "seeing someone": "Seeing someone",
        "available": "Available",
        "married": "Married",
        "straight": "Straight",
        "gay": "Gay",
        "bisexual": "Bisexual",
        "average": "Average build",
        "fit": "Fit",
        "athletic": "Athletic",
        "thin": "Thin",
        "curvy": "Curvy",
        "a little extra": "A little extra",
        "skinny": "Skinny",
        "full figured": "Full-figured",
        "anything": "Eat anything",
        "vegetarian": "Vegetarians",
        "vegan": "Vegans",
        "kosher": "Kosher",
        "halal": "Halal",
        "wants kids": "Want kids",
        "might want kids": "Might want kids",
        "has kids": "Have kids",
        "doesn't want kids": "Don't want kids",
        "no kids, no stated preference": "No stated kid preference",
        "likes dogs and likes cats": "Dog+cat people",
        "likes dogs": "Dog people",
        "likes cats": "Cat people",
        "has dogs": "Dog owners",
        "has cats": "Cat owners",
        "dislikes dogs and dislikes cats": "Pet skeptics",
        "College": "College grads",
        "Master's": "Master's grads",
        "PhD": "PhDs",
        "Professional (JD/MD/MBA)": "JD/MD/MBA grads",
        "HS or less": "High-school educated",
        "2-year college": "2-year college",
        "Space camp (joke)": "Space camp",
        "eth_white": "White",
        "eth_asian": "Asian",
        "eth_black": "Black",
        "eth_hispanic": "Hispanic/Latin",
    }
    return short.get(name, name.replace("_", " ").title() if name else "?")


def trait_lift(ci):
    """Per-feature lift of cluster ci vs global, dummies + eth flags only."""
    mask = clusters == ci
    pool = [c for c in Xp.columns if c not in ("age", "height")]
    lift = (Xp.loc[mask, pool].mean(axis=0) - global_rate[pool])
    return lift.drop([c for c in lift.index if vague_trait(c)], errors="ignore")


def persona_label(ci):
    mask = clusters == ci
    lift = trait_lift(ci)
    male_share = float(Xp.loc[mask, "sex_m"].mean()) if "sex_m" in Xp else 0.5
    sex_qual = ("Male-heavy" if male_share >= 0.68
                else "Female-heavy" if male_share <= 0.32 else None)
    if sex_qual:
        lift = lift.drop(["sex_m", "sex_f"], errors="ignore")
    top = lift.sort_values(ascending=False)
    rates = Xp.loc[mask, top.index].mean(axis=0)
    quals = [t for t in top.index if rates[t] >= 0.12][:2]
    # if the strongest signals are all question-skipping, say so plainly
    pool = [c for c in Xp.columns if c not in ("age", "height")]
    raw = (Xp.loc[mask, pool].mean(axis=0) - global_rate[pool]).sort_values(ascending=False)
    raw_top = [c for c in raw.index if c not in ("sex_m", "sex_f")][:5]
    if sum("missing" in c for c in raw_top) >= 4:
        core = "low-effort profiles"
    elif not quals:
        core = "low-effort profiles"  # top lifts are all question-skipping
    else:
        core = " ".join(pretty_trait(t) for t in quals)
    mean_age = float(adult.loc[mask, "age"].mean())
    qual = []
    if sex_qual:
        qual.append(sex_qual)
    if mean_age <= 26:
        qual.append("young")
    elif mean_age >= 40:
        qual.append("older")
    label = "The " + " ".join(qual + [core]).strip()
    return label if label != "The" else f"Persona {ci}"

labels = {ci: persona_label(ci) for ci in range(best_k)}

# heatmap traits: union of top-4 lift traits per cluster
heat_traits = []
for ci in range(best_k):
    for c in trait_lift(ci).sort_values(ascending=False).head(4).index:
        if c not in heat_traits:
            heat_traits.append(c)
heat_traits = heat_traits[:16]
heat = pd.DataFrame(
    {
        labels[ci]: [
            (Xp.loc[clusters == ci, t].mean() - global_rate[t]) * 100 for t in heat_traits
        ]
        for ci in range(best_k)
    },
    index=[pretty_trait(t) for t in heat_traits],
)

fig = plt.figure(figsize=(12, 8))
gs = fig.add_gridspec(2, 1, height_ratios=[1, 2.2], hspace=0.35)
ax1 = fig.add_subplot(gs[0])
order_idx = sizes.sort_values(ascending=True).index
ax1.barh(
    [labels[i] for i in order_idx],
    [sizes[i] for i in order_idx],
    color=ACCENT_C,
)
ax1.set_xlabel("Profiles")
ax1.set_title(f"Market personas: {best_k} segments (k-means, silhouette={sil_scores[best_k]:.3f})")
for i, ci in enumerate(order_idx):
    ax1.text(sizes[ci] + 150, i, f"{sizes[ci]:,} ({sizes[ci]/len(adult)*100:.1f}%)",
             va="center", fontsize=9)

ax2 = fig.add_subplot(gs[1])
im = ax2.imshow(heat.values, aspect="auto", cmap="RdBu_r",
               vmin=-np.abs(heat.values).max(), vmax=np.abs(heat.values).max())
ax2.set_xticks(range(len(heat.columns)))
ax2.set_xticklabels(heat.columns, rotation=20, ha="right", fontsize=7.5)
ax2.set_yticks(range(len(heat.index)))
ax2.set_yticklabels(heat.index, fontsize=8)
ax2.set_title("Defining traits: share in persona minus global share (pp)")
for r in range(len(heat.index)):
    for c_ in range(len(heat.columns)):
        ax2.text(c_, r, f"{heat.values[r, c_]:+.0f}", ha="center", va="center",
                 fontsize=7, color="white" if abs(heat.values[r, c_]) > 12 else "black")
fig.colorbar(im, ax=ax2, label="pp vs global")
fig.text(0.01, 0.005, CAPTION, fontsize=7, color="#777777", ha="left", va="bottom")
fig.subplots_adjust(left=0.30, right=0.92, bottom=0.24, top=0.90, hspace=0.55)
fig.savefig(CHARTS / "personas.png")
plt.close(fig)

persona_rows = []
for ci in range(best_k):
    mask = clusters == ci
    top = trait_lift(ci).sort_values(ascending=False).head(3).index.tolist()
    persona_rows.append(
        {
            "label": labels[ci],
            "size": int(sizes[ci]),
            "pct": round(float(sizes[ci] / len(adult) * 100), 2),
            "mean_age": round(float(adult.loc[mask, "age"].mean()), 1),
            "male_share_pct": round(float(Xp.loc[mask, "sex_m"].mean() * 100), 1)
            if "sex_m" in Xp else None,
            "top_traits": [pretty_trait(t) for t in top],
        }
    )
persona_rows.sort(key=lambda r: r["size"], reverse=True)
findings["personas"] = {
    "k": best_k,
    "silhouette": round(sil_scores[best_k], 4),
    "silhouette_by_k": {str(k): round(v, 4) for k, v in sil_scores.items()},
    "segments": persona_rows,
}

# ------------------------------------------- g. offspring / baby deadline
resp = adult[adult["offspring_group"] != "missing"].copy()
resp["wants_or_might"] = resp["offspring_group"].isin(["wants kids", "might want kids"]).astype(int)
ob = (
    resp.groupby(["bucket", "sex"], observed=True)["wants_or_might"]
    .mean().mul(100).unstack()
    .reindex([b for b in BUCKET_ORDER if b != "70+"])
)
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(ob.index, ob["m"], marker="o", color=MALE_C, lw=2.2, label="Men")
ax.plot(ob.index, ob["f"], marker="o", color=FEM_C, lw=2.2, label="Women")
ax.fill_between(ob.index, ob["m"], ob["f"], alpha=0.12, color=FEM_C)
ax.set_ylabel("Share wanting / open to kids (%)")
ax.set_xlabel("Age bucket")
ax.set_title("The baby-deadline divergence: women's kid-interest falls off a cliff after 35")
ax.legend(frameon=False)
gap_30 = ob.loc["30-34", "f"] - ob.loc["30-34", "m"]
gap_40 = ob.loc["40-44", "f"] - ob.loc["40-44", "m"]
ax.annotate(f"gap at 30-34: {gap_30:+.1f}pp (women higher)",
            xy=("30-34", ob.loc["30-34", "f"]), xytext=(45, -28),
            textcoords="offset points", fontsize=9,
            arrowprops=dict(arrowstyle="->", lw=1))
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
caption(ax)
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(CHARTS / "offspring_deadline.png")
plt.close(fig)

findings["offspring"] = {
    "response_rate_pct": round(float((adult["offspring_group"] != "missing").mean() * 100), 2),
    "pct_want_or_might_by_sex_bucket": jclean(ob.round(2).to_dict()),
    "category_shares_by_sex_pct": jclean(
        adult[adult["offspring_group"] != "missing"]
        .groupby("sex", observed=True)["offspring_group"]
        .value_counts(normalize=True).mul(100).round(2).unstack().to_dict()
    ),
}

# ------------------------------------------- h. market tightness (liquidity)
tb = straight.groupby(["bucket", "sex"], observed=True).size().unstack(fill_value=0)
tb = tb.reindex([b for b in BUCKET_ORDER if b != "70+"])
liq_men = (tb["f"] / tb["m"] * 100)    # women per 100 men: liquidity for straight men
liq_women = (tb["m"] / tb["f"] * 100)  # men per 100 women: liquidity for straight women

fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(liq_men.index, liq_men, marker="o", color=MALE_C, lw=2.2,
        label="Straight men: women per 100 men")
ax.plot(liq_women.index, liq_women, marker="o", color=FEM_C, lw=2.2,
        label="Straight women: men per 100 women")
ax.axhline(100, color=NEUT_C, ls="--", lw=1.2, label="Parity")
ax.set_ylabel("Opposite-sex profiles per 100 same-sex profiles")
ax.set_xlabel("Age bucket")
ax.set_title("Dating liquidity flips with age: brutal for young men, favorable after 55")
ax.legend(frameon=False, loc="upper right")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
caption(ax)
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(CHARTS / "market_tightness.png")
plt.close(fig)

findings["market_tightness"] = {
    "note": "straight profiles only; liquidity for a seeker = opposite-sex "
            "profiles per 100 same-sex profiles in the same 5-year bucket",
    "women_per_100_men_by_bucket": liq_men.round(1).to_dict(),
    "men_per_100_women_by_bucket": liq_women.round(1).to_dict(),
}

# ------------------------------------------------------------------ education
edu_shares = adult.groupby("sex", observed=True)["edu_level"].value_counts(
    normalize=True).mul(100).round(2).unstack(fill_value=0)
grad_m = float(edu_shares.loc["m", list(GRAD_COLLEGE)].sum())
grad_f = float(edu_shares.loc["f", list(GRAD_COLLEGE)].sum())
findings["education"] = {
    "pct_graduated_college_plus_m": round(grad_m, 2),
    "pct_graduated_college_plus_f": round(grad_f, 2),
    "shares_by_sex_pct": jclean(edu_shares.to_dict()),
}

# ------------------------------------------------------------------ lifestyle
def _share_by_sex(col):
    return jclean(
        adult.groupby("sex", observed=True)[col].value_counts(normalize=True)
        .mul(100).round(2).unstack(fill_value=0).to_dict()
    )


findings["lifestyle"] = {
    "drinks_by_sex_pct": _share_by_sex("drinks"),
    "smokes_by_sex_pct": _share_by_sex("smokes"),
    "drugs_by_sex_pct": _share_by_sex("drugs"),
    "diet_by_sex_pct": _share_by_sex("diet_group"),
}

# ------------------------------------------------------------------ caveats
findings["caveats"] = [
    "Sample is San Francisco 25-mile radius, June 2012, active accounts with photo; "
    "not representative of today's dating market or other cities.",
    "Self-reported data: height/income show digit preference and likely inflation.",
    f"Ages outside 18-69 (n={n_age_outside_18_69}, incl. max {age_max:.0f}) treated as "
    "joke/missing and excluded from bucket analyses.",
    f"Income reported by only {findings['income']['pct_disclosed_overall']:.1f}% of profiles; "
    "reported incomes skew toward disclosure-prone (likely higher-earning) users.",
    f"Offspring question answered by only {findings['offspring']['response_rate_pct']:.1f}% of profiles.",
    "All claims are correlational; personas are descriptive segments, not causal types.",
]

with open(FINDINGS_PATH, "w") as f:
    json.dump(jclean(findings), f, indent=2)

print("done.")
print("n =", n_total, "| male% =", findings["pct_male"])
print("auc =", findings["income"]["model"].get("auc"))
print("personas k =", findings["personas"]["k"])
