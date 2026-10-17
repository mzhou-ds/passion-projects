"""Analysis: how the English Tao Te Ching drifted across 147 years of
retranslation (Chalmers 1868, Legge 1891, Carus 1898, Linnell 2015),
benchmarked against the Chinese source and against a Western control
(Marcus Aurelius' Meditations: Long 1862 vs Chrystal 1902).

Outputs: results.json, findings.txt, charts/*.png
Run: python3 src/analyze.py   (after fetch_data.py + segment.py)
"""
import json
import pathlib
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import shap

ROOT = pathlib.Path(__file__).resolve().parent.parent
CH = ROOT / "data" / "chapters"
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
ERAS = ["chalmers", "legge", "carus", "linnell"]
ERA_LABEL = {"chalmers": "Chalmers 1868", "legge": "Legge 1891",
             "carus": "Carus 1898", "linnell": "Linnell 2015"}
ERA_COLOR = {"chalmers": "#8c6d31", "legge": "#386cb0",
             "carus": "#7fc97f", "linnell": "#e08214"}

WORDS = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")

# ------------------------------------------------------------- lexicons
# Fixed before looking at outcomes; ordinary English function/style
# measures are computed separately below.
LEXICONS = {
    "therapy_self": ["self", "peace", "calm", "stillness", "quiet", "heal",
                     "healing", "wellness", "anxiety", "anxious", "stress",
                     "relax", "breath", "breathing", "inner", "soul",
                     "mindful", "meditation", "meditate", "suffering",
                     "worry", "worries", "happiness", "feelings", "emotion",
                     "emotions", "heart"],
    "governance_war": ["govern", "governs", "governing", "government",
                       "rule", "ruler", "rulers", "kingdom", "empire",
                       "prince", "princes", "war", "wars", "army", "armies",
                       "weapon", "weapons", "battle", "battles", "enemy",
                       "enemies", "conquer", "conquers", "conquered",
                       "victory", "soldier", "soldiers", "law", "laws",
                       "punishment", "punish", "minister", "ministers",
                       "subjects", "throne", "reign", "king", "kings"],
    "nature": ["water", "river", "rivers", "valley", "valleys", "mountain",
               "mountains", "tree", "trees", "wood", "earth", "heaven",
               "sky", "wind", "rain", "snow", "seed", "root", "roots",
               "branch", "branches", "stone", "rock", "ocean", "sea",
               "lake", "flower", "grass"],
    "reason_gloss": ["reason", "reasons", "reasoned", "logos"],
}
IMPERATIVES = {"do", "be", "let", "keep", "follow", "seek", "avoid", "know",
               "take", "give", "make", "hold", "leave", "stop", "put", "use",
               "cultivate", "practice", "embrace", "return", "act", "become",
               "look", "listen", "abide", "dwell", "empty", "fill", "trust",
               "remember", "honour", "honor", "lay", "set", "bring", "call"}
MODALS = {"should", "must", "may", "might", "shall", "ought"}
HEDGES = {"perhaps", "maybe", "seems", "seem", "appears", "appear", "almost",
          "likely", "probably"}
SECOND = {"you", "your", "yours", "thou", "thee", "thy", "thine", "ye"}
FIRST = {"i", "we", "us", "our", "my", "me"}
NEG = {"not", "no", "never", "without", "non", "nothing", "none"}


def features(text: str) -> dict:
    toks = [t.lower().replace("’", "'") for t in WORDS.findall(text)]
    n = max(len(toks), 1)
    sents = [s for s in re.split(r"[.!?]+", text) if len(s.split()) >= 2]
    ns = max(len(sents), 1)
    tokset = {}
    for t in toks:
        tokset[t] = tokset.get(t, 0) + 1
    f = {"n_words": len(toks)}
    for name, words in LEXICONS.items():
        f[f"lex_{name}"] = 1000 * sum(tokset.get(w, 0) for w in words) / n
    f["second_person"] = 1000 * sum(tokset.get(w, 0) for w in SECOND) / n
    f["first_person"] = 1000 * sum(tokset.get(w, 0) for w in FIRST) / n
    f["modal_rate"] = 1000 * sum(tokset.get(w, 0) for w in MODALS) / n
    f["hedge_rate"] = 1000 * sum(tokset.get(w, 0) for w in HEDGES) / n
    f["negation_rate"] = 1000 * sum(tokset.get(w, 0) for w in NEG) / n
    f["sage_rate"] = 1000 * tokset.get("sage", 0) / n
    f["tao_dao_rate"] = 1000 * (tokset.get("tao", 0) + tokset.get("dao", 0)
                               + tokset.get("tau", 0)) / n
    f["nominalization_rate"] = 1000 * sum(
        1 for t in toks if t.endswith(("tion", "ness", "ity", "ment"))
        and len(t) > 5) / n
    f["mean_sentence_len"] = len(toks) / ns
    imp = 0
    for s in sents:
        first = WORDS.findall(s.strip().lstrip("\"'“”‘’()"))
        if first and first[0].lower() in IMPERATIVES:
            imp += 1
    f["imperative_rate"] = 100 * imp / ns
    f["question_rate"] = 100 * text.count("?") / ns
    return f


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                 / (len(a) + len(b) - 2))
    return float((b.mean() - a.mean()) / sp) if sp > 0 else 0.0


