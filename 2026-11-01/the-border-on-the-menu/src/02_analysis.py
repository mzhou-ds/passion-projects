"""Build the city x cuisine matrix from raw OSM dumps and run the border tests.

Inputs:  data/raw/osm_<city>.json (Overpass, tags only) + fetch_log.json
Outputs: data/city_cuisine.csv (shares), data/city_stats.csv,
         data/pairwise.csv, data/border_test.json, data/model.json,
         findings printed to stdout (also saved by the runner).
"""
import json, math, itertools
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
OUT = BASE / "data"
OUT.mkdir(parents=True, exist_ok=True)

CITIES = [
    ("vancouver", "CA", 49.25, -123.12), ("toronto", "CA", 43.72, -79.32),
    ("montreal", "CA", 45.57, -73.72), ("calgary", "CA", 51.05, -114.10),
    ("edmonton", "CA", 53.52, -113.52), ("ottawa", "CA", 45.40, -75.67),
    ("winnipeg", "CA", 49.87, -97.17), ("halifax", "CA", 44.66, -63.60),
    ("san-francisco", "US", 37.76, -122.44), ("los-angeles", "US", 34.15, -118.30),
    ("new-york", "US", 40.71, -73.98), ("seattle", "US", 47.61, -122.33),
    ("boston", "US", 42.34, -71.08), ("chicago", "US", 41.83, -87.68),
    ("houston", "US", 29.77, -95.54), ("portland", "US", 45.51, -122.61),
]

# Fine OSM cuisine values -> family. Anything unmapped stays its own family.
FAMILY = {
    "chinese": "chinese", "cantonese": "chinese", "sichuan": "chinese",
    "szechuan": "chinese", "szechwan": "chinese", "shanghainese": "chinese",
    "dim_sum": "chinese", "hot_pot": "chinese", "hunan": "chinese",
    "taiwanese": "chinese", "peking_duck": "chinese", "noodle": "chinese",
    "japanese": "japanese", "sushi": "japanese", "ramen": "japanese",
    "korean": "korean", "indian": "indian", "thai": "thai",
    "vietnamese": "vietnamese", "mexican": "mexican", "tex-mex": "mexican",
    "italian": "italian", "pizza": "italian", "pasta": "italian",
    "american": "american", "burger": "american", "steak_house": "american",
    "barbecue": "american", "canadian": "canadian", "poutine": "canadian",
    "french": "french", "mediterranean": "mediterranean", "greek": "mediterranean",
    "turkish": "mediterranean", "lebanese": "mediterranean",
    "seafood": "seafood", "sandwich": "sandwich", "breakfast": "breakfast",
    "coffee_shop": "cafe", "ice_cream": "dessert", "bakery": "bakery",
    "asian": "asian-generic", "fusion": "fusion", "international": "international",
    "german": "german", "spanish": "spanish", "portuguese": "portuguese",
    "ethiopian": "ethiopian", "moroccan": "moroccan", "caribbean": "caribbean",
    "filipino": "filipino", "malaysian": "malaysian", "indonesian": "indonesian",
    "nepalese": "indian", "pakistani": "indian", "sri_lankan": "indian",
    "persian": "persian", "afghan": "afghan", "russian": "russian",
    "ukrainian": "ukrainian", "polish": "polish", "irish": "irish",
    "british": "british", "vegetarian": "vegetarian", "vegan": "vegetarian",
}
CHINESE_REGIONAL = {"cantonese", "sichuan", "szechuan", "szechwan",
                    "shanghainese", "dim_sum", "hot_pot", "hunan",
                    "taiwanese", "peking_duck"}

def split_cuisines(tag):
    parts = []
    for chunk in str(tag).split(";"):
        for sub in chunk.split(","):
            v = sub.strip().lower().replace(" ", "_").replace("-", "_")
            if v:
                parts.append(v)
    return parts

def haversine(lat1, lon1, lat2, lon2):
    r = math.radians
    dlat, dlon = r(lat2 - lat1), r(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))

rows, fam_counts, raw_counts, stats = [], {}, {}, []
for slug, country, lat, lon in CITIES:
    p = RAW / f"osm_{slug}.json"
    els = json.loads(p.read_text())["elements"]
    fam, raw = {}, {}
    tagged = 0
    chinese_total, chinese_regional = 0, 0
    for el in els:
        tags = el.get("tags", {})
        c = tags.get("cuisine")
        if not c:
            continue
        tagged += 1
        vals = split_cuisines(c)
        for v in raw:
            pass
        for v in vals:
            raw[v] = raw.get(v, 0) + 1
        fams = {FAMILY.get(v, v) for v in vals}
        for f in fams:
            fam[f] = fam.get(f, 0) + 1
        if "chinese" in fams:
            chinese_total += 1
            if any(v in CHINESE_REGIONAL for v in vals):
                chinese_regional += 1
    fam_counts[slug] = fam
    raw_counts[slug] = raw
    total = len(els)
    shares = {f: n / tagged for f, n in fam.items()} if tagged else {}
    ent = -sum(s * math.log(s) for s in shares.values()) if shares else 0.0
    stats.append({"city": slug, "country": country, "lat": lat, "lon": lon,
                  "restaurants": total, "tagged": tagged,
                  "coverage": tagged / total if total else 0.0,
                  "distinct_families": len(fam),
                  "entropy": ent,
                  "chinese_share": shares.get("chinese", 0.0),
                  "chinese_n": chinese_total,
                  "chinese_regional_share": chinese_regional / chinese_total if chinese_total else float("nan")})
    for f, s in shares.items():
        rows.append({"city": slug, "country": country, "family": f, "share": s,
                     "n": fam[f]})

