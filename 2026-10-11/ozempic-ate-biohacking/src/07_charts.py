import pandas as pd, numpy as np, json, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parents[1]
C = ROOT/"charts"; C.mkdir(exist_ok=True)
df = pd.read_csv(ROOT/"data/trials_categorised.csv")
# 1 era expansion share + counts
g = df.groupby(["era","category"], observed=True).size().unstack(fill_value=0)
order = [c for c in ["diabetes","obesity_weight","cardiovascular","kidney","liver_mash","neuro","sleep_apnea","addiction","musculoskeletal","longevity_aging","other"] if c in g.columns]
g = g[order]
props = g.div(g.sum(axis=1), axis=0)
props.plot(kind="bar", stacked=True, figsize=(10,5), colormap="tab20")
plt.ylabel("share of trial starts"); plt.title("GLP-1 trials stopped being diabetes trials — indication share by era")
plt.legend(ncol=3, fontsize=7); plt.tight_layout(); plt.savefig(C/"indication_expansion.png", dpi=160); plt.close()
# 2 molecule timeline
d = df.dropna(subset=["start_year"]).copy(); d["primary"]=d["molecules"].str.split("|").str[0]
piv = d.groupby(["start_year","primary"]).size().unstack(fill_value=0)
piv = piv.loc[piv.index>=2005]
piv.plot(figsize=(10,5))
plt.ylabel("trials started"); plt.title("Trial starts by molecule: semaglutide and tirzepatide take over after 2017")
plt.tight_layout(); plt.savefig(C/"molecule_timeline.png", dpi=160); plt.close()
# 3 pubmed + pageviews
try:
    pub = pd.read_csv(ROOT/"data/pubmed_yearly.csv"); pv = pub.pivot(index="year", columns="term", values="pubmed_count")
    pv[["semaglutide","tirzepatide","liraglutide","metformin_benchmark"]].plot(figsize=(10,5))
    plt.ylabel("PubMed papers/yr"); plt.title("Literature follows the molecule: semaglutide + tirzepatide PubMed output")
    plt.tight_layout(); plt.savefig(C/"pubmed_trend.png", dpi=160); plt.close()
except Exception as e: print("pubmed chart", e)
try:
    wv = pd.read_csv(ROOT/"data/pageviews_monthly.csv"); wv["date"]=pd.to_datetime(wv["month"].astype(str), format="%Y%m")
    wp = wv.pivot_table(index="date", columns="article", values="views", aggfunc="sum")
    wp[["Ozempic","Mounjaro","Semaglutide","Tirzepatide"]].plot(figsize=(10,5))
    plt.ylabel("Wikipedia views / month"); plt.title("Attention peaked in 2024: the molecule is the search term, not the brand")
    plt.tight_layout(); plt.savefig(C/"attention.png", dpi=160); plt.close()
except Exception as e: print("pageviews chart", e)
# 4 expansion vs core: sponsor + results
fig, axes = plt.subplots(1,2, figsize=(11,4.5))
ct = pd.crosstab(df["is_expansion"], df["sponsor_class"], normalize="index")*100
ct.T.plot(kind="bar", ax=axes[0]); axes[0].set_title("Sponsor mix: expansion (1) vs core (0)"); axes[0].set_ylabel("% of trials")
df.groupby("is_expansion")["has_results"].mean().plot(kind="bar", ax=axes[1], color=["#64748b","#7c3aed"])
axes[1].set_title("Share with posted results"); axes[1].set_xticklabels(["core","expansion"], rotation=0)
plt.tight_layout(); plt.savefig(C/"sponsor_results_gap.png", dpi=160); plt.close()
# 5 FDA reactions
try:
    fda = json.loads((ROOT/"data/openfda.json").read_text())
    oz = pd.DataFrame(fda.get("OZEMPIC",{}).get("top_reactions",[])).head(10)
    if len(oz):
        plt.figure(figsize=(9,5)); plt.barh(oz["reaction"][::-1], oz["count"][::-1], color="#dc2626")
        plt.title("OpenFDA: top reported reactions for OZEMPIC (spontaneous reports, not incidence)")
        plt.tight_layout(); plt.savefig(C/"fda_reactions.png", dpi=160); plt.close()
except Exception as e: print("fda chart", e)
print("charts done")
