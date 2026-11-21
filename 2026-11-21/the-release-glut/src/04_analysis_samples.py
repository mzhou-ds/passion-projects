"""HT-weighted analysis of the Discogs stratified samples.

For each cohort (genre, year), every sampled record gets an exact inclusion
probability from the leaf cells whose filters it matches (see
02_fetch_samples.py), and weight = 1/p. Population estimates are
Horvitz-Thompson weighted. Records are deduplicated by id within a cohort.

Also trains an XGBoost model on the pooled electronic sample to predict
log1p(collection velocity) = log1p(have / age_years), with SHAP importances.

Outputs: data/results_samples.json, data/sample_estimates.csv,
data/model_metrics.json, data/pooled_electronic.csv
"""
import json
import math
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
RAW = os.path.join(DATA, "raw")
SNAP_YEAR = 2026.89  # 2026-11-21

FORMATS = ["Vinyl", "File", "CD", "Cassette"]
FILE_DESCS = ["MP3", "WAV", "FLAC", "AIFF"]
COHORTS = [("electronic", y) for y in (2005, 2015, 2025)]
# NOTE: rock/pop control samples were dropped: the Discogs 10k-result cap
# makes their (format x country) cells un-samplable (rock Vinyl x US 2020
# alone exceeds 10,000). Genre comparison rests on the population counts.


# Discogs style search is hierarchical: querying a style returns records whose
# style is that style OR a sub-style of it (e.g. style=House returns
# Deep House, Electro House, ...). Verified: 0/900 sampled records returned
# by a style query lacked a style containing the query string. So a record
# matches a style cell if any of its styles contains the cell's style string.
# Two empirically verified exceptions (child NOT returned by the parent):
EXCLUSIONS = {("Power Electronics", "Electro"), ("Minimal Techno", "Techno")}


def cell_matches(cell_filters, rec):
    """Does this leaf cell's query filters match the record's attributes?"""
    f = cell_filters
    if "style" in f:
        q = f["style"]
        ok = False
        for s in rec.get("style", []):
            if (s, q) in EXCLUSIONS:
                continue
            if q.lower() in s.lower():
                ok = True
                break
        if not ok:
            return False
    if "format" in f and f["format"] not in rec.get("format", []):
        return False
    if "country" in f and f["country"] != rec.get("country"):
        return False
    return True


def load_cohort(genre, year):
    d = json.load(open(os.path.join(RAW, f"sample_{genre}_{year}.json")))
    cells = d["cells"]
    seen, rows = {}, []
    n_nomatch = 0
    for rec in d["results"]:
        rid = rec["id"]
        if rid in seen:
            continue
        seen[rid] = True
        # Inclusion prob per cell = 1 / npages (one uniform random page drawn
        # per cell). Using n/N instead is wrong when the last page is partial:
        # records on the (least popular) last page would be over-weighted.
        p_not = 1.0
        for c in cells:
            if cell_matches(c["filters"], rec):
                npages = math.ceil(c["total"] / 100)
                p_not *= (1.0 - 1.0 / npages)
        p = 1.0 - p_not
        if p <= 0:
            n_nomatch += 1
            continue
        r = {
            "id": rid, "genre": genre, "year": year,
            "title": rec.get("title", ""),
            "country": rec.get("country", "Unknown"),
            "labels": rec.get("label", []),
            "label1": (rec.get("label") or ["(none)"])[0],
            "format_list": rec.get("format", []),
            "first_format": (rec.get("formats") or [{}])[0].get("name", "Other"),
            "styles": rec.get("style", []),
            "n_styles": len(rec.get("style", [])),
            "have": rec.get("community", {}).get("have", 0),
            "want": rec.get("community", {}).get("want", 0),
            "master_id": rec.get("master_id", 0),
            "p_include": p, "weight": 1.0 / p,
        }
        r["age_years"] = SNAP_YEAR - (year + 0.5)
        r["have_per_year"] = r["have"] / r["age_years"]
        r["is_single"] = "Single" in r["format_list"]
        r["is_album"] = "Album" in r["format_list"]
        r["is_ep"] = "EP" in r["format_list"]
        r["has_master"] = 1 if r["master_id"] else 0
        rows.append(r)
    print(f"  {genre} {year}: {len(rows)} records kept, "
          f"{n_nomatch} dropped (match no cell)", flush=True)
    return pd.DataFrame(rows), d


def wmedian(vals, weights):
    v, w = np.array(vals, dtype=float), np.array(weights, dtype=float)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w)
    return float(v[np.searchsorted(cw, 0.5 * cw[-1])])


def wmean(vals, weights):
    return float(np.average(vals, weights=weights))


