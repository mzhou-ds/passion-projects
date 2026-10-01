"""Can you read ultra-processing off the nutrition label? Predict NOVA from nutrients.

Model: XGBoost multiclass (NOVA 1-4) on the 10 per-100g nutrients + energy.
Stratified 80/20 split, class-weighted. Report accuracy, macro-F1, confusion
matrix, and SHAP importances. Baseline: majority-class and logistic regression.

Second question: are 'health-halo' products (many claims) harder to classify —
i.e., does the label hide the processing?

Outputs: charts/nova_confusion.png, charts/shap_importance.png,
         output/nova_model.json, output/shap_values.csv
"""
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import shap

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})

FEATURES = ["energy_kcal_100g", "proteins_100g", "carbohydrates_100g", "sugars_100g",
            "fat_100g", "saturated_fat_100g", "fiber_100g", "sodium_100g"]
PRETTY = {
    "energy_kcal_100g": "Energy (kcal)", "proteins_100g": "Protein",
    "carbohydrates_100g": "Carbs", "sugars_100g": "Sugars",
    "fat_100g": "Fat", "saturated_fat_100g": "Saturated fat",
    "fiber_100g": "Fiber", "sodium_100g": "Sodium",
}


def main():
    df = pd.read_parquet("data/products.parquet")
    d = df[df["nova_group"].isin([1, 2, 3, 4]) & df[FEATURES].notna().all(axis=1)].copy()
    d["nova"] = d["nova_group"].astype(int) - 1  # 0..3
    X = d[FEATURES].to_numpy()
    y = d["nova"].to_numpy()
    print(f"model rows: {len(d):,}  class balance: {np.bincount(y) / len(y)}")

    Xtr, Xte, ytr, yte, dtr, dte = train_test_split(
        X, y, d.index, test_size=0.2, random_state=7, stratify=y)
    dte = df.loc[dte]

    maj = np.bincount(ytr).argmax()
    maj_acc = accuracy_score(yte, np.full_like(yte, maj))

    sc = StandardScaler().fit(Xtr)
    lr = LogisticRegression(max_iter=2000, class_weight="balanced")
    lr.fit(sc.transform(Xtr), ytr)
    lr_acc = accuracy_score(yte, lr.predict(sc.transform(Xte)))

    w = len(ytr) / (4 * np.bincount(ytr))
    xgb = XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                        subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
                        n_jobs=-1, random_state=7, eval_metric="mlogloss")
    xgb.fit(Xtr, ytr, sample_weight=w[ytr])
    pred = xgb.predict(Xte)
    acc = accuracy_score(yte, pred)
    f1 = f1_score(yte, pred, average="macro")
    print(f"majority baseline acc={maj_acc:.3f} | logistic acc={lr_acc:.3f} | "
          f"xgboost acc={acc:.3f} macro-F1={f1:.3f}")

    cm = confusion_matrix(yte, pred, normalize="true")
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cm[i, j]:.2f}", ha="center", va="center",
                    color="white" if cm[i, j] > 0.5 else "black", fontsize=11)
    ax.set_xticks(range(4), ["NOVA 1", "NOVA 2", "NOVA 3", "NOVA 4"])
    ax.set_yticks(range(4), ["NOVA 1", "NOVA 2", "NOVA 3", "NOVA 4"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Reading processing off the label: NOVA prediction\nfrom nutrition facts alone (row-normalized)", fontsize=11, weight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig("charts/nova_confusion.png", bbox_inches="tight")
    plt.close(fig)

    # SHAP
    explainer = shap.TreeExplainer(xgb)
    sv = explainer.shap_values(Xte[:4000])
    sv = np.array(sv)  # (n, features, classes)
    mean_abs = np.abs(sv).mean(axis=(0, 2))
    order = np.argsort(mean_abs)[::-1]
    imp = pd.DataFrame({"feature": [PRETTY[FEATURES[i]] for i in order],
                        "mean_abs_shap": mean_abs[order]})
    imp.to_csv("output/shap_importance.csv", index=False)
    print(imp.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(imp["feature"][::-1], imp["mean_abs_shap"][::-1], color="#1f77b4", alpha=0.85)
    ax.set_xlabel("Mean |SHAP value| (impact on NOVA class prediction)")
    ax.set_title("What gives away ultra-processing on a nutrition label?", fontsize=11, weight="bold")
    fig.tight_layout()
    fig.savefig("charts/shap_importance.png", bbox_inches="tight")
    plt.close(fig)

    # class-4 (UPF) precision/recall detail
    upf_pred = (pred == 3)
    upf_true = (yte == 3)
    prec = (upf_pred & upf_true).sum() / upf_pred.sum()
    rec = (upf_pred & upf_true).sum() / upf_true.sum()

    # are high-claim products harder to classify?
    dte = dte.copy()
    dte["pred"] = xgb.predict(dte[FEATURES].to_numpy())
    dte["true"] = dte["nova_group"].astype(int) - 1
    dte["correct"] = (dte["pred"] == dte["true"]).astype(int)
    by_claims = dte.groupby("n_claims")["correct"].agg(["mean", "count"])
    by_claims = by_claims[by_claims["count"] >= 200]
    print("\naccuracy by # of front-of-pack claims:")
    print(by_claims.round(3).to_string())

    json.dump({
        "n": int(len(d)), "majority_acc": round(float(maj_acc), 4),
        "logistic_acc": round(float(lr_acc), 4),
        "xgb_acc": round(float(acc), 4), "xgb_macro_f1": round(float(f1), 4),
        "upf_precision": round(float(prec), 4), "upf_recall": round(float(rec), 4),
        "acc_by_n_claims": {str(k): round(float(v), 4) for k, v in by_claims["mean"].items()},
    }, open("output/nova_model.json", "w"), indent=2)
    print("done")


if __name__ == "__main__":
    main()
