"""Classify 8,371 live Greenhouse postings and measure the shape of the Nov 2026
tech hiring market: function mix, AI share, remote share, manager-seat scarcity,
posting staleness (ghost jobs), seniority, and hiring metros."""
import json, re, os, math
from collections import Counter, defaultdict
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = "/tmp/gh_raw.jsonl"  # written by fetch_greenhouse.py; not committed
OUT = os.path.join(BASE, "data", "jobs_classified.csv")
CH = os.path.join(BASE, "charts")
os.makedirs(CH, exist_ok=True)
SNAPSHOT = pd.Timestamp("2026-11-18", tz="UTC")

# ---------------- classifiers ----------------
DATA_PAT = re.compile(r"data scien|data analy|machine learning|\bml\b|ai engineer|applied ai|ai architect|artificial intelligence|research scientist|applied scientist|analytics|data engineer|business intelligence|decision scien|data platform|ai research|mlops|modeling|statistic", re.I)
ENG_PAT = re.compile(r"software engineer|\bengineer\b|engineering|developer|devops|\bsre\b|site reliability|infrastructure|frontend|front-end|backend|back-end|full.?stack|mobile|\bios\b|android|security|qa engineer|test engineer|systems engineer|network engineer|hardware|solutions architect|solutions engineer|firmware|embedded", re.I)
PROD_PAT = re.compile(r"product manager|product ops|product operations", re.I)
DESIGN_PAT = re.compile(r"designer|product design|\bux\b|\bui\b|brand design|visual design|motion design", re.I)
SALES_PAT = re.compile(r"account executive|sales|business development|partnerships|partner manager|revenue|bdr|sdr|sales development|account manager", re.I)
MKTG_PAT = re.compile(r"marketing|growth|content|communications|seo|demand gen|brand marketing|product marketing", re.I)
PEOPLE_PAT = re.compile(r"recruit|talent|people|human resources|\bhr\b|people ops", re.I)
FIN_PAT = re.compile(r"finance|accounting|legal|counsel|treasury|tax |audit|investor relations", re.I)
OPS_PAT = re.compile(r"operations|program manager|project manager|chief of staff|strategy|business operations", re.I)
SUPPORT_PAT = re.compile(r"support|customer success|customer experience|trust and safety|moderation", re.I)

def classify_function(title, depts):
    t = title or ""
    d = " ".join(depts or [])
    s = f"{t} {d}"
    if DATA_PAT.search(s): return "Data / AI"
    if PROD_PAT.search(s): return "Product"
    if ENG_PAT.search(s): return "Engineering"
    if DESIGN_PAT.search(s): return "Design"
    if SALES_PAT.search(s): return "Sales / BD"
    if MKTG_PAT.search(s): return "Marketing / Growth"
    if PEOPLE_PAT.search(s): return "People / Talent"
    if FIN_PAT.search(s): return "Finance / Legal"
    if SUPPORT_PAT.search(s): return "Support / Trust"
    if OPS_PAT.search(s): return "Operations"
    return "Other"

MGR_STRONG = re.compile(r"\bdirector\b|vice president|\bvp\b|head of|group manager|general manager", re.I)
IC_EXCLUDE = re.compile(r"product manager|program manager|project manager|account manager|partner manager|customer success manager|campaign manager|community manager|content manager|product marketing manager|marketing manager|growth marketing|growth manager|lifecycle|paid social|seo manager|social media manager|events manager|communications manager|brand manager|technical program|engagement manager|solutions manager|delivery manager|success manager|support manager|sales operations manager|revenue operations manager|marketing operations manager", re.I)
LEAD_PAT = re.compile(r"\blead\b", re.I)

def classify_manager(title):
    t = (title or "").lower()
    if MGR_STRONG.search(t):
        return True
    if re.search(r"\bmanager\b", t) and not IC_EXCLUDE.search(t):
        return True
    return False

AI_TITLE = re.compile(r"machine learning|artificial intelligence|\bllm\b|generative|deep learning|\bnlp\b|computer vision|\bml\b|applied ai|ai agent|ai research|ai engineer|genai|foundation model|model training", re.I)
AI_DEPT = re.compile(r"machine learning|artificial intelligence|\bai\b|research", re.I)
AI_DESC = re.compile(r"large language model|\bllm\b|generative ai|machine learning|deep learning|fine-tun|foundation model|retrieval-augmented|reinforcement learning|computer vision|\bnlp\b|model training|prompt engineer", re.I)
def classify_ai_strict(title, depts):
    if AI_TITLE.search(title or ""): return True
    return any(AI_DEPT.search(d or "") for d in (depts or []))
def classify_ai_broad(title, desc, depts):
    return classify_ai_strict(title, depts) or bool(AI_DESC.search(desc or ""))

