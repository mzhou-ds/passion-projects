"""Part 1: Cluster NHL forward lines by 5v5 style (MoneyPuck lines.csv, 2023-2025).

Question: what *kind* of line is the McDavid line? Group every regular NHL
line by its on-ice fingerprint, then locate Edmonton's top units.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

RAW = "data/raw"
SEASONS = [2023, 2024, 2025]  # 2023-24, 2024-25, 2025-26
MIN_TOI_SEC = 7500            # ~125 min 5v5 together

def load_lines():
    frames = []
    for s in SEASONS:
        df = pd.read_csv(f"{RAW}/mp_{s}_lines.csv")
        df = df[df["situation"] == "5on5"].copy()
        # forward lines only: D-pairs have exactly one hyphen ("Ekholm-Bouchard");
        # trios have 2+ ("Donato-Bedard-Mikheyev", "Hyman-Mcdavid-Nugent-Hopkins")
        df = df[df["name"].str.count("-") >= 2].copy()
        df["season_label"] = s
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def feat(df):
    d = df.copy()
    d = d[d["icetime"] >= MIN_TOI_SEC].copy()
    hrs = d["icetime"] / 3600.0
    d["xGF60"]  = d["xGoalsFor"] / hrs
    d["xGA60"]  = d["xGoalsAgainst"] / hrs
    d["SOGF60"] = d["shotsOnGoalFor"] / hrs
    d["HDF60"]  = d["highDangerShotsFor"] / hrs
    d["HITS60"] = d["hitsFor"] / hrs
    d["TK60"]   = d["takeawaysFor"] / hrs
    d["GV60"]   = d["giveawaysFor"] / hrs
    d["FINISH"] = d["goalsFor"] / d["xGoalsFor"].replace(0, np.nan)
    d["FOshare"] = d["faceOffsWonFor"] / (d["faceOffsWonFor"] + d["faceOffsWonAgainst"]).replace(0, np.nan)
    d["NETPEN60"] = (d["penaltiesFor"] - d["penaltiesAgainst"]) / hrs
    d["xGshare"] = d["xGoalsPercentage"]
    d["corsi"] = d["corsiPercentage"]
    d = d.dropna(subset=["FINISH", "FOshare"])
    # cap extreme finishing outliers (luck tails)
    d["FINISH"] = d["FINISH"].clip(0.4, 1.8)
    return d

FEATS = ["xGF60","xGA60","SOGF60","HDF60","HITS60","TK60","GV60",
         "FINISH","FOshare","NETPEN60","xGshare","corsi"]

def main():
    df = feat(load_lines())
    print(f"lines with >={MIN_TOI_SEC/60:.0f} min 5v5: {len(df)}")
    X = StandardScaler().fit_transform(df[FEATS])

    print("k  silhouette")
    best = None
    for k in range(4, 9):
        km = KMeans(n_clusters=k, n_init=20, random_state=11)
        lab = km.fit_predict(X)
        s = silhouette_score(X, lab)
        print(f"{k}  {s:.3f}")
        if best is None or s > best[1]:
            best = (k, s, km, lab)
    k, s, km, lab = best
    print(f"chosen k={k} (silhouette {s:.3f})")
    df["cluster"] = lab

    centers = pd.DataFrame(km.cluster_centers_, columns=FEATS)
    centers_raw = pd.DataFrame(
        StandardScaler().fit(df[FEATS]).inverse_transform(km.cluster_centers_),
        columns=FEATS)
    print(centers_raw.round(2).to_string())

    # hand-name archetypes from centroid profile (edited after inspection)
    df.to_csv("data/processed/lines_clustered.csv", index=False)
    centers_raw.to_csv("data/processed/line_cluster_centers.csv")

    # --- figure: PCA scatter, EDM lines annotated ---
    pca = PCA(n_components=2, random_state=11).fit(X)
    P = pca.transform(X)
    fig, ax = plt.subplots(figsize=(11, 7))
    sc = ax.scatter(P[:,0], P[:,1], c=lab, cmap="tab10", s=14, alpha=0.55)
    edm = df[df["team"] == "EDM"].sort_values("icetime", ascending=False).head(12)
    Pe = pca.transform(StandardScaler().fit(df[FEATS]).transform(edm[FEATS]))
    ax.scatter(Pe[:,0], Pe[:,1], c="none", edgecolors="black", s=90, linewidths=1.4, zorder=5)
    for (x, y), nm, cl in zip(Pe, edm["name"], edm["cluster"]):
        ax.annotate(f"{nm}\n(c{cl})", (x, y), fontsize=7,
                    xytext=(6, 6), textcoords="offset points")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.0%} var)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.0%} var)")
    ax.set_title("NHL forward lines by 5v5 style, 2023-24 to 2025-26 (MoneyPuck)\n"
                 "k-means on per-60 rates; Edmonton top lines circled")
    fig.colorbar(sc, ax=ax, label="cluster")
    fig.tight_layout()
    fig.savefig("figures/01_line_clusters.png", dpi=130)
    print("saved figures/01_line_clusters.png")

    # --- where do McDavid lines live? ---
    mcd = df[df["name"].str.contains("mcdavid", case=False, na=False)].sort_values("icetime", ascending=False)
    print("\nMcDavid lines:")
    print(mcd[["season_label","name","team","icetime","xGF60","xGA60","xGshare","cluster"]]
          .to_string(index=False, float_format="%.2f"))
    print("\nEDM top-10 lines by TOI:")
    print(edm[["season_label","name","icetime","xGF60","xGA60","xGshare","cluster"]]
          .to_string(index=False, float_format="%.2f"))

if __name__ == "__main__":
    main()