def main() -> None:
    tao = pd.read_csv(CH / "tao_chapters.csv")
    med = pd.read_csv(CH / "meditations.csv")
    results: dict = {"coverage": {}}

    # ------------------------------------------------ features
    tf = pd.DataFrame([features(t) for t in tao["text"]]).drop(columns=["n_words"])
    tao = pd.concat([tao.reset_index(drop=True), tf], axis=1)
    mf = pd.DataFrame([features(t) for t in med["text"]]).drop(columns=["n_words"])
    med = pd.concat([med.reset_index(drop=True), mf], axis=1)
    feat_cols = [c for c in tf.columns if c != "n_words"]
    for name, g in tao.groupby("translator"):
        results["coverage"][name] = int(len(g))

    # ------------------------------------------------ era panels
    panel = tao.groupby("translator")[feat_cols].mean().reindex(ERAS)
    results["era_panel_per_1000_words"] = {
        c: {e: round(float(panel.loc[e, c]), 2) for e in ERAS}
        for c in feat_cols}
    results["era_words_total"] = {
        e: int(tao[tao.translator == e]["n_words"].sum()) for e in ERAS}
    results["era_mean_chapter_words"] = {
        e: round(float(tao[tao.translator == e]["n_words"].mean()), 1)
        for e in ERAS}

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharex=True)
    for ax, col, title in [
            (axes[0], "lex_therapy_self", "Therapy / self words"),
            (axes[1], "lex_governance_war", "Governance / war words"),
            (axes[2], "lex_nature", "Nature words")]:
        ys = [panel.loc[e, col] for e in ERAS]
        ax.plot(range(4), ys, "o-", color="#333333", lw=1.6)
        for i, e in enumerate(ERAS):
            ax.plot(i, ys[i], "o", color=ERA_COLOR[e], ms=9)
        ax.set_title(title + " (per 1,000 words)")
        ax.set_xticks(range(4))
        ax.set_xticklabels(["1868", "1891", "1898", "2015"], rotation=30)
        ax.grid(alpha=0.25)
    fig.suptitle("The Tao's vocabulary rotates: from the state to the self")
    fig.tight_layout()
    fig.savefig(CHARTS / "lexicon_panels.png")
    plt.close(fig)

    # ------------------------------------------------ expansion vs Chinese
    piv = tao.pivot_table(index="chapter", columns="translator",
                          values="words_per_cn_char")
    common = piv.dropna()
    results["chapters_in_all_four"] = int(len(common))
    results["mean_words_per_cn_char"] = {
        e: round(float(common[e].mean()), 3) for e in ERAS}
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for e in ERAS:
        ax.plot(common.index, common[e], lw=1.1, alpha=0.85,
                color=ERA_COLOR[e], label=ERA_LABEL[e])
    ax.set_xlabel("Chapter")
    ax.set_ylabel("English words per Chinese character")
    ax.set_title("Expansion ratio by chapter: how much English each era "
                 "needed for the same Chinese")
    ax.legend(frameon=False, ncol=4, fontsize=8.5)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHARTS / "expansion_ratio.png")
    plt.close(fig)

    # ------------------------------------------------ TF-IDF disagreement
    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2,
                          sublinear_tf=True)
    X = vec.fit_transform(tao["text"])
    D = cosine_distances(X)
    idx = {(t, int(c)): i for i, (t, c) in
           enumerate(zip(tao["translator"], tao["chapter"]))}
    drift_rows = []
    for ch in sorted(set(tao["chapter"])):
        row = {"chapter": int(ch)}
        for a, b in [("chalmers", "linnell"), ("legge", "linnell"),
                     ("carus", "linnell"), ("chalmers", "legge"),
                     ("legge", "carus")]:
            if (a, ch) in idx and (b, ch) in idx:
                row[f"dist_{a}_{b}"] = float(D[idx[(a, ch)], idx[(b, ch)]])
        drift_rows.append(row)
    drift = pd.DataFrame(drift_rows)
    main_drift = drift.dropna(subset=["dist_legge_linnell"]).sort_values(
        "dist_legge_linnell", ascending=False)
    results["most_reinvented_legge_to_linnell"] = [
        {"chapter": int(r.chapter),
         "tfidf_distance": round(float(r.dist_legge_linnell), 3)}
        for r in main_drift.head(12).itertuples()]
    results["least_reinvented_legge_to_linnell"] = [
        {"chapter": int(r.chapter),
         "tfidf_distance": round(float(r.dist_legge_linnell), 3)}
        for r in main_drift.tail(8).itertuples()]
    results["mean_tfidf_distance"] = {
        c: round(float(drift[c].mean()), 3)
        for c in drift.columns if c.startswith("dist_")}

    top = main_drift.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh([f"ch. {c}" for c in top["chapter"]], top["dist_legge_linnell"],
            color="#386cb0", alpha=0.9)
    ax.set_xlabel("TF-IDF cosine distance, Legge 1891 vs Linnell 2015")
    ax.set_title("The most reinvented chapters (same Chinese, different book)")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(CHARTS / "reinvented_chapters.png")
    plt.close(fig)

    # ------------------------------------------------ famous-chapter test
    FAMOUS = {1, 8, 11, 25, 33, 42, 56, 76, 78, 81}
    d = drift.dropna(subset=["dist_legge_linnell"]).copy()
    d["famous"] = d["chapter"].isin(FAMOUS)
    fam, rest = d[d.famous]["dist_legge_linnell"], d[~d.famous]["dist_legge_linnell"]
    rng = np.random.default_rng(7)
    obs = fam.mean() - rest.mean()
    pooled = np.concatenate([fam, rest])
    # proper permutation: shuffle once per draw, split at len(fam)
    diffs = []
    for _ in range(5000):
        p = rng.permutation(pooled)
        diffs.append(p[:len(fam)].mean() - p[len(fam):].mean())
    pval = float((np.abs(diffs) >= abs(obs)).mean())
    results["famous_chapters"] = {
        "famous_set": sorted(FAMOUS),
        "mean_drift_famous": round(float(fam.mean()), 3),
        "mean_drift_rest": round(float(rest.mean()), 3),
        "permutation_p_two_sided": round(pval, 4)}

    # ------------------------------------------------ era classifier + SHAP
    clf_feats = feat_cols
    Xc = tao[clf_feats].to_numpy(float)
    yc = tao["translator"].map({e: i for i, e in enumerate(ERAS)}).to_numpy()
    cv = StratifiedKFold(5, shuffle=True, random_state=3)
    model = xgb.XGBClassifier(n_estimators=300, max_depth=3,
                              learning_rate=0.06, subsample=0.9,
                              colsample_bytree=0.9, random_state=3)
    scores = cross_val_score(model, Xc, yc, cv=cv)
    results["era_classifier"] = {
        "cv_accuracy_mean": round(float(scores.mean()), 3),
        "cv_accuracy_sd": round(float(scores.std()), 3),
        "chance": 0.25,
        "features": clf_feats}
    model.fit(Xc, yc)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(Xc)
    sv_arr = np.asarray(sv)
    if sv_arr.ndim == 3:  # (n, features, classes) or (classes, n, features)
        if sv_arr.shape[1] == len(clf_feats):
            imp = np.abs(sv_arr).mean(axis=(0, 2))
        else:
            imp = np.abs(sv_arr).mean(axis=(0, 1))
    else:
        imp = np.abs(sv_arr).mean(axis=0)
    order = np.argsort(imp)[::-1]
    results["era_classifier"]["shap_importance"] = {
        clf_feats[i]: round(float(imp[i]), 3) for i in order}
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    top_idx = order[:10][::-1]
    ax.barh([clf_feats[i].replace("_", " ") for i in top_idx],
            imp[top_idx], color="#e08214", alpha=0.9)
    ax.set_xlabel("Mean |SHAP| - what gives a translation's era away")
    ax.set_title("A model can date a Tao translation from its language alone")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(CHARTS / "shap_importance.png")
    plt.close(fig)

    # sensitivity: drop Chalmers (OCR + footnotes), 3-era classifier
    tao3 = tao[tao.translator != "chalmers"]
    X3 = tao3[clf_feats].to_numpy(float)
    y3 = tao3["translator"].map({"legge": 0, "carus": 1, "linnell": 2}).to_numpy()
    scores3 = cross_val_score(
        xgb.XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.06,
                          subsample=0.9, colsample_bytree=0.9, random_state=3),
        X3, y3, cv=StratifiedKFold(5, shuffle=True, random_state=3))
    results["era_classifier_no_chalmers"] = {
        "cv_accuracy_mean": round(float(scores3.mean()), 3), "chance": 0.333}

    # ------------------------------------------------ chapter clustering
    cl = drift.dropna(subset=["dist_legge_linnell", "dist_carus_linnell"]).copy()
    lp = tao[tao.translator == "legge"].set_index("chapter")
    np_ = tao[tao.translator == "linnell"].set_index("chapter")
    cl["therapy_delta"] = [np_.loc[c, "lex_therapy_self"] - lp.loc[c, "lex_therapy_self"]
                           for c in cl["chapter"]]
    cl["governance_delta"] = [np_.loc[c, "lex_governance_war"] - lp.loc[c, "lex_governance_war"]
                              for c in cl["chapter"]]
    cl["expansion_delta"] = [np_.loc[c, "words_per_cn_char"] - lp.loc[c, "words_per_cn_char"]
                             for c in cl["chapter"]]
    cfeat = ["dist_legge_linnell", "dist_carus_linnell", "therapy_delta",
             "governance_delta", "expansion_delta"]
    Z = StandardScaler().fit_transform(cl[cfeat])
    km = KMeans(n_clusters=3, n_init=20, random_state=5).fit(Z)
    cl["cluster"] = km.labels_
    results["chapter_clusters"] = {}
    for k in range(3):
        sub = cl[cl.cluster == k]
        results["chapter_clusters"][str(k)] = {
            "chapters": [int(c) for c in sorted(sub["chapter"])],
            "mean": {c: round(float(sub[c].mean()), 3) for c in cfeat}}

    # ------------------------------------------------ control: Meditations
    med_panel = med.groupby("translator")[feat_cols].mean()
    tao_d, med_d = {}, {}
    lp_ch = tao[tao.translator == "legge"]
    nn_ch = tao[tao.translator == "linnell"]
    merged = lp_ch.set_index("chapter").join(
        nn_ch.set_index("chapter"), lsuffix="_legge", rsuffix="_linnell",
        how="inner")
    long_b = med[med.translator == "long"]
    chr_b = med[med.translator == "chrystal"]
    for c in feat_cols:
        tao_d[c] = cohens_d(merged[f"{c}_legge"], merged[f"{c}_linnell"])
        med_d[c] = cohens_d(long_b[c], chr_b[c])
    results["cohens_d_legge_to_linnell"] = {k: round(v, 2) for k, v in tao_d.items()}
    results["cohens_d_long_to_chrystal_meditations"] = {
        k: round(v, 2) for k, v in med_d.items()}
    results["mean_abs_d"] = {
        "tao_1891_to_2015": round(float(np.mean([abs(v) for v in tao_d.values()])), 2),
        "meditations_1862_to_1902": round(float(np.mean([abs(v) for v in med_d.values()])), 2)}
    results["meditations_panel"] = {
        c: {"long_1862": round(float(med_panel.loc["long", c]), 2),
            "chrystal_1902": round(float(med_panel.loc["chrystal", c]), 2)}
        for c in feat_cols}

    fig, ax = plt.subplots(figsize=(10, 4.4))
    xs = np.arange(len(feat_cols))
    ax.bar(xs - 0.2, [abs(tao_d[c]) for c in feat_cols], width=0.4,
           label="Tao: Legge 1891 -> Linnell 2015", color="#e08214")
    ax.bar(xs + 0.2, [abs(med_d[c]) for c in feat_cols], width=0.4,
           label="Meditations: Long 1862 -> Chrystal 1902", color="#386cb0")
    ax.set_xticks(xs)
    ax.set_xticklabels([c.replace("lex_", "").replace("_rate", "").replace("_", " ")
                        for c in feat_cols], rotation=38, ha="right", fontsize=8)
    ax.set_ylabel("|Cohen's d| between translations")
    ax.set_title("Retranslation drift by feature: the Tao's earthquake is sentence length")
    ax.legend(frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(CHARTS / "control_drift.png")
    plt.close(fig)

    # ------------------------------------------------ headline deltas
    def pct(e0, e1, col):
        a, b = panel.loc[e0, col], panel.loc[e1, col]
        return round(float(100 * (b - a) / a), 1) if a else None
    results["headline_deltas_pct_1868_to_2015"] = {
        c: pct("chalmers", "linnell", c) for c in feat_cols}
    results["headline_deltas_pct_1891_to_2015"] = {
        c: pct("legge", "linnell", c) for c in feat_cols}

    (ROOT / "results.json").write_text(json.dumps(results, indent=1))
    print(json.dumps({k: results[k] for k in
                      ["coverage", "era_words_total", "mean_words_per_cn_char",
                       "mean_tfidf_distance", "famous_chapters", "mean_abs_d"]},
                     indent=1))
    print("era classifier CV:", results["era_classifier"]["cv_accuracy_mean"],
          "| no-chalmers:", results["era_classifier_no_chalmers"]["cv_accuracy_mean"])
    print("top SHAP:", list(results["era_classifier"]["shap_importance"])[:6])
    print("most reinvented:", results["most_reinvented_legge_to_linnell"][:5])


if __name__ == "__main__":
    main()