def wshare(mask, weights):
    m = np.array(mask, dtype=bool)
    w = np.array(weights, dtype=float)
    return float(w[m].sum() / w.sum())


def cohort_estimates(df, counts_total):
    w = df["weight"].values
    est = {
        "n_sample": int(len(df)),
        "weight_total": round(float(w.sum())),
        "weight_total_vs_genre": None,  # filled by caller
        "have_median": wmedian(df["have"], w),
        "have_mean": round(wmean(df["have"], w), 1),
        "have_p90": float(np.percentile(df["have"], 90)),
        "have_zero_pct": round(wshare(df["have"] == 0, w) * 100, 1),
        "have_le5_pct": round(wshare(df["have"] <= 5, w) * 100, 1),
        "have_ge100_pct": round(wshare(df["have"] >= 100, w) * 100, 1),
        "want_median": wmedian(df["want"], w),
        "want_have_ratio_median": round(float(np.median(
            df["want"] / np.maximum(df["have"], 1))), 2),
        "have_per_year_median": round(wmedian(df["have_per_year"], w), 2),
        "have_per_year_mean": round(wmean(df["have_per_year"], w), 2),
        "single_pct": round(wshare(df["is_single"], w) * 100, 1),
        "album_pct": round(wshare(df["is_album"], w) * 100, 1),
        "ep_pct": round(wshare(df["is_ep"], w) * 100, 1),
        "has_master_pct": round(wshare(df["has_master"] == 1, w) * 100, 1),
        "n_styles_mean": round(wmean(df["n_styles"], w), 2),
        "distinct_labels_sample": int(df["label1"].nunique()),
        "distinct_masters_sample": int((df.loc[df["master_id"] > 0, "master_id"]).nunique()),
        "masters_records": int((df["master_id"] > 0).sum()),
    }
    # format mix (weighted shares)
    fmt = df.groupby("first_format").apply(
        lambda g: g["weight"].sum(), include_groups=False)
    fmt = (fmt / fmt.sum() * 100).round(1).to_dict()
    est["format_mix_pct"] = {k: float(v) for k, v in fmt.items()}
    # file-description mix among File releases
    file_df = df[df["first_format"] == "File"]
    if len(file_df):
        descs = {}
        for d in FILE_DESCS:
            descs[d] = wshare(file_df["format_list"].apply(lambda fl: d in fl),
                             file_df["weight"])
        est["file_desc_mix_pct"] = {k: round(v * 100, 1) for k, v in descs.items()}
    # label concentration (primary label, weighted shares)
    lab = df.groupby("label1").apply(
        lambda g: g["weight"].sum(), include_groups=False)
    lab = lab / lab.sum()
    est["top10_label_share_pct"] = round(float(lab.nlargest(10).sum() * 100), 1)
    est["top1_label_share_pct"] = round(float(lab.max() * 100), 2)
    est["label_hhi"] = int(round(float((lab ** 2).sum() * 10000)))
    est["top_labels"] = {k: round(float(v * 100), 2)
                         for k, v in lab.nlargest(5).items()}
    # country mix
    cty = df.groupby("country").apply(
        lambda g: g["weight"].sum(), include_groups=False)
    cty = (cty / cty.sum() * 100).round(1)
    est["top_countries_pct"] = {k: float(v) for k, v in cty.nlargest(8).items()}
    # master duplication: share of SKUs that are extra variants of a sampled master
    m = df[df["master_id"] > 0]
    if len(m):
        dup = 1.0 - m["master_id"].nunique() / len(m)
        est["extra_variant_share_sample"] = round(float(dup), 3)
    # weighted median collectors by format (the mechanism behind the collapse)
    fmt_have = {}
    for fmt in ("Vinyl", "File", "CD", "CDr", "Cassette"):
        sub = df[df["first_format"] == fmt]
        if len(sub) >= 30:
            fmt_have[fmt] = {
                "n": int(len(sub)),
                "have_median": float(wmedian(sub["have"], sub["weight"])),
                "have_per_year_median": round(
                    float(wmedian(sub["have_per_year"], sub["weight"])), 2),
                "have_zero_pct": round(
                    float(wshare(sub["have"] == 0, sub["weight"]) * 100), 1),
            }
    est["format_have"] = fmt_have
    if counts_total:
        est["weight_total_vs_genre"] = round(float(w.sum() / counts_total), 3)
    return est