def classify_remote(loc, desc):
    l = (loc or "").lower()
    if "remote" in l: return "Remote"
    if "hybrid" in l: return "Hybrid"
    d = (desc or "").lower()
    if "this role is remote" in d or "this position is remote" in d or "remote-first" in d:
        return "Remote"
    return "On-site"

SEN_PAT = [("Intern", re.compile(r"intern", re.I)), ("New grad", re.compile(r"new grad|early career|university grad", re.I)),
           ("Junior", re.compile(r"\bjunior\b|associate", re.I)), ("Senior", re.compile(r"\bsenior\b", re.I)),
           ("Staff", re.compile(r"\bstaff\b", re.I)), ("Principal+", re.compile(r"principal|distinguished|fellow", re.I))]
def classify_seniority(title):
    t = title or ""
    for name, pat in SEN_PAT:
        if pat.search(t): return name
    return "Mid / unmarked"

METROS = {
    "San Francisco": ["san francisco", "sf,", " san francisco"], "New York": ["new york", "nyc"],
    "Seattle": ["seattle"], "Austin": ["austin"], "Boston": ["boston"], "Chicago": ["chicago"],
    "Los Angeles": ["los angeles"], "San Jose": ["san jose"], "Denver": ["denver"],
    "Atlanta": ["atlanta"], "Washington DC": ["washington, d.c", "washington dc", "washington, dc"],
    "London": ["london"], "Toronto": ["toronto"], "Dublin": ["dublin"], "Amsterdam": ["amsterdam"],
    "Berlin": ["berlin"], "Singapore": ["singapore"], "Bangalore": ["bangalore", "bengaluru"],
    "Sydney": ["sydney"], "Tokyo": ["tokyo"], "Paris": ["paris"], "Portland": ["portland"],
    "San Diego": ["san diego"], "Miami": ["miami"], "Vancouver": ["vancouver"],
}
def extract_metros(loc):
    l = (" " + (loc or "").lower() + " ")
    found = []
    for metro, keys in METROS.items():
        if any(k in l for k in keys):
            found.append(metro)
    return found

# ---------------- load & classify ----------------
rows = [json.loads(l) for l in open(RAW)]
df = pd.DataFrame(rows)
df["function"] = [classify_function(t, d) for t, d in zip(df.title, df.departments)]
df["is_manager"] = [classify_manager(t) for t in df.title]
df["is_lead"] = [bool(LEAD_PAT.search(t or "")) and not m for t, m in zip(df.title, df.is_manager)]
df["is_ai"] = [classify_ai_strict(t, depts) for t, depts in zip(df.title, df.departments)]
df["is_ai_broad"] = [classify_ai_broad(t, d, depts) for t, d, depts in zip(df.title, df.description, df.departments)]
df["remote_class"] = [classify_remote(l, d) for l, d in zip(df.location, df.description)]
df["seniority"] = [classify_seniority(t) for t in df.title]
pub = pd.to_datetime(df["first_published"], errors="coerce", utc=True)
upd = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
df["age_days"] = (SNAPSHOT - pub.fillna(upd)).dt.days.clip(lower=0)
df["is_ghost"] = df["age_days"] > 90
df["metros"] = [extract_metros(l) for l in df.location]
# descriptions are dropped from the committed file (36MB of text); the
# classification flags derived from them are kept. Full text lives in /tmp/gh_raw.
df.drop(columns=["description"]).to_csv(OUT, index=False)
print(f"classified {len(df)} postings, {df.company.nunique()} companies")

# ---------------- summary ----------------
S = {}
S["n_postings"] = len(df)
S["n_companies"] = int(df.company.nunique())
S["function_share"] = (df.function.value_counts(normalize=True) * 100).round(1).to_dict()
S["ai_share"] = round(df.is_ai.mean() * 100, 1)
S["ai_share_title_only"] = round(df.title.str.contains(AI_TITLE, regex=True).mean() * 100, 1)
S["ai_share_broad"] = round(df.is_ai_broad.mean() * 100, 1)
S["manager_share"] = round(df.is_manager.mean() * 100, 1)
S["lead_share"] = round(df.is_lead.mean() * 100, 1)
S["remote_share"] = (df.remote_class.value_counts(normalize=True) * 100).round(1).to_dict()
S["ghost_share"] = round(df.is_ghost.mean() * 100, 1)
S["median_age_days"] = float(df.age_days.median())
S["seniority_share"] = (df.seniority.value_counts(normalize=True) * 100).round(1).to_dict()
# DS slice
ds = df[df.function == "Data / AI"]
S["ds_n"] = len(ds)
S["ds_manager_share"] = round(ds.is_manager.mean() * 100, 1)
S["ds_ai_share"] = round(ds.is_ai.mean() * 100, 1)
S["ds_remote_share"] = round((ds.remote_class == "Remote").mean() * 100, 1)
S["ds_ghost_share"] = round(ds.is_ghost.mean() * 100, 1)
eng = df[df.function == "Engineering"]
S["eng_manager_share"] = round(eng.is_manager.mean() * 100, 1)
S["eng_ai_share"] = round(eng.is_ai.mean() * 100, 1)
prod = df[df.function == "Product"]
S["prod_manager_share"] = round(prod.is_manager.mean() * 100, 1)
# manager seats per 100 IC roles by function
for name, sub in [("overall", df), ("data", ds), ("eng", eng), ("product", prod)]:
    mgr = sub.is_manager.sum()
    ic = len(sub) - mgr
    S[f"manager_per_100_ic_{name}"] = round(mgr / max(ic, 1) * 100, 1)
    S[f"one_manager_per_n_ic_{name}"] = round(ic / max(mgr, 1), 1)
