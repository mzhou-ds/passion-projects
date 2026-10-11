"""Categorise trials into indication buckets; compute expansion stats."""
import pandas as pd, numpy as np, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT/"data/trials.csv")
df["start_date_norm"] = df["start_date"].astype(str).str.replace(r"^(\d{4}-\d{2})$", r"\1-01", regex=True)
df["start_year"] = pd.to_datetime(df["start_date_norm"], errors="coerce").dt.year
RULES = [
 ("addiction", r"addict|alcohol|smoking|nicotine|cocaine|opioid|substance abuse|cannabis"),
 ("neuro", r"alzheimer|parkinson|dementia|cognitive|neurodegener|multiple sclerosis"),
 ("sleep_apnea", r"sleep apnea|sleep apnoea|obstructive sleep"),
 ("kidney", r"kidney|renal|nephropath|chronic kidney|ckd|albuminuria"),
 ("cardiovascular", r"cardiovascular|heart failure|myocardial|stroke|atheroscler|coronary|atrial fibrillation|hypertension"),
 ("liver_mash", r"steatohepatitis|mash|nash|hepatic|liver|fibrosis"),
 ("musculoskeletal", r"osteoarthritis|arthritis|knee pain|musculoskeletal|back pain"),
 ("longevity_aging", r"\baging\b|ageing|longevity|frailty|sarcopenia"),
 ("diabetes", r"diabetes|diabetic|glycemic|glycaemic|hba1c|hyperglyc"),
 ("obesity_weight", r"obes|overweight|weight|bariatric"),
]
def categorise(txt):
    t = str(txt).lower().replace("nonalcoholic","").replace("non-alcoholic","").replace("non alcoholic","")
    for label, pat in RULES:
        if re.search(pat, t): return label
    return "other"
df["category"] = df["conditions"].fillna("") .apply(categorise)
# if condition empty, fall back to title
mask = df["category"]=="other"
df.loc[mask, "category"] = df.loc[mask, "title"].fillna("").apply(categorise)
EXPANSION = {"cardiovascular","kidney","neuro","addiction","sleep_apnea","liver_mash","musculoskeletal","longevity_aging"}
df["is_expansion"] = df["category"].isin(EXPANSION).astype(int)
df["is_core"] = df["category"].isin({"diabetes","obesity_weight"}).astype(int)
df["era"] = pd.cut(df["start_year"], bins=[0,2017,2021,2030], labels=["pre-2018","2018-2021","2022+"])
df.to_csv(ROOT/"data/trials_categorised.csv", index=False)
summary = {}
summary["n_trials"] = int(len(df))
summary["by_molecule_primary"] = df["molecules"].str.split("|").str[0].value_counts().to_dict()
summary["by_category"] = df["category"].value_counts().to_dict()
summary["expansion_share_overall"] = float(df["is_expansion"].mean())
summary["expansion_share_by_era"] = {str(k): float(v) for k,v in df.groupby("era", observed=True)["is_expansion"].mean().items()}
summary["counts_by_era_category"] = df.groupby(["era","category"], observed=True).size().unstack(fill_value=0).to_dict()
summary["by_year"] = {str(int(k)): int(v) for k,v in df.dropna(subset=["start_year"]).groupby("start_year").size().items()}
summary["by_year_molecule"] = df.dropna(subset=["start_year"]).assign(primary=df["molecules"].str.split("|").str[0]).groupby(["start_year","primary"]).size().unstack(fill_value=0).astype(int).to_dict()
summary["sponsor_by_expansion"] = {str(k): {str(kk): int(vv) for kk,vv in v.items()} for k,v in df.groupby(["is_expansion","sponsor_class"]).size().unstack(fill_value=0).to_dict().items()}
summary["phase_by_expansion"] = {f"{k[0]}|{k[1]}": int(v) for k,v in df.groupby(["is_expansion","phases"]).size().items()}
summary["median_enrollment_by_category"] = {str(k): float(v) for k,v in df.groupby("category")["enrollment"].median().items()}
summary["has_results_by_category"] = {str(k): float(v) for k,v in df.groupby("category")["has_results"].mean().items()}
summary["status_counts"] = df["status"].value_counts().head(10).to_dict()
(ROOT/"data/summary.json").write_text(json.dumps(summary, indent=2, default=str))
print(json.dumps(summary, indent=2, default=str)[:6000])
