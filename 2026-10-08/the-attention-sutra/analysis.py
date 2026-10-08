#!/usr/bin/env python3
"""
The Attention Sutra — who wins the philosophy attention economy, and why.

Three data layers, all public, all reproducible:
  1. Wikimedia pageviews API: monthly en.wikipedia views, Jan 2016 - Sep 2026,
     for 36 philosophy articles grouped into 5 traditions.
  2. Wikipedia API: article length (bytes) as a supply-side control.
  3. Project Gutenberg: 8 primary texts, stylometric features (sentence
     length, Flesch reading ease, imperative / second-person / question /
     negation rates, lexical diversity).

Analyses:
  A. Tradition attention shares, indexed trends, COVID-window deltas,
     January (New-Year) seasonality, growth 2016-19 vs 2023-26.
  B. KMeans clustering of articles by the *shape* of their monthly
     attention trajectory (archetypes, not levels).
  C. Stylometry of the 8 primary texts + PCA; join text style to the
     attention those works/authors actually receive; correlations with
     honest small-n caveats, plus a leave-one-out linear check.

Run: python3 analysis.py   (downloads once, caches under data/cache/)
Outputs: data/*.csv, results.json, findings.txt, figures/*.png
"""
import json, math, re, sys, time, unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent
DATA = ROOT / "data"; FIGS = ROOT / "figures"; CACHE = DATA / "cache"
for d in (DATA, FIGS, CACHE):
    d.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "MusingWithMike-AttentionSutra/1.0 (daily research build)"}
START, END = "2016010100", "2026093000"

# ---------------------------------------------------------------- articles
# article -> (tradition, kind)  kind: person | work | concept
ARTICLES = {
    # Stoicism
    "Stoicism": ("stoicism", "concept"), "Marcus_Aurelius": ("stoicism", "person"),
    "Seneca_the_Younger": ("stoicism", "person"), "Epictetus": ("stoicism", "person"),
    "Meditations": ("stoicism", "work"), "Zeno_of_Citium": ("stoicism", "person"),
    # Eastern (Taoist / Buddhist / Hindu / Confucian shelf, as read in the West)
    "Taoism": ("eastern", "concept"), "Tao_Te_Ching": ("eastern", "work"),
    "Laozi": ("eastern", "person"), "Zen": ("eastern", "concept"),
    "Mindfulness": ("eastern", "concept"), "Karma": ("eastern", "concept"),
    "Buddhism": ("eastern", "concept"), "Bhagavad_Gita": ("eastern", "work"),
    "Confucius": ("eastern", "person"), "Alan_Watts": ("eastern", "person"),
    "Dhammapada": ("eastern", "work"), "Yin_and_yang": ("eastern", "concept"),
    # Transcendentalism
    "Transcendentalism": ("transcendentalism", "concept"),
    "Ralph_Waldo_Emerson": ("transcendentalism", "person"),
    "Henry_David_Thoreau": ("transcendentalism", "person"),
    "Walden": ("transcendentalism", "work"),
    # Existentialism / meaning
    "Existentialism": ("existential", "concept"),
    "Friedrich_Nietzsche": ("existential", "person"),
    "Søren_Kierkegaard": ("existential", "person"),
    "Albert_Camus": ("existential", "person"),
    "Viktor_Frankl": ("existential", "person"),
    "Nihilism": ("existential", "concept"), "Absurdism": ("existential", "concept"),
    "Man's_Search_for_Meaning": ("existential", "work"),
    # Classical / analytic control shelf
    "Plato": ("classical", "person"), "Aristotle": ("classical", "person"),
    "Socrates": ("classical", "person"), "Immanuel_Kant": ("classical", "person"),
    "Philosophy": ("classical", "concept"), "Ethics": ("classical", "concept"),
}