def main():
    counts = json.load(open(os.path.join(RAW, "discogs_counts.json")))
    manifest = json.load(open(os.path.join(RAW, "sample_cells.json")))
    all_est, frames = {}, {}
    pooled = []
    for genre, year in COHORTS:
        df, d = load_cohort(genre, year)
        frame_total = sum(c["total"] for c in d["cells"])
        est = cohort_estimates(df, counts[genre][str(year)])
        est["frame_total"] = frame_total
        est["genre_total"] = counts[genre][str(year)]
        all_est[f"{genre}_{year}"] = est
        print(f"{genre} {year}: n={len(df)} sumw={est['weight_total']:,} "
              f"(vs genre {counts[genre][str(year)]:,}) "
              f"have_med={est['have_median']} hpy_med={est['have_per_year_median']} "
              f"file={est['format_mix_pct'].get('File')} vinyl={est['format_mix_pct'].get('Vinyl')} "
              f"hhi={est['label_hhi']}", flush=True)
        if genre == "electronic":
            pooled.append(df)
    pooled = pd.concat(pooled, ignore_index=True)
    pooled.to_csv(os.path.join(DATA, "pooled_electronic.csv"), index=False)

    # ---- model: what predicts collection velocity? ----------------------
    import shap
    import xgboost as xgb
    from sklearn.model_selection import cross_val_score

    df = pooled.copy()
    # label prominence within cohort sample
    lab_counts = (df.groupby(["year", "label1"]).size()
                    .rename("label_n").reset_index())
    df = df.merge(lab_counts, on=["year", "label1"], how="left")
    df["label_n"] = df["label_n"].fillna(1)
    df["y"] = np.log1p(df["have_per_year"])
    df["country_group"] = df["country"].where(
        df["country"].isin(["UK", "US", "Germany", "Netherlands"]), "Other")
    df["country_group"] = df["country_group"].where(
        df["country"] != "Unknown", "Unknown")
    for s, col in [("House", "is_house"), ("Techno", "is_techno"),
                   ("Ambient", "is_ambient"), ("Experimental", "is_exp"),
                   ("Trance", "is_trance")]:
        df[col] = df["styles"].apply(lambda st: s in st).astype(int)
    feats = ["age_years", "year", "n_styles", "is_single", "is_album",
             "has_master", "label_n", "is_house", "is_techno", "is_ambient",
             "is_exp", "is_trance"]
    X = pd.get_dummies(df[feats + ["first_format", "country_group"]],
                       columns=["first_format", "country_group"],
                       drop_first=True).astype(float)
    model = xgb.XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, n_jobs=2)
    # HT weights, clipped at the 99th percentile so a few huge-weight
    # records do not dominate the fit.
    sw = df["weight"].clip(upper=df["weight"].quantile(0.99)).values
    from sklearn.metrics import r2_score
    from sklearn.model_selection import KFold
    kf = KFold(n_splits=5, shuffle=True, random_state=0)
    fold_r2 = []
    for tr, te in kf.split(X):
        m = xgb.XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, n_jobs=2)
        m.fit(X.iloc[tr], df["y"].iloc[tr], sample_weight=sw[tr])
        fold_r2.append(r2_score(df["y"].iloc[te], m.predict(X.iloc[te])))
    scores = np.array(fold_r2)
    model.fit(X, df["y"], sample_weight=sw)
    ex = shap.TreeExplainer(model)
    sv = ex.shap_values(X.sample(min(2000, len(X)), random_state=0))
    imp = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
    metrics = {
        "n": int(len(df)),
        "target": "log1p(have_per_year)",
        "cv_r2_mean": round(float(scores.mean()), 3),
        "cv_r2_std": round(float(scores.std()), 3),
        "shap_top": {k: round(float(v), 3) for k, v in imp.head(12).items()},
        "feature_columns": list(X.columns),
    }
    json.dump(metrics, open(os.path.join(DATA, "model_metrics.json"), "w"), indent=2)
    print(json.dumps(metrics, indent=2))

    # ---- style shares from manifest leaf totals -------------------------
    style_totals = {}
    for genre, year in COHORTS:
        if genre != "electronic":
            continue
        cells = manifest[f"{genre}_{year}"]
        st = {}
        for c in cells:
            s = c["filters"].get("style")
            if s:
                st[s] = st.get(s, 0) + c["total"]
        style_totals[str(year)] = st
    json.dump(style_totals, open(os.path.join(DATA, "style_totals_manifest.json"), "w"), indent=2)

    json.dump(all_est, open(os.path.join(DATA, "results_samples.json"), "w"), indent=2)
    rows = []
    for k, e in all_est.items():
        g, y = k.rsplit("_", 1)
        rows.append({"cohort": k, "genre": g, "year": int(y), **{
            kk: vv for kk, vv in e.items()
            if isinstance(vv, (int, float))}})
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "sample_estimates.csv"), index=False)
    print("DONE")


if __name__ == "__main__":
    main()
