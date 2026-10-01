"""Hidden sugar in the savory aisle + claim-stacking analysis.

1. Rank main categories (>=80 products) by median sugar per 100g. Tag each
   category sweet/savory/other via keyword rules, then surface the most
   sugary SAVORY categories — dessert-level sugar where shoppers don't
   expect it.
2. Claim stacking: mean nutri_points / UPF share by number of front-of-pack
   claims. Does piling on labels buy you anything?

Outputs: charts/hidden_sugar.png, charts/claim_stacking.png,
         output/hidden_sugar.csv, output/claim_stacking.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})

SAVORY_CATS = ["soup", "bread", "cracker", "pasta", "noodle", "sauce", "dressing",
                "condiment", "ketchup", "mayonnaise", "marinade", "stock", "broth",
                "ready-meal", "frozen-meal", "pizza", "sandwich", "meat", "sausage",
                "cheese", "chip", "popcorn", "peanut-butter", "hummus", "salsa",
                "tortilla", "rice-cake"]


def is_savory(cat):
    c = (cat or "").lower()
    return any(h in c for h in SAVORY_CATS)


def main():
    df = pd.read_parquet("data/products.parquet")
    # physically impossible values are transcription errors
    df.loc[df["sugars_100g"] > 100, "sugars_100g"] = None

    # --- 1. hidden sugar ---
    g = df[df["sugars_100g"].notna() & df["main_category"].notna()].groupby("main_category")
    stats = g["sugars_100g"].agg(["median", "count"]).reset_index()
    stats = stats[(stats["count"] >= 80) & stats["main_category"].apply(is_savory)].copy()
    stats = stats.sort_values("median", ascending=False)
    stats.to_csv("output/hidden_sugar.csv", index=False)

    top = stats.head(15)
    print("Most sugary SAVORY categories (median g sugar / 100g):")
    print(top[["main_category", "median", "count"]].to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(top))
    ax.barh(y, top["median"], color="#d62728", alpha=0.85)
    for i, v in enumerate(top["median"]):
        ax.text(v + 0.2, i, f"{v:.1f}g", va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("-", " ") for c in top["main_category"]])
    ax.set_xlabel("Median sugar per 100g (g)")
    ax.set_title("Dessert-level sugar, savory packaging: the sweetest 'savory' categories",
                 fontsize=11, weight="bold")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig("charts/hidden_sugar.png", bbox_inches="tight")
    plt.close(fig)

    # spot check: worst offenders in the single sweetest savory category
    worst_cat = top.iloc[0]["main_category"]
    worst = df[(df["main_category"] == worst_cat) & df["sugars_100g"].notna()].nlargest(
        5, "sugars_100g")[["product_name", "brands", "sugars_100g"]]
    print(f"\nSugariest products in '{worst_cat}':")
    print(worst.to_string(index=False))

    # --- 2. claim stacking ---
    d = df[df["nutri_points"].notna()].copy()
    stack = d.groupby("n_claims").agg(
        nutri_points=("nutri_points", "mean"),
        upf_share=("is_upf", "mean"),
        n=("nutri_points", "count")).reset_index()
    stack = stack[stack["n"] >= 100]
    stack.to_csv("output/claim_stacking.csv", index=False)
    print("\nClaim stacking:")
    print(stack.round(3).to_string(index=False))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5))
    a1.plot(stack["n_claims"], stack["nutri_points"], marker="o", color="#2ca02c")
    a1.set_xlabel("Number of front-of-pack claims")
    a1.set_ylabel("Mean Nutri-Score points (5 = best)")
    a1.set_title("More labels, better food?", weight="bold")
    a1.grid(alpha=0.3)
    a2.plot(stack["n_claims"], stack["upf_share"] * 100, marker="o", color="#d62728")
    a2.set_xlabel("Number of front-of-pack claims")
    a2.set_ylabel("% ultra-processed (NOVA 4)")
    a2.set_title("Or more labels, more processing?", weight="bold")
    a2.grid(alpha=0.3)
    fig.suptitle("Claim stacking: what each extra label actually buys you", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig("charts/claim_stacking.png", bbox_inches="tight")
    plt.close(fig)
    print("charts written")


if __name__ == "__main__":
    main()