TEXTS = {  # gutenberg id -> (title, article to join, tradition)
    216:  ("Tao Te Ching (Legge, 1891)", "Tao_Te_Ching", "eastern"),
    2017: ("Dhammapada (Muller, 1881)", "Dhammapada", "eastern"),
    4094: ("Analects of Confucius (Legge)", "Confucius", "eastern"),
    2388: ("Bhagavad Gita (Arnold, 1885)", "Bhagavad_Gita", "eastern"),
    2680: ("Meditations of Marcus Aurelius (Long)", "Meditations", "stoicism"),
    2944: ("Emerson, Essays: First Series (1841)", "Ralph_Waldo_Emerson", "transcendentalism"),
    205:  ("Thoreau, Walden (1854)", "Walden", "transcendentalism"),
    4363: ("Nietzsche, Beyond Good and Evil (Zimmern, 1909)", "Friedrich_Nietzsche", "existential"),
}

def get(url, **kw):
    for i in range(4):
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code == 200:
            return r
        time.sleep(2 * (i + 1))
    r.raise_for_status()

# ---------------------------------------------------------------- pageviews
def fetch_pageviews():
    cache = CACHE / "pageviews.json"
    if cache.exists():
        return pd.DataFrame(json.loads(cache.read_text()))
    rows = []
    for art in ARTICLES:
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"en.wikipedia/all-access/all-agents/{requests.utils.quote(art, safe='')}"
               f"/monthly/{START}/{END}")
        items = get(url).json().get("items", [])
        for it in items:
            rows.append({"article": art, "tradition": ARTICLES[art][0],
                         "kind": ARTICLES[art][1], "month": it["timestamp"][:6],
                         "views": it["views"]})
        print(f"  pageviews {art}: {len(items)} months", flush=True)
    df = pd.DataFrame(rows)
    cache.write_text(json.dumps(rows))
    return df

def fetch_lengths():
    cache = CACHE / "lengths.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out, arts = {}, list(ARTICLES)
    for i in range(0, len(arts), 20):
        batch = "|".join(a.replace("_", " ") for a in arts[i:i + 20])
        j = get("https://en.wikipedia.org/w/api.php",
                params={"action": "query", "prop": "info", "format": "json",
                        "titles": batch}).json()
        for p in j["query"]["pages"].values():
            out[p["title"].replace(" ", "_")] = p.get("length", np.nan)
    cache.write_text(json.dumps(out))
    return out

# ---------------------------------------------------------------- texts
WORD = re.compile(r"[A-Za-z']+")
SENT = re.compile(r"(?<=[.!?])\s+")
IMPERATIVE_STARTS = set("""do be let go take make keep seek know learn live die fear hope
love hate give find hold leave turn stand sit walk speak listen look see think act begin
remember forget follow avoid choose trust doubt ask answer rise fall stay move wait watch
guard cultivate practice abstain refrain cease strive endeavour endeavor consider meditate""".split())

def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if len(w) <= 3: return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")): n -= 1
    return max(1, n)

def text_features(raw):
    m = re.search(r"\*\*\* START OF.*?\*\*\*", raw, re.S)
    if m: raw = raw[m.end():]
    m = re.search(r"\*\*\* END OF", raw)
    if m: raw = raw[:m.start()]
    words = WORD.findall(raw)
    sents = [s.strip() for s in SENT.split(raw) if len(s.split()) >= 3]
    nw, ns = len(words), max(1, len(sents))
    wps = nw / ns
    syl = np.mean([syllables(w) for w in words[::7]])  # sample for speed
    flesch = 206.835 - 1.015 * wps - 84.6 * syl
    low = [s.lower() for s in sents]
    you = sum(len(re.findall(r"\byou\b|\byour\b|\bthou\b|\bthy\b|\bthee\b", s)) for s in low)
    ques = np.mean([s.rstrip().endswith("?") for s in sents])
    imp = np.mean([WORD.findall(s)[0].lower() in IMPERATIVE_STARTS
                   for s in low if WORD.findall(s)])
    neg = sum(len(re.findall(r"\bnot\b|\bno\b|\bnever\b|\bnothing\b|\bwithout\b", s)) for s in low)
    hapax = pd.Series([w.lower() for w in words]).value_counts()
    return {"words": nw, "sentences": ns, "words_per_sentence": round(wps, 1),
            "flesch_reading_ease": round(float(flesch), 1),
            "you_per_1k": round(1000 * you / nw, 2),
            "question_rate": round(float(ques), 4),
            "imperative_start_rate": round(float(imp), 4),
            "negation_per_1k": round(1000 * neg / nw, 2),
            "type_token_ratio": round(len(hapax) / nw, 4),
            "hapax_share": round(float((hapax == 1).mean()), 3)}