shares_df = pd.DataFrame(rows)
stats_df = pd.DataFrame(stats)
shares_df.to_csv(OUT / "city_cuisine.csv", index=False)
stats_df.to_csv(OUT / "city_stats.csv", index=False)

# Wide matrix over families present in >= 3 cities, for pairwise distances.
wide = shares_df.pivot_table(index="city", columns="family", values="share",
                             fill_value=0.0)
keep = [c for c in wide.columns if (wide[c] > 0).sum() >= 3]
W = wide[keep]
city_country = dict((s, c) for s, c, _, _ in CITIES)
city_xy = dict((s, (la, lo)) for s, _, la, lo in CITIES)

pairs = []
for a, b in itertools.combinations(W.index, 2):
    va, vb = W.loc[a].values, W.loc[b].values
    cos = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb))) if np.linalg.norm(va) and np.linalg.norm(vb) else 0.0
    la1, lo1 = city_xy[a]; la2, lo2 = city_xy[b]
    pairs.append({"city_a": a, "city_b": b,
                  "same_country": city_country[a] == city_country[b],
                  "cross_border": city_country[a] != city_country[b],
                  "km": haversine(la1, lo1, la2, lo2),
                  "cosine_distance": 1 - cos})
pair_df = pd.DataFrame(pairs)
pair_df.to_csv(OUT / "pairwise.csv", index=False)

# OLS: cosine_distance ~ km_z + cross_border, + permutation test on border coef.
import statsmodels.api as sm
X = pd.DataFrame({"km": pair_df["km"], "cross": pair_df["cross_border"].astype(float)})
X["km_z"] = (X["km"] - X["km"].mean()) / X["km"].std()
Xc = sm.add_constant(X[["km_z", "cross"]])
ols = sm.OLS(pair_df["cosine_distance"], Xc).fit()
rng = np.random.default_rng(7)
y = pair_df["cosine_distance"].values
perm = []
cross = X["cross"].values; kmz = X["km_z"].values
for _ in range(5000):
    pc = rng.permutation(cross)
    Xp = sm.add_constant(pd.DataFrame({"km_z": kmz, "cross": pc}))
    perm.append(sm.OLS(y, Xp).fit().params["cross"])
perm = np.array(perm)
p_perm = float((np.abs(perm) >= abs(ols.params["cross"])).mean())

# LOOCV country classifier from cuisine vectors (logistic, scaled).
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
Xv = W.values
yv = np.array([1 if city_country[c] == "CA" else 0 for c in W.index])
pred = []
for i in range(len(Xv)):
    m = np.ones(len(Xv), bool); m[i] = False
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    clf.fit(Xv[m], yv[m])
    pred.append(int(clf.predict(Xv[i:i + 1])[0]))
pred = np.array(pred)
acc = float((pred == yv).mean())
null_acc = []
for _ in range(2000):
    yp = rng.permutation(yv)
    pr = []
    for i in range(len(Xv)):
        m = np.ones(len(Xv), bool); m[i] = False
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        clf.fit(Xv[m], yp[m])
        pr.append(int(clf.predict(Xv[i:i + 1])[0]))
    null_acc.append(float((np.array(pr) == yp).mean()))
null_acc = np.array(null_acc)

# Country means for headline families.
fam_wide = shares_df.pivot_table(index="city", columns="family", values="share", fill_value=0.0)
fam_wide["country"] = [city_country[c] for c in fam_wide.index]
means = fam_wide.groupby("country").mean(numeric_only=True).T
means["ratio_ca_us"] = means["CA"] / means["US"].replace(0, np.nan)
means.to_csv(OUT / "family_country_means.csv")

result = {
    "n_cities": len(CITIES),
    "total_restaurants": int(stats_df["restaurants"].sum()),
    "total_tagged": int(stats_df["tagged"].sum()),
    "ols": {"cross_border_coef": float(ols.params["cross"]),
            "km_z_coef": float(ols.params["km_z"]),
            "const": float(ols.params["const"]),
            "r2": float(ols.rsquared), "p_perm_border": p_perm,
            "n_pairs": len(pair_df)},
    "loocv_country_accuracy": acc,
    "loocv_null_mean": float(null_acc.mean()),
    "loocv_null_p": float((null_acc >= acc).mean()),
    "entropy_ca_mean": float(stats_df[stats_df.country == "CA"]["entropy"].mean()),
    "entropy_us_mean": float(stats_df[stats_df.country == "US"]["entropy"].mean()),
    "chinese_specificity_ca": float(stats_df[stats_df.country == "CA"]["chinese_regional_share"].mean()),
    "chinese_specificity_us": float(stats_df[stats_df.country == "US"]["chinese_regional_share"].mean()),
    "families_kept": len(keep),
}
(OUT / "border_test.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
print("\n--- city stats ---")
print(stats_df.to_string(index=False))
print("\n--- CA/US family means (top by CA share) ---")
print(means.sort_values("CA", ascending=False).head(25).round(4).to_string())
