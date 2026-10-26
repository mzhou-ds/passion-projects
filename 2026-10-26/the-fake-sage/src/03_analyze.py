"""Analysis: how much of the quotation canon is fake, whose fakes are worst,
and do the fakes speak a different dialect than the real thing?

Labels come from Wikiquote's own editorial buckets:
  fake    = disputed + misattributed
  sourced = quotes tied to a named work / verifiable source
  unsourced ('Attributed') is tracked separately as a provenance gap.
"""
import json, math, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261026)

# --- frozen lexicons (declared before looking at group differences) --------
THERAPY = set("""heal healing healed journey inner happiness happy positive energy
universe manifest gratitude grateful mindful mindfulness breathe breath dream dreams
soul heart love yourself self believe fearless pain suffering joy joyful peace peaceful
kindness gentle spirit growth grow blossom bloom shine light darkness wound wounds
trauma worthy enough brave courage smile laugh tears cry emotion emotions feel feelings""".split())
NATURE = set("""river water ocean sea mountain tree trees flower flowers wind rain snow
earth sky sun moon star stars stone rock forest garden seed seeds root roots leaf leaves
bird birds fish spring winter summer autumn season seasons nature valley cloud clouds""".split())
GOVERN = set("""king kings ruler rulers rule ruled empire state nation nations war wars
army soldier soldiers enemy enemies law laws judge justice power throne crown kingdom
govern government lord lords master slave slaves freedom liberty tyrant battle sword""".split())
SECOND = {"you", "your", "yours", "yourself", "yourselves", "thou", "thee", "thy", "thine"}
FIRST = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}
WORD = re.compile(r"[a-z']+")

def features(text: str) -> dict:
    toks = WORD.findall(text.lower())
    n = max(len(toks), 1)
    per = lambda s: 1000.0 * sum(t in s for t in toks) / n
    return {
        "words": len(toks),
        "second_person_per_k": per(SECOND),
        "first_person_per_k": per(FIRST),
        "therapy_per_k": per(THERAPY),
        "nature_per_k": per(NATURE),
        "govern_per_k": per(GOVERN),
        "questions": text.count("?"),
        "exclamations": text.count("!"),
        "modern_i": 1.0 if re.search(r"\bi\b", text) else 0.0,  # capital-I standalone in cleaned text
    }

