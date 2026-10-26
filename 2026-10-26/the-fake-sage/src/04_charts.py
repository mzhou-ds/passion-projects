"""Charts for The Fake Sage."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "charts"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

per = pd.read_csv(ROOT / "data" / "per_thinker.csv")
res = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))

# 1) stacked provenance bar, worst unverified first
d = per.sort_values("unverified_share_all", ascending=True)
fig, ax = plt.subplots(figsize=(9, 9))
ax.barh(d.thinker, d.fake_share_checked * 0 + (d.disputed + d.misattributed) / d.total,
        color="#b3392e", label="Disputed / misattributed (fake)")
ax.barh(d.thinker, d.unsourced / d.total, left=(d.disputed + d.misattributed) / d.total,
        color="#e0a458", label="Attributed, no source (unverified)")
ax.barh(d.thinker, d.sourced / d.total,
        left=(d.disputed + d.misattributed + d.unsourced) / d.total,
        color="#4a7a5b", label="Sourced")
ax.set_xlabel("Share of the thinker's Wikiquote canon")
ax.set_title("How much of each sage is actually sourced?\nRumi is 85% provenance-free; Laozi has the worst proven-fake rate (19%)")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout(); fig.savefig(CH / "provenance_stack.png", dpi=150); plt.close(fig)

# 2) the fake dialect
dial = res["dialect"]
labels = ["Therapy words\nper 1k", "Second person\nper 1k", "First person\nper 1k", "Median length\n(words)"]
fake = [dial["therapy_per_k"]["fake_mean"], dial["second_person_per_k"]["fake_mean"],
        dial["first_person_per_k"]["fake_mean"], dial["words"]["fake_median"]]
src = [dial["therapy_per_k"]["sourced_mean"], dial["second_person_per_k"]["sourced_mean"],
       dial["first_person_per_k"]["sourced_mean"], dial["words"]["sourced_median"]]
fig, axes = plt.subplots(1, 4, figsize=(10, 3.2))
for ax, lab, f, s in zip(axes, labels, fake, src):
    ax.bar(["Fake", "Sourced"], [f, s], color=["#b3392e", "#4a7a5b"])
    ax.set_title(lab, fontsize=9)
    for i, v in enumerate([f, s]):
        ax.text(i, v * 1.04, f"{v:.0f}", ha="center", fontsize=9)
    ax.set_ylim(0, max(f, s) * 1.25)
fig.suptitle("Fake quotes speak a different dialect: shorter, warmer, aimed at you")
fig.tight_layout(); fig.savefig(CH / "fake_dialect.png", dpi=150); plt.close(fig)

# 3) east/west: fakes vs sourced therapy density
fb, sb = res["fake_dialect_by_tradition"], res["sourced_dialect_by_tradition"]
fig, ax = plt.subplots(figsize=(7, 4))
x = [0, 1]
ax.bar([i - 0.2 for i in x], [sb["east_therapy"], sb["west_therapy"]], width=0.4,
       color="#4a7a5b", label="What they actually said")
ax.bar([i + 0.2 for i in x], [fb["east_therapy"], fb["west_therapy"]], width=0.4,
       color="#b3392e", label="What we invented for them")
ax.set_xticks(x); ax.set_xticklabels(["Eastern sages", "Western thinkers"])
ax.set_ylabel("Therapy / self-help words per 1,000")
ax.set_title("The wellness voice is projected onto the East:\nfake Eastern quotes carry 2.5x the therapy vocabulary of fake Western ones")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(CH / "east_west_wellness.png", dpi=150); plt.close(fig)

# 4) fame vs fake share
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.scatter(per.pageviews_2024, per.fake_share_checked * 100, s=55, color="#34568b")
for _, r in per.iterrows():
    if r.fake_share_checked > 0.09 or r.pageviews_2024 > 3_000_000:
        ax.annotate(r.thinker, (r.pageviews_2024, r.fake_share_checked * 100),
                    fontsize=8, xytext=(4, 4), textcoords="offset points")
ax.set_xscale("log")
ax.set_xlabel("Wikipedia pageviews, 2024 (log scale)")
ax.set_ylabel("Proven-fake share of checked canon (%)")
ax.set_title("Fame helps a little (Spearman rho=0.32, p=0.09) —\nLaozi is both the most-read and the most-faked sage here")
fig.tight_layout(); fig.savefig(CH / "fame_vs_fake.png", dpi=150); plt.close(fig)

# 5) SHAP importance
shap_imp = res["classifier"]["shap_mean_abs"]
s = pd.Series(shap_imp).sort_values()
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.barh(s.index, s.values, color="#34568b")
ax.set_xlabel("Mean |SHAP| — XGBoost, voice-only fake detector (AUC 0.74)")
ax.set_title("Length is the loudest tell that a quote is fake")
fig.tight_layout(); fig.savefig(CH / "shap_importance.png", dpi=150); plt.close(fig)
print("charts done")
