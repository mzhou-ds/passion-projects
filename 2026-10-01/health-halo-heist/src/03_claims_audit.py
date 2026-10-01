"""The health-halo audit: do front-of-pack claims predict better nutrition?

Design: for each claim, compare claimed vs unclaimed products WITHIN the same
main category (controls for category mix — e.g. 'gluten-free' skews toward
snacks). For categories with >=25 claimed and >=25 unclaimed products,
compute the median difference (claimed - unclaimed) in:
  - nutri_points (Nutri-Score a=5..e=1; higher = better)
  - is_upf (share NOVA 4; lower = better)
  - sugars / sodium / saturated fat per 100g
Aggregate across categories weighted by # claimed products. Report weighted
mean delta + 95% CI (normal approx on category-level deltas).
Also: raw (unmatched) deltas for the "what a shopper sees" view.

Outputs: charts/claims_effect.png, charts/upf_share.png, output/claims_audit.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})

CLAIM_LABELS = {
    "claim_organic": "Organic",
    "claim_gluten_free": "Gluten-free",
    "claim_high_protein": "High protein",
    "claim_low_fat": "Low fat",
    "claim_low_sugar": "Low/no sugar",
    "claim_natural": "Natural",
    "claim_whole_grain": "Whole grain",
    "claim_keto": "Keto",
    "claim_paleo": "Paleo",
    "claim_low_calorie": "Low calorie",
    "claim_non_gmo": "Non-GMO",
    "claim_vegan": "Vegan",
    "claim_high_fiber": "High fiber",
    "claim_clean_label": "No artificial",
    "claim_heart_healthy": "Heart healthy",
    "claim_low_sodium": "Low sodium",
}
METRICS = ["nutri_points", "is_upf", "sugars_100g", "sodium_100g", "saturated_fat_100g"]
MIN_N = 10
MIN_CATS = 5
JUNK_CATS = {"undefined", "null", "none", ""}


def main():
    df = pd.read_parquet("data/products.parquet")
    df = df[df["main_category"].notna() & ~df["main_category"].isin(JUNK_CATS)].copy()
    results = []
    for claim, label in CLAIM_LABELS.items():
        claimed = df[df[claim]]
        if len(claimed) < 100:
            continue
        deltas, weights, n_cats = [], [], 0
        for cat, g in df.groupby("main_category"):
            gc = g[g[claim]]
            gu = g[~g[claim]]
            if len(gc) < MIN_N or len(gu) < MIN_N:
                continue
            n_cats += 1
            w = len(gc)
            d = {}
            for m in METRICS:
                a = gc[m].dropna()
                b = gu[m].dropna()
                d[m] = (a.median() - b.median()) if len(a) > 10 and len(b) > 10 else np.nan
            deltas.append(d)
            weights.append(w)
        if not deltas or len(deltas) < MIN_CATS:
            continue
        dd = pd.DataFrame(deltas)
        w = np.array(weights, dtype=float)
        w = w / w.sum()
        row = {"claim": label, "n_claimed": len(claimed), "n_categories": n_cats}
        for m in METRICS:
            v = dd[m].to_numpy(dtype=float)
            mask = ~np.isnan(v)
            if mask.sum() < 3:
                row[m + "_delta"] = np.nan
                row[m + "_ci"] = np.nan
                continue
            vv, ww = v[mask], w[mask]
            ww = ww / ww.sum()
            mean = float(np.sum(vv * ww))
            # weighted variance of category deltas
            var = float(np.sum(ww * (vv - mean) ** 2))
            ci = 1.96 * np.sqrt(var / mask.sum())
            row[m + "_delta"] = mean
            row[m + "_ci"] = ci
        # raw unmatched delta for context
        gu_all = df[~df[claim]]
        row["raw_nutri_delta"] = claimed["nutri_points"].median() - gu_all["nutri_points"].median()
        row["raw_upf_delta"] = claimed["is_upf"].mean() - gu_all["is_upf"].mean()
        results.append(row)

    res = pd.DataFrame(results).sort_values("n_claimed", ascending=False)
    res.to_csv("output/claims_audit.csv", index=False)
    print(res[["claim", "n_claimed", "n_categories", "nutri_points_delta", "is_upf_delta"]].to_string(index=False))

    # --- chart 1: matched nutri-score delta per claim ---
    plot = res.dropna(subset=["nutri_points_delta"]).sort_values("nutri_points_delta")
    fig, ax = plt.subplots(figsize=(9, 6.5))
    y = np.arange(len(plot))
    ax.barh(y, plot["nutri_points_delta"], xerr=plot["nutri_points_ci"],
            color=["#2ca02c" if v > 0 else "#d62728" for v in plot["nutri_points_delta"]],
            ecolor="black", capsize=3, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["claim"])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Matched Nutri-Score advantage of claimed products\n(median claimed − median unclaimed, same category; + = claimed is healthier)")
    ax.set_title("The health-halo audit: does the claim survive a fair comparison?", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig("charts/claims_effect.png", bbox_inches="tight")
    plt.close(fig)

    # --- chart 2: ultra-processed share ---
    plot2 = res.dropna(subset=["is_upf_delta"]).sort_values("is_upf_delta")
    fig, ax = plt.subplots(figsize=(9, 6.5))
    y = np.arange(len(plot2))
    ax.barh(y, plot2["is_upf_delta"] * 100, xerr=plot2["is_upf_ci"] * 100,
            color=["#2ca02c" if v < 0 else "#d62728" for v in plot2["is_upf_delta"]],
            ecolor="black", capsize=3, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(plot2["claim"])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Extra ultra-processed share among claimed products (percentage points, category-matched)")
    ax.set_title("Which 'healthy' labels hide the most ultra-processed food?", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig("charts/upf_share.png", bbox_inches="tight")
    plt.close(fig)
    print("charts written")


if __name__ == "__main__":
    main()
