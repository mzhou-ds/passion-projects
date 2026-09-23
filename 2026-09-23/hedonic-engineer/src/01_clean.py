#!/usr/bin/env python3
"""01_clean.py — build the analysis sample from the Stack Overflow 2025 survey.

Input : survey_results_public.csv (downloaded separately, see README).
Output: data/sample.parquet — one row per professional developer with valid
        compensation, plus engineered feature columns.
"""
import re
import pandas as pd
import numpy as np

RAW = "../../hedonic-tmp/survey_results_public.csv"  # fallback if run from repo
import os
if not os.path.exists(RAW):
    RAW = os.environ.get("SO2025_RAW", "/home/hatch/workspace/hedonic-tmp/survey_results_public.csv")

COLS = ["MainBranch", "Country", "WorkExp", "YearsCode", "DevType", "EdLevel",
        "RemoteWork", "OrgSize", "Industry", "ICorPM", "ConvertedCompYearly",
        "AISelect", "LanguageHaveWorkedWith", "Age", "Employment"]

TOP_LANGS = ["JavaScript", "HTML/CSS", "Python", "TypeScript", "SQL", "Bash/Shell (all shells)",
             "Java", "C#", "C++", "C", "PHP", "Go", "Rust", "Kotlin", "Swift",
             "Ruby", "R", "Dart", "Scala", "PowerShell"]
TOP_ROLES = ["Developer, full-stack", "Developer, back-end", "Developer, front-end",
             "Developer, desktop or enterprise applications", "Developer, mobile",
             "Developer, embedded applications or devices", "Data scientist or machine learning specialist",
             "Data engineer", "DevOps specialist", "Developer, game or graphics",
             "Engineering manager", "Developer, QA or test", "Developer, AI",
             "Security professional", "Developer, cloud infrastructure",
             "System administrator", "Developer, blockchain", "Developer Advocate"]

def clean_exp(v):
    if pd.isna(v):
        return np.nan
    v = str(v)
    if "Less than 1" in v:
        return 0.5
    if "50 or more" in v:
        return 50.0
    m = re.match(r"(\d+)", v)
    return float(m.group(1)) if m else np.nan

def main():
    df = pd.read_csv(RAW, usecols=COLS, low_memory=False)
    print("raw rows:", len(df))
    # professional developers with valid comp
    d = df[df["MainBranch"] == "I am a developer by profession"].copy()
    d = d[d["ConvertedCompYearly"].notna()]
    d = d[(d["ConvertedCompYearly"] >= 1_000) & (d["ConvertedCompYearly"] <= 2_000_000)]
    # keep employees + contractors (paid work), drop students/retired/not-employed
    d = d[~d["Employment"].isin(["Student", "Not employed", "Retired"])]

    d["log_comp"] = np.log(d["ConvertedCompYearly"])
    d["WorkExpY"] = d["WorkExp"].apply(clean_exp)
    d = d[d["WorkExpY"].notna()]

    # simplified features
    d["remote_simple"] = d["RemoteWork"].map({
        "Remote": "Remote",
        "Hybrid (some remote, leans heavy to in-person)": "Hybrid",
        "Hybrid (some in-person, leans heavy to flexibility)": "Hybrid",
        "In-person": "In-person",
        "Your choice (very flexible, you can come in when you want or just as needed)": "Flexible",
    }).fillna("Other")
    d["ai_freq"] = d["AISelect"].map({
        "Yes, I use AI tools daily": "daily",
        "Yes, I use AI tools weekly": "weekly",
        "Yes, I use AI tools monthly or infrequently": "monthly",
        "No, and I don't plan to": "no_never",
        "No, but I plan to soon": "no_soon",
    }).fillna("unknown")
    d["manager"] = (d["ICorPM"] == "People manager").astype(int)

    langs = d["LanguageHaveWorkedWith"].fillna("")
    for lang in TOP_LANGS:
        d[f"lang_{lang}"] = langs.str.contains(re.escape(lang), regex=True).astype(int)

    roles = d["DevType"].fillna("")
    for role in TOP_ROLES:
        key = re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_")[:28]
        d[f"role_{key}"] = roles.str.contains(re.escape(role), regex=True).astype(int)

    # top-30 countries as dummies later; keep string col
    d["Country_top30"] = d["Country"].where(
        d["Country"].isin(d["Country"].value_counts().head(30).index), "Other")

    d["Ed_simple"] = d["EdLevel"].map({
        "Bachelor’s degree (B.A., B.S., B.Eng., etc.)": "bachelors",
        "Master’s degree (M.A., M.S., M.Eng., MBA, etc.)": "masters",
        "Some college/university study without earning a degree": "some_college",
        "Secondary school (e.g. American high school, German Realschule or Gymnasium, etc.)": "secondary",
        "Professional degree (JD, MD, Ph.D, Ed.D, etc.)": "doctorate",
        "Associate degree (A.A., A.S., etc.)": "associate",
    }).fillna("other")

    d["Org_simple"] = d["OrgSize"].map({
        "Less than 20 employees": "1-19",
        "20 to 99 employees": "20-99",
        "100 to 499 employees": "100-499",
        "500 to 999 employees": "500-999",
        "1,000 to 4,999 employees": "1000-4999",
        "5,000 to 9,999 employees": "5000-9999",
        "10,000 or more employees": "10000+",
        "Just me - I am a freelancer, sole proprietor, etc.": "solo",
    }).fillna("other")

    keep = (["log_comp", "ConvertedCompYearly", "Country", "Country_top30", "WorkExpY",
             "remote_simple", "ai_freq", "manager", "Ed_simple", "Org_simple",
             "Industry", "Age", "DevType"]
            + [f"lang_{l}" for l in TOP_LANGS]
            + [c for c in d.columns if c.startswith("role_")])
    d[keep].to_csv("data/sample.csv", index=False)
    print("sample rows:", len(d), "| median comp:", d["ConvertedCompYearly"].median())
    print("countries:", d["Country"].nunique())

if __name__ == "__main__":
    main()
