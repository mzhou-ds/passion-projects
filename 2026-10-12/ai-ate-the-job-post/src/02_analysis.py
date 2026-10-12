"""Classify every job post / seeker pitch and build the time series.

Classification is transparent keyword rules over the post text (first check:
the header line posters write, e.g. 'Acme | Senior ML Engineer | REMOTE').
Salary ranges are parsed from $-amounts like $150k, $120,000, $180-220k.
"""
import json, re
import pandas as pd
import numpy as np

AI_PAT = re.compile(r"\b(ai|ml|llm|llms|gpt|machine learning|deep learning|nlp|"
                    r"artificial intelligence|genai|generative ai|computer vision|"
                    r"mlops|data scien\w+|prompt engineer\w*|neural network\w*|"
                    r"rag|fine[- ]tun\w+|transformer model\w*|agent(s)?\b.{0,20}\b(ai|llm))", re.I)
ROLE_PATS = {
    "ai_ml": re.compile(r"\b(ml engineer|machine learning engineer|ai engineer|research scientist|data scientist|applied scientist|mlops|ai/ml|machine learning|deep learning)\b", re.I),
    "backend": re.compile(r"\bbackend|back-end|back end\b", re.I),
    "frontend": re.compile(r"\bfrontend|front-end|front end\b", re.I),
    "fullstack": re.compile(r"\bfull[- ]?stack\b", re.I),
    "data_eng": re.compile(r"\bdata engineer|analytics engineer|data platform\b", re.I),
    "devops_infra": re.compile(r"\bdevops|sre|site reliability|platform engineer|infrastructure engineer\b", re.I),
    "mobile": re.compile(r"\b(mobile engineer|ios engineer|android engineer|ios developer|android developer|react native)\b", re.I),
    "product": re.compile(r"\bproduct manager|product management|\bpm\b", re.I),
    "design": re.compile(r"\bdesigner|product design|ux design|ui/ux\b", re.I),
    "sales_gtM": re.compile(r"\b(account executive|sales|business development|growth|marketing manager|gtm)\b", re.I),
    "security": re.compile(r"\bsecurity engineer|security analyst|appsec\b", re.I),
}
STACK = {
    "python": r"\bpython\b", "typescript": r"\btypescript\b", "react": r"\breact\b",
    "go": r"\bgolang\b|\bgo\b", "rust": r"\brust\b", "java": r"\bjava\b",
    "ruby": r"\bruby|rails\b", "node": r"\bnode(\.js)?\b", "aws": r"\baws\b",
    "kubernetes": r"\bkubernetes|k8s\b", "postgres": r"\bpostgres\w*\b",
    "pytorch": r"\bpytorch\b", "llm_stack": r"\b(langchain|openai|anthropic|llamaindex|vector|embeddings)\b",
}
SAL_PAT = re.compile(r"\$\s?(\d{2,3}(?:,\d{3})?|\d{2,3})\s?k?\b", re.I)

def parse_salary(text):
    vals = []
    for m in SAL_PAT.finditer(text):
        raw = m.group(0)
        num = float(m.group(1).replace(",", ""))
        if "k" in raw.lower() and num < 1000:
            num *= 1000
        if 30000 <= num <= 900000:
            vals.append(num)
    if not vals:
        return np.nan, np.nan, 0
    return min(vals), max(vals), 1

