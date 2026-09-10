"""Compute linguistic metrics for each philosophy text.

Metrics per text:
  - Readability: Flesch Reading Ease, Flesch-Kincaid grade, Gunning Fog
    (via textstat), mean sentence length, mean syllables/word
  - Lexical diversity: type-token ratio on first 10k words
  - Voice: 1st-person singular ("I") and plural ("we") rates per 1k words,
    questions and exclamations per 1k words
  - Concreteness: mean Brysbaert et al. (2014) concreteness rating
    (1 = abstract, 5 = concrete) over rated content words
  - Abstraction: abstract-noun suffix density per 1k words,
    polysyllabic (>=3 syllables) share
  - Sentiment: mean VADER compound over paragraphs (valence of word choice)

Caveats: all texts are English translations of varying vintage, so absolute
values reflect translators as well as authors; the *trends* are the signal.
"""
import csv
import re
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TEXTS = DATA / "texts"

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
VOWEL_RE = re.compile(r"[aeiouy]+")


def syllables(word):
    w = word.lower()
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]e|ed|[^laeiouy]es)$", "", w)
    w = re.sub(r"^y", "", w)
    n = len(VOWEL_RE.findall(w))
    return max(1, n)


def split_sentences(text):
    """Rough sentence splitter that protects common abbreviations."""
    t = text
    for abbr in ("Mr.", "Mrs.", "Ms.", "Dr.", "St.", "e.g.", "i.e.", "etc.",
                 "vs.", "Fig.", "No.", "Ch.", "Bk.", "cf.", "viz.", "op.",
                 "cit.", "ibid.", "Chap.", "Sect.", "Art.", "Vol.", "p.",
                 "pp.", "n.", "sq.", "ff."):
        t = t.replace(abbr, abbr.replace(".", "\u00b7"))
    parts = re.split(r"[.!?]+", t)
    sents = [p.replace("\u00b7", ".").strip() for p in parts]
    return [s for s in sents if len(s.split()) >= 3]


def readability(tokens, sentences):
    """Flesch Reading Ease, Flesch-Kincaid grade, Gunning Fog (own impl)."""
    n_words = len(tokens)
    n_sent = max(1, len(sentences))
    n_syll = sum(syllables(t) for t in tokens)
    wps = n_words / n_sent
    spw = n_syll / n_words
    fre = 206.835 - 1.015 * wps - 84.6 * spw
    fk = 0.39 * wps + 11.8 * spw - 15.59
    complex_words = sum(1 for t in tokens if syllables(t) >= 3 and len(t) > 3)
    fog = 0.4 * (wps + 100 * complex_words / n_words)
    return fre, fk, fog, wps, spw


def load_concreteness():
    # Brysbaert, Warriner & Kuperman (2014), 40k English lemmas, 1-5 scale.
    # Bundled with the 'wordtangible' package (CC-BY data release by authors).
    path = Path(__import__("wordtangible").__file__).parent / "resources" / "concreteness_ratings.csv"
    d = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = next(k for k in row if k.lower() in ("word", "word.orig"))
            val = next(k for k in row if k.lower().startswith("conc"))
            d[row[key].strip().lower()] = float(row[val])
    return d


FIRST_SING = {"i", "me", "my", "mine", "myself"}
FIRST_PLUR = {"we", "us", "our", "ours", "ourselves"}
SECOND = {"you", "your", "yours", "yourself", "yourselves"}
ABSTRACT_SUFFIXES = ("tion", "sion", "ness", "ity", "ism", "ence", "ance",
                     "ment", "dom", "ship", "hood", "ure", "age")
STOP = set(("the a an and or but of to in on for with as at by from is are was "
            "were be been being have has had do does did will would shall should "
            "can could may might must it its this that these those he him his she "
            "her they them their we us our you your i me my not no nor so if then "
            "than too very when where which who whom whose what how all any both "
            "each few more most other some such only own same than very").split())


def analyze(text, conc, vader):
    tokens = [t.lower() for t in WORD_RE.findall(text)]
    n = len(tokens)
    sentences = split_sentences(text)
    fre, fk, fog, wps, spw = readability(tokens, sentences)
    words_10k = tokens[:10000]
    ttr = len(set(words_10k)) / max(1, len(words_10k))

    first_sing = sum(1 for t in tokens if t in FIRST_SING)
    first_plur = sum(1 for t in tokens if t in FIRST_PLUR)
    second = sum(1 for t in tokens if t in SECOND)
    questions = text.count("?")
    exclaims = text.count("!")
    abstract = sum(1 for t in tokens if len(t) > 5 and t.endswith(ABSTRACT_SUFFIXES))
    poly = sum(1 for t in tokens if syllables(t) >= 3)

    content = [t for t in tokens if t not in STOP]
    conc_vals = [conc[t] for t in content if t in conc]

    paras = [p for p in re.split(r"\n\s*\n", text) if len(p.split()) > 20]
    comp = [vader.polarity_scores(p[:4000])["compound"] for p in paras]

    return {
        "words": n,
        "flesch_ease": fre,
        "flesch_kincaid_grade": fk,
        "gunning_fog": fog,
        "avg_sentence_len": wps,
        "avg_syllables_per_word": spw,
        "ttr_10k": ttr,
        "i_per_1k": 1000 * first_sing / n,
        "we_per_1k": 1000 * first_plur / n,
        "you_per_1k": 1000 * second / n,
        "questions_per_1k": 1000 * questions / n,
        "exclaims_per_1k": 1000 * exclaims / n,
        "abstract_per_1k": 1000 * abstract / n,
        "polysyllabic_share": poly / n,
        "concreteness": sum(conc_vals) / max(1, len(conc_vals)),
        "concreteness_coverage": len(conc_vals) / max(1, len(content)),
        "vader_mean": sum(comp) / max(1, len(comp)),
        "vader_pos_share": sum(1 for c in comp if c >= 0.2) / max(1, len(comp)),
        "vader_neg_share": sum(1 for c in comp if c <= -0.2) / max(1, len(comp)),
    }


def main():
    conc = load_concreteness()
    print(f"concreteness norms loaded: {len(conc):,} lemmas")
    vader = SentimentIntensityAnalyzer()
    corpus = pd.read_csv(DATA / "corpus.csv")
    rows = []
    for _, r in corpus.iterrows():
        text = (TEXTS / f"{r['slug']}.txt").read_text(encoding="utf-8")
        m = analyze(text, conc, vader)
        rows.append({**r.to_dict(), **m})
        print(f"{r['slug']:24s} ease={m['flesch_ease']:5.1f} "
              f"conc={m['concreteness']:.2f} i/1k={m['i_per_1k']:4.1f}")
    pd.DataFrame(rows).to_csv(DATA / "metrics.csv", index=False)
    print("metrics.csv written")


if __name__ == "__main__":
    main()
