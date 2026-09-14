"""Part 2 — Discourse: what tech talks about (Hacker News front page + 2021-2026 AI share).

Classifies the top-500 front-page stories into topics with keyword rules, and
charts AI-keyword share of all HN stories per month since 2021 (Algolia data,
one keyword query per month — see 01b_fetch_hn_ai.py for why).
"""
import json, re, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from urllib.parse import urlparse

BASE = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026"
plt.rcParams.update({"figure.dpi": 140, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

TOPICS = [
    ("Show HN & launches", r"^show hn"),
    ("Ask HN", r"^ask hn"),
    ("AI / ML", r"\b(ai|llm|gpt|Muse|chatgpt|machine learning|neural|diffusion|transformer|openai|anthropic|deepmind|gemini|llama|rag\b|agents?|copilot|deepseek|qwen|mistral|grok|openrouter|huggingface|ollama|vllm|midjourney|self-improv)\b"),
    ("Hardware & chips", r"\b(chip|gpu|cpu|semiconductor|nvidia|tsmc|intel\b|amd\b|raspberry|hardware|silicon|asml|arm\b|microcode|8087|qemu|retro|fpga|battery|solid-state)\b"),
    ("Security", r"\b(security|vulnerab|cve-|hack|breach|ransomware|encrypt|phish|malware|0-day|zero-day|rsa\b|surveillance|nsa\b)\b"),
    ("Startups & business", r"\b(startup|funding|yc\b|ipo|acqui|valuation|layoff|hiring|saas|revenue|unicorn|sequoia|a16z|board\b|ceo\b|market-cap|s&p\b)\b"),
    ("Programming & CS", r"\b(rust\b|v8\b|javascript|typescript|compiler|type\b|types\b|wasm|webassembly|concurrency|kernel|linux|postgres|database|css\b|ide\b|git\b|programmer|algorithm|logic\b|functional|async|await|runtime|basic\b|julia\b|python\b|go\b|sql\b)\b"),
    ("Science & math", r"\b(science|physics|genome|dna\b|radiation|math\b|astronom|biolog|neuroscience|quantum|chemistry|climate|evolution|navier-stokes|theorem)\b"),
    ("Big Tech & products", r"\b(apple|iphone|ipad|google\b|android|sony|youtube|microsoft|meta\b|amazon\b|tesla|spacex|samsung|app store|play store|windows\b)\b"),
    ("Policy, privacy & society", r"\b(privacy|regulat|\beu\b|antitrust|gdpr|copyright|government|military|internet|blackout|censorship|cartography|un\b|election|senate|fcc)\b"),
]
def classify(title):
    t = (title or "").lower()
    for name, pat in TOPICS:
        if re.search(pat, t):
            return name
    return "Essays & misc"

raw = json.load(open(f"{BASE}/data/hn_top500.json"))
stories = pd.DataFrame(raw["stories"])
stories["topic"] = stories["title"].apply(classify)
stories["domain"] = stories["url"].apply(
    lambda u: urlparse(u).netloc.replace("www.", "") if isinstance(u, str) else "text post")
print(stories["topic"].value_counts())

# ---------- chart 7: topic mix ----------
tc = stories["topic"].value_counts()
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(tc.index[::-1], (tc[::-1] / len(stories) * 100),
               color=["#c0392b" if t == "AI / ML" else "#4a6fa5" for t in tc.index[::-1]], alpha=0.85)
ax.bar_label(bars, fmt="%.1f%%")
ax.set_title(f"What tech talks about: HN front page by topic (n={len(stories)}, Sep 2026)",
             fontsize=14, pad=12)
ax.set_xlabel("% of front-page stories")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/07_hn_topics.png")

# ---------- chart 8: AI keyword share over time ----------
ai_m = pd.DataFrame(json.load(open(f"{BASE}/data/hn_ai_monthly.json")))
# NOTE: Algolia's estimated nbHits for the *total* story count becomes unstable
# for 2026 months (alternating 29k/143k/370k while keyword counts stay sane), so
# the monthly series is capped at Dec 2025; Sep-2026 level comes from the
# front-page classifier instead.
ai_m = ai_m[ai_m["year"] <= 2025].copy()
ai_m["date"] = pd.to_datetime(ai_m[["year", "month"]].assign(day=1))
fig, ax = plt.subplots(figsize=(11, 4.5))
for kw, col, lab in [("kw_AI", "#c0392b", "'AI'"), ("kw_ChatGPT", "#e67e22", "'ChatGPT'"),
                     ("kw_LLM", "#8e44ad", "'LLM'")]:
    share = ai_m[kw] / ai_m["stories_total"] * 100
    ax.plot(ai_m["date"], share, color=col, lw=2, label=lab)
ax.axvline(pd.Timestamp("2022-11-30"), color="gray", ls="--", alpha=0.6)
ax.text(pd.Timestamp("2022-11-30"), ax.get_ylim()[1] * 0.92, "ChatGPT launch", fontsize=9)
ax.set_title("The AI takeover of tech discourse (keyword share of HN stories)", fontsize=14, pad=12)
ax.set_ylabel("% of stories mentioning keyword")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
ax.legend(frameon=False, title="keyword")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/08_hn_ai_share.png")

# ---------- chart 9: engagement by topic ----------
eng = stories.groupby("topic").agg(n=("id", "size"),
                                   med_comments=("descendants", "median"),
                                   med_score=("score", "median")).reset_index()
eng = eng[eng["n"] >= 5]
fig, ax = plt.subplots(figsize=(10, 6))
for _, r in eng.iterrows():
    ax.scatter(r["med_score"], r["med_comments"], s=r["n"] * 6,
               color="#c0392b" if r["topic"] == "AI / ML" else "#4a6fa5", alpha=0.8)
    ax.annotate(r["topic"], (r["med_score"], r["med_comments"]), fontsize=9,
                xytext=(6, 4), textcoords="offset points")
ax.set_title("Engagement by topic (bubble size = story count)", fontsize=14, pad=12)
ax.set_xlabel("Median score"); ax.set_ylabel("Median comments")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/09_hn_engagement.png")

# ---------- chart 10: domains ----------
dom = stories["domain"].value_counts().head(12)
fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(dom.index[::-1], dom.values[::-1], color="#16a085", alpha=0.85)
ax.set_title("Where front-page stories link to (top domains)", fontsize=14, pad=12)
ax.set_xlabel("Stories")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/10_hn_domains.png")

# ---------- findings ----------
kw = "kw_AI"
findings = {
    "n_stories": int(len(stories)),
    "topic_shares": {k: round(v / len(stories) * 100, 1) for k, v in tc.items()},
    "ai_kw_share_2021_avg_pct": round((ai_m[ai_m["year"] == 2021][kw] / ai_m[ai_m["year"] == 2021]["stories_total"]).mean() * 100, 2),
    "ai_kw_share_2025_avg_pct": round((ai_m[ai_m["year"] == 2025][kw] / ai_m[ai_m["year"] == 2025]["stories_total"]).mean() * 100, 2),
    "chatgpt_kw_share_peak_pct": round((ai_m["kw_ChatGPT"] / ai_m["stories_total"]).max() * 100, 2),
    "ai_med_comments": float(stories[stories["topic"] == "AI / ML"]["descendants"].median()),
    "nonai_med_comments": float(stories[stories["topic"] != "AI / ML"]["descendants"].median()),
    "top_domains": dom.head(5).to_dict(),
}
with open(f"{BASE}/data/findings_hn.json", "w") as f:
    json.dump(findings, f, indent=2)
print(json.dumps(findings, indent=2))