# remote by function
S["remote_by_function"] = {f: round((g.remote_class == "Remote").mean() * 100, 1) for f, g in df.groupby("function")}
S["manager_by_function"] = {f: round(g.is_manager.mean() * 100, 1) for f, g in df.groupby("function")}
S["ai_by_function"] = {f: round(g.is_ai.mean() * 100, 1) for f, g in df.groupby("function")}
S["ghost_by_function"] = {f: round(g.is_ghost.mean() * 100, 1) for f, g in df.groupby("function")}
# company table (min 30 postings)
ct = df.groupby("company").agg(n=("title", "size"), ai=("is_ai", "mean"), mgr=("is_manager", "mean"),
                               remote=("remote_class", lambda s: (s == "Remote").mean()),
                               ghost=("is_ghost", "mean"), median_age=("age_days", "median"),
                               ds=("function", lambda s: (s == "Data / AI").mean()))
ct = ct[ct.n >= 30].sort_values("n", ascending=False)
for c in ["ai", "mgr", "remote", "ghost", "ds"]:
    ct[c] = (ct[c] * 100).round(1)
ct["median_age"] = ct["median_age"].round(0)
ct.to_csv(os.path.join(BASE, "data", "company_table.csv"))
S["top_companies_by_n"] = ct["n"].head(10).to_dict()
S["top_ai_share"] = ct.sort_values("ai", ascending=False)[["n", "ai"]].head(10).to_dict("index")
S["top_ghost"] = ct.sort_values("ghost", ascending=False)[["n", "ghost"]].head(10).to_dict("index")
S["top_remote"] = ct.sort_values("remote", ascending=False)[["n", "remote"]].head(10).to_dict("index")
S["top_mgr"] = ct.sort_values("mgr", ascending=False)[["n", "mgr"]].head(10).to_dict("index")
# metros (fractional)
mc = Counter()
for metros in df.metros:
    for m in metros:
        mc[m] += 1 / len(metros)
S["top_metros"] = {k: round(v, 1) for k, v in mc.most_common(15)}
S["pct_with_recognized_metro"] = round(df.metros.apply(bool).mean() * 100, 1)
# age buckets
S["age_buckets"] = {
    "<30d": round((df.age_days < 30).mean() * 100, 1),
    "30-90d": round(((df.age_days >= 30) & (df.age_days <= 90)).mean() * 100, 1),
    "91-180d": round(((df.age_days > 90) & (df.age_days <= 180)).mean() * 100, 1),
    ">180d": round((df.age_days > 180).mean() * 100, 1),
}
# US-only remote (locations mentioning US or Remote US)
us = df[df.location.str.contains(r"\bUS\b|United States|\bUSA\b", case=False, na=False, regex=True) | df.remote_class.eq("Remote")]
S["us_n"] = len(us)
S["us_remote_share"] = round((us.remote_class == "Remote").mean() * 100, 1)
# sample check: manager titles
S["sample_manager_titles"] = df[df.is_manager].title.value_counts().head(15).to_dict()
S["sample_ds_manager_titles"] = ds[ds.is_manager].title.value_counts().head(10).to_dict()
print("OTHER top titles:", df[df.function=="Other"].title.value_counts().head(12).to_dict())
print("INTERCOM title-AI:", round(df[df.company=="intercom"].is_ai.mean()*100,1), "broad:", round(df[df.company=="intercom"].is_ai_broad.mean()*100,1))
print("ANTHROPIC title-AI:", round(df[df.company=="anthropic"].is_ai.mean()*100,1), "broad:", round(df[df.company=="anthropic"].is_ai_broad.mean()*100,1))
print("DATABRICKS title-AI:", round(df[df.company=="databricks"].is_ai.mean()*100,1), "broad:", round(df[df.company=="databricks"].is_ai_broad.mean()*100,1))
json.dump(S, open(os.path.join(BASE, "data", "summary.json"), "w"), indent=2)
print(json.dumps(S, indent=2))
