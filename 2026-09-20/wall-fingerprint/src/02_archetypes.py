"""02_archetypes.py — cluster normalized pacing profiles into archetypes.

Features: rel0..rel9 = per-5k-segment pace / runner's own average pace
(1.0 = even, >1 = slower than average). k-means over finishers, then
characterize clusters by finish-time tier, sex, and year.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

SEG_LABELS = ["0-5k", "5-10k", "10-15k", "15-20k", "20-25k",
              "25-30k", "30-35k", "35-40k", "40-42.2k"]
REL = [f"rel{i}" for i in range(9)]

df = pd.read_pickle("output/berlin_clean.pkl")
print("n =", len(df))
X = df[REL].values

# choose k
rng = np.random.RandomState(7)
sample = X[rng.choice(len(X), 40000, replace=False)]
for k in (4, 5, 6):
    km = KMeans(n_clusters=k, n_init=5, random_state=7).fit(sample)
    print(f"k={k} silhouette={silhouette_score(sample, km.labels_):.4f}")

K = 5
km = KMeans(n_clusters=K, n_init=10, random_state=7).fit(X)
df["cluster"] = km.labels_
cent = pd.DataFrame(km.cluster_centers_, columns=REL)

# name clusters from centroid shape
# hand-labeled from centroid shapes (stable: random_state=7)
names = {1: "Metronome", 2: "The Fade", 0: "The Wall",
         3: "The Crash", 4: "The Collapse"}
print(names)
df["archetype"] = df["cluster"].map(names)

# ---- chart 1: centroid profiles
fig, ax = plt.subplots(figsize=(10, 6))
for c in range(K):
    ax.plot(SEG_LABELS, cent.loc[c].values, marker="o", label=names[c])
ax.axhline(1.0, color="k", lw=0.8, ls="--")
ax.set_ylabel("Segment pace ÷ own average pace")
ax.set_title("Pacing archetypes — Berlin Marathon 2016–2019 (n=158,674)")
ax.legend()
plt.xticks(rotation=25)
plt.tight_layout()
plt.savefig("charts/01_archetypes.png", dpi=130)
plt.close()

# ---- composition table
df["tier"] = pd.cut(df["time_full_s"] / 3600,
                    [2, 3, 3.5, 4, 4.5, 8],
                    labels=["sub-3", "3–3:30", "3:30–4", "4–4:30", "4:30+"])
ct = pd.crosstab(df["archetype"], df["tier"], normalize="columns").round(3) * 100
print("\narchetype share by finish tier (%):")
print(ct.round(1).to_string())
cg = pd.crosstab(df["archetype"], df["gender"], normalize="columns").round(3) * 100
print("\narchetype share by sex (%):")
print(cg.round(1).to_string())
overall = df["archetype"].value_counts(normalize=True).round(4) * 100
print("\noverall (%):"); print(overall.round(1).to_string())

# median finish time per archetype
med = df.groupby("archetype")["time_full_s"].median() / 60
print("\nmedian finish (min):"); print(med.round(1).sort_values().to_string())

# bonk flag: avg pace over 30-42.195k vs avg pace over 0-30k

df.to_pickle("output/berlin_archetypes.pkl")
cent.to_csv("output/centroids.csv")
json.dump(names, open("output/archetype_names.json", "w"), indent=1)
ct.round(1).to_csv("output/archetype_by_tier.csv")
cg.round(1).to_csv("output/archetype_by_sex.csv")
