"""
Parse raw HN job posts into structured features.

A Who-is-Hiring post usually leads with: Company | Location | Remote |
Role | Salary... The body then lists a stack. We extract:
  - remote status (remote / hybrid / onsite / unknown), location buckets
  - salary mentions ($ ranges, normalized to annual USD midpoint)
  - seniority (senior/staff/principal/lead), founding/early hints
  - tech mentions from a curated dictionary (languages, frameworks,
    infra, data, AI terms) -- word-boundary regex, lowercased text
  - AI-post flag: mentions of AI/ML/LLM terms

Output: data/posts_parsed.csv
"""
import html
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TECH = {
    # languages
    "python": r"\bpython\b", "typescript": r"\btypescript\b|\bts\b(?=\s*(?:/|,|and|developer|engineer))",
    "javascript": r"\bjavascript\b|\bnode\.?js\b", "go": r"\bgolang\b|\bgo\b(?=\s*(?:/|,|and|developer|engineer|backend))",
    "rust": r"\brust\b", "java": r"\bjava\b(?!script)", "kotlin": r"\bkotlin\b",
    "swift": r"\bswift\b", "ruby": r"\bruby\b|\brails\b", "php": r"\bphp\b|\blaravel\b",
    "scala": r"\bscala\b", "elixir": r"\belixir\b", "c++": r"\bc\+\+\b", "c#": r"\bc#\b|\.net\b",
    # frontend / mobile
    "react": r"\breact\b", "next.js": r"\bnext\.?js\b", "vue": r"\bvue\b", "angular": r"\bangular\b",
    "ios": r"\bios\b", "android": r"\bandroid\b", "react native": r"\breact native\b", "flutter": r"\bflutter\b",
    # backend / infra
    "postgres": r"\bpostgres(?:ql)?\b", "mysql": r"\bmysql\b", "mongodb": r"\bmongo(?:db)?\b",
    "redis": r"\bredis\b", "kafka": r"\bkafka\b", "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "aws": r"\baws\b|amazon web services", "gcp": r"\bgcp\b|google cloud", "azure": r"\bazure\b",
    "docker": r"\bdocker\b", "terraform": r"\bterraform\b", "graphql": r"\bgraphql\b",
    # data / AI
    "sql": r"\bsql\b", "spark": r"\bspark\b", "dbt": r"\bdbt\b", "airflow": r"\bairflow\b",
    "pytorch": r"\bpytorch\b", "tensorflow": r"\btensorflow\b",
    "llm": r"\bllm(s)?\b|large language model", "ai/ml": r"\b(ai|ml|machine learning|deep learning|nlp|computer vision)\b",
    "rag": r"\brag\b|retrieval augmented", "agents": r"\bai agent(s)?\b|agentic\b",
    "data science": r"\bdata scien(ce|tist)\b", "analytics": r"\bdata analyst\b|\banalytics engineer\b",
}
AI_TERMS = ["llm", "ai/ml", "rag", "agents", "pytorch", "tensorflow"]

LOCATIONS = {
    "san francisco / bay area": r"san francisco|bay area|\bsf\b",
    "new york": r"new york|\bnyc\b",
    "seattle": r"seattle",
    "austin": r"austin",
    "boston": r"boston",
    "los angeles": r"los angeles|\bla\b(?=\s*(?:/|,|\||-))",
    "london": r"london",
    "berlin": r"berlin",
    "toronto": r"toronto",
    "remote - us": r"remote.{0,20}(us|usa|united states)|us remote",
    "remote - worldwide": r"remote.{0,20}(worldwide|global|anywhere)|worldwide remote",
}


def clean(text: str) -> str:
    t = html.unescape(str(text))
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_salary(text_low: str):
    # $120k, $120,000, 120k-160k, $150K - $200K etc.
    m = re.findall(r"\$?\s*(\d{2,3})\s*k\s*(?:-|–|to)\s*\$?\s*(\d{2,3})\s*k", text_low)
    if m:
        lo, hi = int(m[0][0]) * 1000, int(m[0][1]) * 1000
        if 30_000 <= lo <= 600_000 and hi > lo:
            return lo, hi, (lo + hi) / 2
    m = re.findall(r"\$\s*(\d{2,3}),\d{3}\s*(?:-|–|to)\s*\$?\s*(\d{2,3}),\d{3}", text_low)
    if m:
        lo, hi = int(m[0][0]) * 1000, int(m[0][1]) * 1000
        if 30_000 <= lo <= 900_000 and hi > lo:
            return lo, hi, (lo + hi) / 2
    return None, None, None


def main():
    df = pd.read_csv(DATA / "posts_raw.csv")
    df["text_clean"] = df["text"].map(clean)
    df["text_low"] = df["text_clean"].str.lower()
    df["thread_month"] = df["thread_date"].str.slice(0, 7)
    df["thread_dt"] = pd.to_datetime(df["thread_date"], errors="coerce", utc=True)

    first200 = df["text_low"].str.slice(0, 200)
    df["is_remote"] = first200.str.contains(r"\bremote\b", regex=True) | df["text_low"].str.slice(0, 400).str.contains(r"\bremote\b", regex=True)
    df["is_hybrid"] = df["text_low"].str.contains(r"\bhybrid\b", regex=True)
    df["is_onsite"] = df["text_low"].str.slice(0, 400).str.contains(r"on-?site|in[- ]office|in person", regex=True)
    df["work_mode"] = "unknown"
    df.loc[df["is_hybrid"], "work_mode"] = "hybrid"
    df.loc[df["is_remote"] & ~df["is_hybrid"], "work_mode"] = "remote"
    df.loc[df["is_onsite"] & ~df["is_remote"] & ~df["is_hybrid"], "work_mode"] = "onsite"

    df["is_senior"] = df["text_low"].str.contains(r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b", regex=True)
    df["is_ai_post"] = False
    for name, pat in TECH.items():
        col = f"tech_{name}"
        df[col] = df["text_low"].str.contains(pat, regex=True)
    ai_cols = [f"tech_{t}" for t in AI_TERMS]
    df["is_ai_post"] = df[ai_cols].any(axis=1)
    df["n_tech"] = df[[c for c in df.columns if c.startswith("tech_")]].sum(axis=1)

    salaries = df["text_low"].map(parse_salary)
    df["salary_min"], df["salary_max"], df["salary_mid"] = zip(*salaries)
    df["has_salary"] = df["salary_mid"].notna()

    for loc, pat in LOCATIONS.items():
        df[f"loc_{loc}"] = df["text_low"].str.slice(0, 300).str.contains(pat, regex=True)

    df.to_csv(DATA / "posts_parsed.csv", index=False)
    print(df.shape)
    print(df["work_mode"].value_counts().to_string())
    print(f"AI posts: {df['is_ai_post'].mean():.1%}  salary disclosed: {df['has_salary'].mean():.1%}")


if __name__ == "__main__":
    main()