def permutation_p(a, b, n_iter=20000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = abs(a.mean() - b.mean())
    pool = np.concatenate([a, b])
    hits = 0
    for _ in range(n_iter):
        rng.shuffle(pool)
        if abs(pool[: len(a)].mean() - pool[len(a):].mean()) >= obs:
            hits += 1
    return (hits + 1) / (n_iter + 1)

def main():
    df = pd.read_csv(ROOT / "data" / "quotes.csv")
    feats = pd.DataFrame([features(t) for t in df["text"]])
    df = pd.concat([df, feats], axis=1)
    df.to_csv(ROOT / "data" / "quotes_features.csv", index=False)

    log = json.loads((ROOT / "data" / "raw" / "fetch_log.json").read_text(encoding="utf-8"))
    views = {e["name"]: e["pageviews"].get("2024", 0) for e in log}

    # ---- per-thinker table -------------------------------------------------
    rows = []
    for (name, trad), g in df.groupby(["thinker", "tradition"]):
        c = g["status"].value_counts().to_dict()
        s, d, m, u = (c.get(k, 0) for k in ("sourced", "disputed", "misattributed", "unsourced"))
        checked = s + d + m
        rows.append({
            "thinker": name, "tradition": trad, "sourced": s, "disputed": d,
            "misattributed": m, "unsourced": u, "total": len(g),
            "fake_share_checked": (d + m) / checked if checked else None,
            "unverified_share_all": (d + m + u) / len(g) if len(g) else None,
            "pageviews_2024": views.get(name, 0),
        })
    per = pd.DataFrame(rows).sort_values("fake_share_checked", ascending=False)
    per.to_csv(ROOT / "data" / "per_thinker.csv", index=False)

    out = {"n_quotes": int(len(df)), "n_thinkers": int(df.thinker.nunique())}
    tot = df["status"].value_counts().to_dict()
    out["status_totals"] = {k: int(v) for k, v in tot.items()}
    checked = tot.get("sourced", 0) + tot.get("disputed", 0) + tot.get("misattributed", 0)
    out["pooled_fake_share_checked"] = (tot.get("disputed", 0) + tot.get("misattributed", 0)) / checked
    out["pooled_unverified_share_all"] = 1 - tot.get("sourced", 0) / len(df)
    out["per_thinker"] = per.to_dict("records")

    # ---- fame vs fake share -------------------------------------------------
    sub = per.dropna(subset=["fake_share_checked"])
    rho, p = stats.spearmanr(sub["pageviews_2024"], sub["fake_share_checked"])
    out["fame_vs_fake"] = {"spearman_rho": float(rho), "p": float(p), "n": int(len(sub))}
    rho2, p2 = stats.spearmanr(sub["pageviews_2024"], sub["unverified_share_all"])
    out["fame_vs_unverified"] = {"spearman_rho": float(rho2), "p": float(p2), "n": int(len(sub))}

    # ---- east vs west --------------------------------------------------------
    ew = {}
    for trad in ("east", "west"):
        t = per[per.tradition == trad]
        ew[trad] = {"median_fake_share": float(t.fake_share_checked.median()),
                    "mean_fake_share": float(t.fake_share_checked.mean()),
                    "median_unverified": float(t.unverified_share_all.median()),
                    "n_thinkers": int(len(t))}
    out["east_west"] = ew
    out["east_west_fake_p"] = permutation_p(
        per[per.tradition == "east"].fake_share_checked.dropna(),
        per[per.tradition == "west"].fake_share_checked.dropna())
    out["east_west_unverified_p"] = permutation_p(
        per[per.tradition == "east"].unverified_share_all.dropna(),
        per[per.tradition == "west"].unverified_share_all.dropna())

    # ---- dialect: fake vs sourced language -----------------------------------
    lab = df[df.status.isin(["sourced", "disputed", "misattributed"])].copy()
    lab["fake"] = lab.status.isin(["disputed", "misattributed"]).astype(int)
    feat_cols = ["words", "second_person_per_k", "first_person_per_k", "therapy_per_k",
                 "nature_per_k", "govern_per_k", "questions", "exclamations"]
    dialect = {}
    for c in feat_cols:
        a = lab[lab.fake == 1][c]; b = lab[lab.fake == 0][c]
        # Cohen's d
        sd = math.sqrt((a.var() * (len(a) - 1) + b.var() * (len(b) - 1)) / (len(a) + len(b) - 2))
        dialect[c] = {"fake_mean": float(a.mean()), "sourced_mean": float(b.mean()),
                      "fake_median": float(a.median()), "sourced_median": float(b.median()),
                      "cohens_d": float((a.mean() - b.mean()) / sd) if sd else None,
                      "mannwhitney_p": float(stats.mannwhitneyu(a, b).pvalue)}
    out["dialect"] = dialect

    # thinker-level paired test (each thinker with >=3 fakes): therapy density
    paired = []
    for name, g in lab.groupby("thinker"):
        f, s = g[g.fake == 1], g[g.fake == 0]
        if len(f) >= 3 and len(s) >= 10:
            paired.append({"thinker": name,
                           "therapy_diff": float(f.therapy_per_k.mean() - s.therapy_per_k.mean()),
                           "second_diff": float(f.second_person_per_k.mean() - s.second_person_per_k.mean()),
                           "words_ratio": float(f.words.median() / max(s.words.median(), 1))})
    out["paired_thinkers"] = paired
    if len(paired) >= 5:
        out["paired_therapy_wilcoxon_p"] = float(stats.wilcoxon([x["therapy_diff"] for x in paired]).pvalue)
        out["paired_second_wilcoxon_p"] = float(stats.wilcoxon([x["second_diff"] for x in paired]).pvalue)

    # ---- east fakes vs west fakes ---------------------------------------------
    ef = lab[(lab.fake == 1) & (lab.tradition == "east")]
    wf = lab[(lab.fake == 1) & (lab.tradition == "west")]
    out["fake_dialect_by_tradition"] = {
        "east_n": int(len(ef)), "west_n": int(len(wf)),
        "east_therapy": float(ef.therapy_per_k.mean()), "west_therapy": float(wf.therapy_per_k.mean()),
        "east_second": float(ef.second_person_per_k.mean()), "west_second": float(wf.second_person_per_k.mean()),
        "east_words_med": float(ef.words.median()), "west_words_med": float(wf.words.median()),
    }
    # and sourced baselines by tradition
    es = lab[(lab.fake == 0) & (lab.tradition == "east")]
    ws = lab[(lab.fake == 0) & (lab.tradition == "west")]
    out["sourced_dialect_by_tradition"] = {
        "east_therapy": float(es.therapy_per_k.mean()), "west_therapy": float(ws.therapy_per_k.mean()),
        "east_second": float(es.second_person_per_k.mean()), "west_second": float(ws.second_person_per_k.mean()),
    }

    # ---- classifier: can voice alone spot a fake? ------------------------------
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score, balanced_accuracy_score
    from xgboost import XGBClassifier
    X = lab[feat_cols].values; y = lab["fake"].values
    clf = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.06,
                        scale_pos_weight=float((y == 0).sum() / max((y == 1).sum(), 1)),
                        subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
                        random_state=20261026, n_jobs=4)
    cv = StratifiedKFold(5, shuffle=True, random_state=7)
    proba = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]
    out["classifier"] = {"auc": float(roc_auc_score(y, proba)),
                         "balanced_accuracy_at_0.5": float(balanced_accuracy_score(y, proba > 0.5)),
                         "n_fake": int(y.sum()), "n_sourced": int((y == 0).sum())}
    clf.fit(X, y)
    import shap
    expl = shap.TreeExplainer(clf)
    sv = expl.shap_values(X)
    out["classifier"]["shap_mean_abs"] = {c: float(np.abs(sv[:, i]).mean()) for i, c in enumerate(feat_cols)}
    lab = lab.assign(fake_proba=clf.predict_proba(X)[:, 1])
    top_fake = lab[lab.fake == 1].nlargest(12, "fake_proba")[["thinker", "text", "fake_proba"]]
    out["most_modern_sounding_fakes"] = [
        {"thinker": r.thinker, "proba": round(float(r.fake_proba), 3), "text": r.text[:300]}
        for r in top_fake.itertuples()]
    missed = lab[lab.fake == 0].nlargest(8, "fake_proba")[["thinker", "text", "fake_proba"]]
    out["sourced_that_sound_fake"] = [
        {"thinker": r.thinker, "proba": round(float(r.fake_proba), 3), "text": r.text[:300]}
        for r in missed.itertuples()]
    # example fakes per famous eastern thinker for the write-up
    ex = {}
    for name in ("Laozi", "Confucius", "Buddha", "Rumi", "Socrates", "Voltaire", "Marcus Aurelius"):
        g = df[(df.thinker == name) & (df.status == "misattributed")]
        ex[name] = [t[:260] for t in g["text"].head(4)]
    out["example_misattributed"] = ex

    (ROOT / "results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_quotes", "status_totals", "pooled_fake_share_checked",
          "pooled_unverified_share_all", "fame_vs_fake", "east_west", "east_west_fake_p",
          "classifier")}, indent=1))

if __name__ == "__main__":
    main()
