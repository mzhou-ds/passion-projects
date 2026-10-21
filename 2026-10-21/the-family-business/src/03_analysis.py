"""Headline analyses over the genealogy table. Everything is computed on
clearly named universes:

  DEMAND  = the top-5,000-by-downloads sample (models people actually pull)
  UNION   = all unique models across the three samples
  NEWEST  = the 3,000 most recently created models (the supply firehose)

`downloads` on the Hub API is last-30-day downloads; `downloadsAllTime`
is the cumulative counter. Shares are reported on last-30-day volume
unless labelled all-time.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
df = pd.read_csv(HERE / "data" / "models_genealogy.csv", low_memory=False)
fam = pd.read_csv(HERE / "data" / "families.csv")
OUT = HERE / "data" / "summary.json"

demand = df[df["samples"].str.contains("downloads")].copy()
newest = df[df["samples"].str.contains("newest")].copy()
liked = df[df["samples"].str.contains("likes")].copy()
S = {}


def hhi(shares):
    return float((shares**2).sum())


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * x).sum()) / (n * x.sum()) - (n + 1) / n)


def share_table(data, col, value="downloads"):
    t = data.groupby(col)[value].sum().sort_values(ascending=False)
    return t / t.sum()

# ---------- universe sizes ----------
S["n_union"] = int(len(df))
S["n_demand"] = int(len(demand))
S["n_newest"] = int(len(newest))
S["demand_downloads_total"] = int(demand["downloads"].sum())
S["demand_downloads_alltime_total"] = int(demand["downloadsAllTime"].sum())

# ---------- derivative share ----------
for name, data in [("demand", demand), ("union", df)]:
    d = data[data["is_derivative"] == True]  # noqa: E712
    S[f"{name}_deriv_share_of_models"] = float(data["is_derivative"].mean())
    S[f"{name}_deriv_share_of_downloads"] = float(
        d["downloads"].sum() / data["downloads"].sum()
    )
    S[f"{name}_deriv_share_of_downloads_alltime"] = float(
        d["downloadsAllTime"].sum() / data["downloadsAllTime"].sum()
    )
    S[f"{name}_relation_mix_downloads"] = {
        str(k): float(v)
        for k, v in share_table(d, "relation").items()
    }

# ---------- concentration (demand universe) ----------
for level in ["family", "root_org", "root"]:
    sh = share_table(demand, level)
    S[f"hhi_{level}"] = hhi(sh)
    S[f"effective_n_{level}"] = 1.0 / hhi(sh)
    S[f"top5_share_{level}"] = float(sh.head(5).sum())
    S[f"top10_share_{level}"] = float(sh.head(10).sum())
    S[f"top_{level}"] = [
        {"name": str(k), "share": float(v)} for k, v in sh.head(15).items()
    ]
S["gini_downloads_demand_models"] = gini(demand["downloads"].values)
S["top1pct_models_download_share"] = float(
    demand.nlargest(max(1, len(demand) // 100), "downloads")["downloads"].sum()
    / demand["downloads"].sum()
)
S["median_downloads_demand"] = float(demand["downloads"].median())
S["share_demand_models_under_100_dl"] = float((demand["downloads"] < 100).mean())

# ---------- top families table (demand universe) ----------
fam_d = (
    demand.groupby("family")
    .agg(root=("root", "first"), root_org=("root_org", "first"),
         n_models=("id", "count"), n_derivatives=("is_derivative", "sum"),
         downloads=("downloads", "sum"),
         downloadsAllTime=("downloadsAllTime", "sum"),
         likes=("likes", "sum"), max_depth=("depth", "max"))
    .reset_index()
    .sort_values("downloads", ascending=False)
)
topfam = fam_d.head(20).copy()
topfam["share_of_demand_downloads"] = topfam["downloads"] / demand["downloads"].sum()
S["top_families"] = topfam[
    ["family", "root_org", "n_models", "n_derivatives", "downloads",
     "downloadsAllTime", "likes", "max_depth", "share_of_demand_downloads"]
].to_dict("records")
S["n_families_demand"] = int(len(fam_d))
# for the top families: how much of the family total is the root itself
# vs its descendants?
own = demand.set_index("id")["downloads"]
fam_d["root_own_downloads"] = fam_d["root"].map(own).fillna(0).astype(int)
fam_d["descendant_downloads"] = fam_d["downloads"] - fam_d["root_own_downloads"]
S["top_families_root_split"] = fam_d.head(12)[
    ["family", "downloads", "root_own_downloads", "descendant_downloads", "n_models"]
].to_dict("records")
# org-level totals on the demand universe
org_tot = demand.groupby("root_org")["downloads"].sum().sort_values(ascending=False)
S["top_root_org_totals"] = [
    {"org": str(k), "downloads": int(v), "share": float(v / demand["downloads"].sum())}
    for k, v in org_tot.head(12).items()
]
qwen = demand[demand["root_org"] == "qwen"]
S["qwen_family_count_demand"] = int(qwen["family"].nunique())
S["qwen_download_share"] = float(qwen["downloads"].sum() / demand["downloads"].sum())
S["n_families_union"] = int(len(fam))
S["families_single_model_share"] = float((fam["n_models"] == 1).mean())

# ---------- depth ----------
S["depth_download_share"] = {
    str(k): float(v) for k, v in share_table(demand, "depth").items()
}
S["max_depth_demand"] = int(demand["depth"].max())
deep = demand[demand["depth"] >= 3].sort_values("downloads", ascending=False)
S["deep_examples"] = deep[["id", "root", "depth", "relation", "downloads"]].head(10).to_dict("records")

# ---------- vintage ----------
demand["cohort"] = np.where(demand["created_year"] <= 2022, "2022_or_earlier",
                             demand["created_year"].astype("Int64").astype(str))
S["vintage_download_share"] = {
    str(k): float(v) for k, v in share_table(demand, "cohort").items()
}
S["vintage_model_share"] = {
    str(k): float(v) for k, v in demand["cohort"].value_counts(normalize=True).items()
}
# downloads-weighted median creation date
dd = demand.sort_values("created")
cw = np.cumsum(dd["downloads"].values)
med_id = dd.iloc[int(np.searchsorted(cw, cw[-1] / 2))]["id"]
S["downloads_weighted_median_model"] = str(med_id)
S["downloads_weighted_median_created"] = str(
    demand.loc[demand["id"] == med_id, "createdAt"].iloc[0]
)
old = demand[demand["created_year"] <= 2022]
S["pre2023_share_of_downloads"] = float(old["downloads"].sum() / demand["downloads"].sum())
S["pre2023_share_of_models_demand"] = float(len(old) / len(demand))

# ---------- task mix ----------
S["task_download_share"] = {
    str(k): float(v) for k, v in share_table(demand, "pipeline_tag").head(12).items()
}
S["task_model_share_top"] = {
    str(k): float(v)
    for k, v in demand["pipeline_tag"].value_counts(normalize=True).head(12).items()
}
gen = demand[demand["pipeline_tag"] == "text-generation"]
S["text_generation_share_of_downloads"] = float(
    gen["downloads"].sum() / demand["downloads"].sum()
)
S["text_generation_share_of_models"] = float(len(gen) / len(demand))

# ---------- the firehose (newest cohort) ----------
S["newest_median_downloads"] = float(newest["downloads"].median())
S["newest_share_zero_downloads"] = float((newest["downloads"] == 0).mean())
S["newest_share_under_10_dl"] = float((newest["downloads"] < 10).mean())
S["newest_share_under_100_dl"] = float((newest["downloads"] < 100).mean())
S["newest_deriv_share_of_models"] = float(newest["is_derivative"].mean())
S["newest_share_zero_likes"] = float((newest["likes"] == 0).mean())
S["newest_top10_share_of_newest_downloads"] = float(
    newest.nlargest(10, "downloads")["downloads"].sum() / max(1, newest["downloads"].sum())
)

# ---------- attention vs usage ----------
both = demand[(demand["downloads"] > 0) & (demand["likes"] > 0)].copy()
both["dl_per_like"] = both["downloads"] / both["likes"]
S["corr_log_likes_log_downloads_demand"] = float(
    np.corrcoef(np.log10(both["likes"]), np.log10(both["downloads"]))[0, 1]
)
S["spearman_likes_downloads_demand"] = float(
    both["likes"].corr(both["downloads"], method="spearman")
)
S["share_demand_models_zero_likes"] = float((demand["likes"] == 0).mean())
infra = (
    both.groupby("pipeline_tag")
    .agg(n=("id", "count"), med_dl_per_like=("dl_per_like", "median"),
         downloads=("downloads", "sum"), likes=("likes", "sum"))
    .query("n >= 30")
    .sort_values("med_dl_per_like", ascending=False)
)
S["infrastructure_index_by_task"] = infra.reset().to_dict("records") if False else infra.reset_index().to_dict("records")
liked_top = liked.sort_values("likes", ascending=False).head(100)
S["top100_liked_share_also_top5000_downloaded"] = float(
    liked_top["samples"].str.contains("downloads").mean()
)

# ---------- first-party vs third-party derivatives ----------
dv = demand[demand["is_derivative"] == True].copy()  # noqa: E712
dv["third_party"] = dv["author"].str.lower() != dv["root_org"]
S["third_party_share_of_deriv_downloads"] = float(
    dv.loc[dv["third_party"], "downloads"].sum() / dv["downloads"].sum()
)
S["third_party_share_of_deriv_models"] = float(dv["third_party"].mean())
QUANT_RE = r"(gguf|awq|gptq|mlx|int4|int8|4bit|8bit|bnb|exl2|qat)"
dv["name_quant"] = dv["id"].str.lower().str.contains(QUANT_RE, regex=True)
S["name_quant_share_of_deriv_downloads"] = float(
    dv.loc[dv["name_quant"], "downloads"].sum() / dv["downloads"].sum()
)
S["name_quant_share_of_deriv_models"] = float(dv["name_quant"].mean())
# same-org derivative champions: manufacturers selling their own finetunes
fp = dv[~dv["third_party"]].groupby("root_org")["downloads"].sum().sort_values(ascending=False)
S["first_party_deriv_downloads_by_org"] = [
    {"org": str(k), "downloads": int(v)} for k, v in fp.head(8).items()
]
tp = dv[dv["third_party"]].groupby("author")["downloads"].sum().sort_values(ascending=False)
S["top_repackagers_by_downloads"] = [
    {"author": str(k), "downloads": int(v)} for k, v in tp.head(10).items()
]

# ---------- who manufactures: originals by org ----------
orig = demand[demand["is_derivative"] == False]  # noqa: E712
S["originals_top_orgs_by_downloads"] = [
    {"org": str(k), "share_of_original_downloads": float(v)}
    for k, v in share_table(orig, "author").head(12).items()
]
S["n_authors_demand"] = int(demand["author"].nunique())
S["n_authors_of_originals_demand"] = int(orig["author"].nunique())
S["n_root_orgs_demand"] = int(demand["root_org"].nunique())

with open(OUT, "w") as fh:
    json.dump(S, fh, indent=2, default=str)
print(json.dumps({k: v for k, v in S.items() if not isinstance(v, (list, dict))}, indent=2))
print(f"\nwrote {OUT}")
