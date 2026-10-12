import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ts = pd.read_csv("data/timeseries.csv", index_col="ym")
x = pd.to_datetime(ts.index)

def save(fig, name):
    fig.tight_layout(); fig.savefig(f"charts/{name}", dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(x, ts["posts"], label="Job posts (Who is hiring)", color="#1f77b4")
ax.plot(x, ts["seekers"], label="Job seekers (Who wants to be hired)", color="#d62728")
ax.axvline(pd.Timestamp("2022-11-30"), color="grey", ls="--", lw=1)
ax.text(pd.Timestamp("2022-12-15"), ts["posts"].max()*0.92, "ChatGPT\nlaunches", fontsize=8, color="grey")
ax.set_title("HN hiring threads: demand vs supply, 2019-2026"); ax.legend(); ax.set_ylabel("top-level posts / month")
save(fig, "volume.png")

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(x, ts["ai_share"]*100, color="#9467bd", label="Job posts mentioning AI/ML/LLM")
ax.plot(x, ts["seeker_ai_share"]*100, color="#8c564b", ls="--", label="Seeker pitches mentioning AI/ML/LLM")
ax.plot(x, ts["llm_share"]*100, color="#e377c2", label="Job posts naming LLM/GPT/GenAI specifically")
ax.plot(x, ts["ds_ml_share"]*100, color="#7f7f7f", ls=":", label="Job posts using data-science/ML language")
ax.axvline(pd.Timestamp("2022-11-30"), color="grey", ls="--", lw=1)
ax.set_title("The AI share of tech hiring"); ax.set_ylabel("% of posts"); ax.legend()
save(fig, "ai_share.png")

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(x, ts["seekers_per_post"], color="#2ca02c")
ax.set_title("Tightness index: seekers per job post (higher = softer market for candidates)")
ax.set_ylabel("seekers / post")
save(fig, "tightness.png")

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(x, ts["remote_share"]*100, label="Remote mentioned")
ax.plot(x, ts["sf_share"]*100, label="SF Bay Area mentioned")
ax.set_title("Remote and SF shares of job posts"); ax.set_ylabel("% of posts"); ax.legend()
save(fig, "remote_sf.png")

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(x, ts["sal_median"]/1000, label="All posts, median parsed salary ($k)")
ax.plot(x, ts["ai_sal_median"]/1000, label="AI posts")
ax.plot(x, ts["nonai_sal_median"]/1000, label="Non-AI posts")
ax.plot(x, ts["sal_disclosed_share"]*100, color="grey", ls=":", label="% disclosing any $ figure (right axis, scaled)")
ax.set_title("Parsed salary medians in job posts"); ax.set_ylabel("$k"); ax.legend(fontsize=8)
save(fig, "salary.png")

roles = [c for c in ts.columns if c.startswith("role_")]
fig, ax = plt.subplots(figsize=(10, 4.5))
for c in roles:
    ax.plot(x, ts[c]*100, label=c.replace("role_", "").replace("_share", ""))
ax.set_title("Role mix in job posts (% mentioning)"); ax.set_ylabel("% of posts"); ax.legend(fontsize=7, ncol=3)
save(fig, "role_mix.png")
print("charts done")