def classify(df):
    t = df["text"].fillna("")
    low = t.str.lower()
    df["is_ai"] = low.str.contains(AI_PAT).astype(int)
    df["llm_era"] = low.str.contains(r"\b(llm|llms|gpt|generative ai|genai|large language model)\b", regex=True).astype(int)
    df["bare_ai"] = low.str.contains(r"\bai\b", regex=True).astype(int)
    df["ds_ml_lang"] = low.str.contains(r"\b(data scien\w+|machine learning|deep learning)\b", regex=True).astype(int)
    for role, pat in ROLE_PATS.items():
        df[f"role_{role}"] = low.str.contains(pat).astype(int)
    for name, pat in STACK.items():
        df[f"stk_{name}"] = low.str.contains(pat, regex=True).astype(int)
    df["remote"] = low.str.contains(r"\bremote\b").astype(int)
    df["onsite_hybrid"] = low.str.contains(r"\b(on[- ]?site|hybrid|in[- ]office)\b").astype(int)
    df["sf_bay"] = low.str.contains(r"san francisco|bay area|\bsf\b|silicon valley").astype(int)
    df["nyc"] = low.str.contains(r"new york|\bnyc\b").astype(int)
    df["founding"] = low.str.contains(r"\bfounding\b").astype(int)
    df["senior_plus"] = low.str.contains(r"\b(senior|staff|principal|lead|sr\.)\b").astype(int)
    df["visa"] = low.str.contains(r"\bvisa\b").astype(int)
    sal = t.apply(parse_salary)
    df["sal_min"] = [s[0] for s in sal]; df["sal_max"] = [s[1] for s in sal]
    df["sal_disclosed"] = [s[2] for s in sal]
    df["sal_mid"] = (df["sal_min"] + df["sal_max"]) / 2
    df["ym"] = df["thread_date"].str[:7]
    df["n_words"] = t.str.split().str.len()
    return df

def main():
    hiring = classify(pd.read_csv("data/posts_hiring.csv"))
    seekers = classify(pd.read_csv("data/posts_seekers.csv"))
    hiring.to_csv("data/posts_hiring_classified.csv", index=False)
    seekers.to_csv("data/posts_seekers_classified.csv", index=False)

    g = hiring.groupby("ym")
    ts = pd.DataFrame({
        "posts": g.size(), "ai_share": g["is_ai"].mean(), "llm_share": g["llm_era"].mean(),
        "bare_ai_share": g["bare_ai"].mean(), "ds_ml_share": g["ds_ml_lang"].mean(), "remote_share": g["remote"].mean(),
        "sf_share": g["sf_bay"].mean(), "founding_share": g["founding"].mean(),
        "senior_share": g["senior_plus"].mean(), "sal_disclosed_share": g["sal_disclosed"].mean(),
        "sal_median": g["sal_mid"].median(),
        "ai_sal_median": hiring[hiring.is_ai == 1].groupby("ym")["sal_mid"].median(),
        "nonai_sal_median": hiring[hiring.is_ai == 0].groupby("ym")["sal_mid"].median(),
    })
    ts["seekers"] = seekers.groupby("ym").size()
    ts["seeker_ai_share"] = seekers.groupby("ym")["is_ai"].mean()
    ts["seekers_per_post"] = ts["seekers"] / ts["posts"]
    for role in ROLE_PATS:
        ts[f"role_{role}_share"] = hiring.groupby("ym")[f"role_{role}"].mean()
    for name in STACK:
        ts[f"stk_{name}_share"] = hiring.groupby("ym")[f"stk_{name}"].mean()
    ts.to_csv("data/timeseries.csv")

    def era(mask):
        h = hiring[mask]
        return {"posts_per_month": float(h.groupby("ym").size().mean()),
                "ai_share": float(h["is_ai"].mean()), "remote_share": float(h["remote"].mean()),
                "sal_disclosed_share": float(h["sal_disclosed"].mean()),
                "sal_median": float(h["sal_mid"].median()),
                "founding_share": float(h["founding"].mean())}
    yrs = pd.to_datetime(hiring["thread_date"]).dt.year
    summary = {
        "n_hiring_posts": int(len(hiring)), "n_seeker_posts": int(len(seekers)),
        "months": int(hiring["ym"].nunique()),
        "eras": {str(y): era(yrs == y) for y in sorted(yrs.unique())},
        "latest_ai_share": float(ts["ai_share"].iloc[-3:].mean()),
        "latest_seekers_per_post": float(ts["seekers_per_post"].iloc[-3:].mean()),
        "peak_posts_month": ts["posts"].idxmax(), "peak_posts": int(ts["posts"].max()),
        "trough_posts_month": ts.loc[ts.index >= "2022", "posts"].idxmin(),
        "trough_posts": int(ts.loc[ts.index >= "2022", "posts"].min()),
    }
    json.dump(summary, open("data/summary.json", "w"), indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