def fetch_texts():
    cache = CACHE / "text_stats.json"
    if cache.exists():
        return pd.DataFrame(json.loads(cache.read_text()))
    rows = []
    for gid, (title, article, trad) in TEXTS.items():
        raw = get(f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt").text
        f = text_features(raw)
        f.update({"gutenberg_id": gid, "title": title, "article": article, "tradition": trad})
        rows.append(f)
        print(f"  text {title}: {f['words']} words", flush=True)
    df = pd.DataFrame(rows)
    cache.write_text(json.dumps(rows))
    return df

# ---------------------------------------------------------------- main
def main():
    pv = fetch_pageviews()
    pv["date"] = pd.to_datetime(pv["month"], format="%Y%m")
    pv.to_csv(DATA / "pageviews_monthly.csv", index=False)
    lengths = fetch_lengths()
    texts = fetch_texts()
    texts.to_csv(DATA / "text_stats.csv", index=False)
    R = {}

    wide = pv.pivot_table(index="date", columns="article", values="views", aggfunc="sum").sort_index()
    trad = pv.groupby(["date", "tradition"])["views"].sum().unstack().sort_index()
    R["months"] = [str(trad.index.min().date()), str(trad.index.max().date())]
    R["articles"] = int(pv.article.nunique()); R["total_views"] = int(pv.views.sum())

    # A1 shares + indexed trend
    share = trad.div(trad.sum(axis=1), axis=0) * 100
    R["share_2016"] = {k: round(v, 1) for k, v in share.loc["2016"].mean().items()}
    R["share_recent"] = {k: round(v, 1) for k, v in share.loc["2025":"2026"].mean().items()}
    idx = trad / trad.loc["2016"].mean() * 100
    slopes = {}
    for c in trad.columns:
        y = np.log(trad[c].loc["2017":]); x = (y.index - y.index[0]).days / 365.25
        slopes[c] = round(float(np.polyfit(x, y, 1)[0]) * 100, 1)  # %/yr log trend
    R["log_trend_pct_per_year_2017plus"] = slopes

    # A2 COVID window & growth & January effect
    per = pv.copy()
    per["period"] = np.select(
        [per.date < "2020-03-01", per.date <= "2021-12-31", per.date <= "2022-12-31"],
        ["pre_2016_2020-02", "covid_2020-03_2021-12", "hangover_2022"], "recent_2023plus")
    piv = per.groupby(["article", "period"])["views"].mean().unstack()
    piv["covid_lift_pct"] = (piv["covid_2020-03_2021-12"] / piv["pre_2016_2020-02"] - 1) * 100
    early = pv[pv.date < "2020"].groupby("article")["views"].mean()
    late = pv[pv.date >= "2023"].groupby("article")["views"].mean()
    growth = ((late / early - 1) * 100).rename("growth_2023plus_vs_2016_19_pct")
    jan = pv.assign(m=pv.date.dt.month).query("m==1").groupby("tradition")["views"].mean()
    nonjan = pv.assign(m=pv.date.dt.month).query("m!=1").groupby("tradition")["views"].mean()
    idx_pivot = wide.div(wide.loc["2016"].mean())
    art = pd.DataFrame({"avg_monthly_views_recent": late.round(0),
                        "log10_recent": np.log10(late).round(2),
                        "page_bytes": pd.Series(lengths)})
    art = art.join(growth).join(piv["covid_lift_pct"].rename("covid_lift_pct").round(1))
    art["tradition"] = [ARTICLES[a][0] for a in art.index]
    art["kind"] = [ARTICLES[a][1] for a in art.index]
    art = art.sort_values("avg_monthly_views_recent", ascending=False)
    art.to_csv(DATA / "article_stats.csv")
    R["january_lift_pct_by_tradition"] = {k: round(float(v), 1) for k, v in
                                          ((jan / nonjan - 1) * 100).items()}
    R["top5_recent"] = {k: int(v) for k, v in art["avg_monthly_views_recent"].head(5).items()}
    R["biggest_gainers"] = {k: round(float(v)) for k, v in growth.sort_values(ascending=False).head(5).items()}
    R["biggest_losers"] = {k: round(float(v)) for k, v in growth.sort_values().head(5).items()}
    R["covid_lift_by_tradition"] = {k: round(float(v), 1) for k, v in
        per.groupby(["tradition", "period"])["views"].mean().unstack()
           .assign(l=lambda d: (d["covid_2020-03_2021-12"] / d["pre_2016_2020-02"] - 1) * 100)["l"].items()}

    # A3 kind-level (person vs work vs concept), seasonality, anomaly audit
    kind_g = pv.merge(art[["growth_2023plus_vs_2016_19_pct"]], left_on="article",
                      right_index=True, how="left")
    R["median_growth_by_kind"] = {k: round(float(v), 1) for k, v in
        art.groupby("kind")["growth_2023plus_vs_2016_19_pct"].median().items()}
    R["median_growth_by_tradition"] = {k: round(float(v), 1) for k, v in
        art.groupby("tradition")["growth_2023plus_vs_2016_19_pct"].median().items()}
    seas = pv.assign(m=pv.date.dt.month).groupby(["tradition", "m"])["views"].mean().unstack(0)
    seas_idx = (seas / seas.mean() * 100).round(1)
    seas_idx.to_csv(DATA / "seasonality_by_tradition.csv")
    R["september_index_by_tradition"] = {k: float(seas_idx.loc[9, k]) for k in seas_idx.columns}
    R["january_index_by_tradition"] = {k: float(seas_idx.loc[1, k]) for k in seas_idx.columns}
    step = (wide / wide.shift(1)).max()
    art["max_mom_jump"] = step.reindex(art.index).round(2).values
    art["anomaly_flag"] = np.where(art["max_mom_jump"] >= 3, "step-change: audit before citing", "")
    ex = pv[pv.article != "Laozi"]
    trad_ex = ex.groupby(["date", "tradition"])["views"].sum().unstack()
    share_ex = trad_ex.div(trad_ex.sum(axis=1), axis=0) * 100
    R["share_recent_excluding_Laozi"] = {k: round(float(v), 1) for k, v in
                                         share_ex.loc["2025":"2026"].mean().items()}
    R["eastern_growth_excluding_Laozi_note"] = (
        "Laozi monthly views stepped 6.3x in Mar 2023 (49k->361k) and stayed elevated; "
        "pattern is consistent with automated/referral traffic, not organic reading. "
        "Headline eastern figures exclude Laozi where noted.")
    art.to_csv(DATA / "article_stats.csv")

    # B trajectory clustering (shape, not level): z-score each article's series
    Z = (wide - wide.mean()) / wide.std()
    km = KMeans(n_clusters=4, n_init=20, random_state=7).fit(Z.T)
    art["cluster"] = pd.Series(km.labels_, index=wide.columns).reindex(art.index).values
    centers = pd.DataFrame(km.cluster_centers_, columns=wide.index)
    prof = {}
    for c in range(4):
        s = centers.loc[c]
        prof[str(c)] = {"covid_2020_21": round(float(s.loc["2020":"2021"].mean()), 2),
                        "recent_2024_26": round(float(s.loc["2024":].mean()), 2),
                        "early_2016_17": round(float(s.loc["2016":"2017"].mean()), 2),
                        "members": sorted(wide.columns[km.labels_ == c].tolist())}
    R["trajectory_clusters"] = prof
    art.to_csv(DATA / "article_stats.csv")

    # C stylometry + join to attention
    tj = texts.set_index("article").join(art[["avg_monthly_views_recent", "log10_recent",
                                              "growth_2023plus_vs_2016_19_pct", "covid_lift_pct"]])
    feats = ["words_per_sentence", "flesch_reading_ease", "you_per_1k", "question_rate",
             "imperative_start_rate", "negation_per_1k", "type_token_ratio"]
    corr = {f: round(float(np.corrcoef(tj[f], tj["log10_recent"])[0, 1]), 2) for f in feats}
    R["style_vs_log_attention_corr_n8"] = corr
    pca_model = PCA(n_components=2)
    pca_xy = pca_model.fit_transform(StandardScaler().fit_transform(tj[feats]))
    tj["pc1"], tj["pc2"] = pca_xy[:, 0].round(2), pca_xy[:, 1].round(2)
    R["pca_variance"] = [round(float(v), 2) for v in pca_model.explained_variance_ratio_]
    tj.to_csv(DATA / "text_attention_join.csv")
    # leave-one-out linear check: flesch + you-rate -> log attention
    X = StandardScaler().fit_transform(tj[["flesch_reading_ease", "you_per_1k"]].astype(float))
    y = tj["log10_recent"].values.astype(float); pred = np.zeros_like(y)
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False
        b = np.linalg.lstsq(np.c_[X[m], np.ones(m.sum())], y[m], rcond=None)[0]
        pred[i] = np.r_[X[i], 1] @ b
    ss = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    R["loo_linear_R2_style2_n8"] = round(float(ss), 2)

    # ------------------------------------------------------------ figures
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                         "grid.alpha": .25, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for c in share.columns: ax.plot(share.index, share[c], label=c, lw=1.6)
    ax.set_ylabel("share of panel views (%)"); ax.legend(ncol=3, fontsize=8)
    ax.annotate("eastern share inflated from Mar 2023\nby the Laozi step-change anomaly (see audit)",
                xy=(pd.Timestamp("2023-06-01"), 38), xytext=(pd.Timestamp("2019-06-01"), 39),
                fontsize=7, arrowprops=dict(arrowstyle="->", lw=.8))
    ax.set_title("Fig 1 — Who owns philosophy attention? (share of 36-article panel)")
    fig.tight_layout(); fig.savefig(FIGS / "fig1_attention_share.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for c in idx.columns: ax.plot(idx.index, idx[c], label=c, lw=1.6)
    ax.axhline(100, color="grey", lw=.8); ax.set_ylabel("monthly views, 2016 avg = 100")
    ax.legend(ncol=3, fontsize=8); ax.set_title("Fig 2 — Indexed attention by tradition")
    fig.tight_layout(); fig.savefig(FIGS / "fig2_indexed_trends.png"); plt.close(fig)

    g = growth.sort_values()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    colors = ["#2e7d32" if v > 0 else "#b71c1c" for v in g]
    ax.barh(g.index, g.clip(-60, 150).values, color=colors); ax.axvline(0, color="k", lw=.8)
    ax.annotate("Laozi +591% — flagged step-change anomaly\n(see README audit), bar clipped",
                xy=(150, len(g) - 1), xytext=(55, len(g) - 4), fontsize=7,
                arrowprops=dict(arrowstyle="->", lw=.8))
    ax.set_xlabel("avg monthly views: 2023–26 vs 2016–19 (%)")
    ax.set_title("Fig 3 — Winners and losers of the decade")
    fig.tight_layout(); fig.savefig(FIGS / "fig3_growth.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for c in range(4):
        ax.plot(wide.index, centers.loc[c].rolling(3, center=True).mean(),
                label=f"cluster {c} (n={(km.labels_==c).sum()})", lw=1.6)
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"), color="orange", alpha=.12)
    ax.set_ylabel("z-scored views (3-mo smooth)"); ax.legend(fontsize=8)
    ax.set_title("Fig 4 — Attention trajectory archetypes (COVID window shaded)")
    fig.tight_layout(); fig.savefig(FIGS / "fig4_clusters.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for trad_name, sub in tj.groupby("tradition"):
        ax.scatter(sub["flesch_reading_ease"], sub["log10_recent"], s=90, label=trad_name)
        for a, r in sub.iterrows():
            ax.annotate(a.replace("_", " "), (r["flesch_reading_ease"], r["log10_recent"]),
                        fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Flesch reading ease of primary text (higher = easier)")
    ax.set_ylabel("log10 avg monthly Wikipedia views, 2023–26")
    ax.legend(fontsize=8); ax.set_title("Fig 5 — Easier texts, bigger audiences? (n=8 works)")
    fig.tight_layout(); fig.savefig(FIGS / "fig5_style_vs_attention.png"); plt.close(fig)

    (ROOT / "results.json").write_text(json.dumps(R, indent=2))
    lines = [f"{k}: {v}" for k, v in R.items()]
    (ROOT / "findings.txt").write_text("\n".join(lines))
    print(json.dumps(R, indent=2))

if __name__ == "__main__":
    main()
