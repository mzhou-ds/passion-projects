#!/usr/bin/env python3
"""Build #68 analysis v3: final numbers.
- Analects added; containment recomputed on truncated Walden.
- Fingerprint null calibration (source-vs-source).
- Locate the two Vishnu Purana quotations by chapter.
- Per-essay fingerprints for Emerson.
"""
import json, os, re
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "data")

def clean(t):
    m = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", t, re.S)
    if m: t = t[m.end():]
    m = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", t, re.S)
    if m: t = t[:m.start()]
    return t

def load(k):
    return clean(open(os.path.join(RAW, f"{k}.txt"), encoding="utf-8", errors="ignore").read())

def words(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s']", " ", text)
    return re.sub(r"\s+", " ", text).split()

def sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text) if len(p.strip()) > 20]

def ngrams(ws, n):
    return set(tuple(ws[i:i + n]) for i in range(len(ws) - n + 1))

walden_full = load("walden")
CD = walden_full.find("I heartily accept the motto")
walden = walden_full[:CD] if CD > 0 else walden_full
texts = {
    "walden": walden,
    "emerson_essays1": load("emerson_essays1"),
    "emerson_nature": load("emerson_nature"),
    "gita_arnold": load("gita_arnold"),
    "upanishads_muller": load("upanishads_muller"),
    "vishnu_purana": load("vishnu_purana"),
    "analects_legge": load("analects"),
    "kjv": load("kjv"),
    "sartor": load("sartor"),
}
SOURCES = ["gita_arnold", "upanishads_muller", "vishnu_purana", "analects_legge"]
CONTROLS = ["kjv", "sartor"]
print({k: f"{len(words(v)):,}w" for k, v in texts.items()})

# --- 1. containment with Analects
src_grams = {s: {6: ngrams(words(texts[s]), 6), 8: ngrams(words(texts[s]), 8)}
             for s in SOURCES + CONTROLS}
final = {}
for t in ["walden", "emerson_essays1", "emerson_nature"]:
    tw = words(texts[t])
    ts = sentences(texts[t])
    row = {}
    for s in SOURCES + CONTROLS:
        h6 = ngrams(tw, 6) & src_grams[s][6]
        h8 = ngrams(tw, 8) & src_grams[s][8]
        sent_hits = sum(1 for x in ts if len(words(x)) >= 6 and (ngrams(words(x), 6) & src_grams[s][6]))
        row[s] = {"distinct_6g": len(h6), "distinct_8g": len(h8),
                  "sentences_with_6g": sent_hits, "sentence_share": round(sent_hits / len(ts), 4)}
    final[t] = row
    print(f"\n{t}:")
    for s in SOURCES + CONTROLS:
        print(f"  {s:18s} 6g={row[s]['distinct_6g']:3d} 8g={row[s]['distinct_8g']:3d}"
              f" sents={row[s]['sentences_with_6g']:3d} ({row[s]['sentence_share']:.2%})")

# which Analects 6-grams hit in Walden?
hits = ngrams(words(walden), 6) & src_grams["analects_legge"][6]
print("\nWalden 6-gram hits vs Analects (Legge):")
for h in sorted(hits):
    print("  ", " ".join(h))
for x in sentences(walden):
    if len(words(x)) >= 6 and (ngrams(words(x), 6) & src_grams["analects_legge"][6]):
        print("  SENT:", x[:240])

# --- 2. fingerprint null calibration
all_src = SOURCES + CONTROLS
vec = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 1))
X = vec.fit_transform([texts[s] for s in all_src])
vocab = np.array(vec.get_feature_names_out())
finger = {}
for i, s in enumerate(all_src):
    row = X[i].toarray()[0]
    finger[s] = set(vocab[np.argsort(row)[-150:][::-1]].tolist())

def fp_share(text):
    c = Counter(w for w in words(text) if w.isalpha())
    tot = sum(c.values())
    return {s: round(100 * sum(c[w] for w in finger[s]) / tot, 2) for s in all_src}

print("\nFingerprint null matrix (row text, col fingerprint) — diagonals are ~100% by construction, off-diagonals are the chance level:")
print(f"{'':22s}" + "".join(f"{s[:12]:>13s}" for s in all_src))
for s in all_src:
    print(f"{s:22s}" + "".join(f"{fp_share(texts[s])[c]:13.2f}" for c in all_src))
print("\nTargets:")
for t in ["walden", "emerson_essays1", "emerson_nature"]:
    print(f"  {t:18s} {fp_share(texts[t])}")

# --- 3. locate Vishnu quotations by Walden chapter
WALDEN_CHAPTERS = ["Economy", "Where I Lived, and What I Lived For", "Reading",
    "Sounds", "Solitude", "Visitors", "The Bean-Field", "The Village",
    "The Ponds", "Baker Farm", "Higher Laws", "Brute Neighbors",
    "House-Warming", "Former Inhabitants; and Winter Visitors",
    "Winter Animals", "The Pond in Winter", "Spring", "Conclusion"]
def split_walden(text):
    lines = text.split("\n")
    idx = [(i, ln.strip().rstrip(".")) for i, ln in enumerate(lines)
           if ln.strip().rstrip(".") in WALDEN_CHAPTERS]
    chunks = {}
    for j, (i, title) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        chunks[title] = "\n".join(lines[i + 1:end])
    return chunks
wch = split_walden(walden)
for probe in ["be not afflicted", "milk a cow", "Bhagvat-Geeta", "Bhagvat Geeta"]:
    for ch, txt in wch.items():
        if probe.lower() in txt.lower():
            print(f"'{probe}' -> chapter: {ch}")
# per-essay fingerprint
ESSAYS = ["HISTORY", "SELF-RELIANCE", "COMPENSATION", "SPIRITUAL LAWS", "LOVE",
          "FRIENDSHIP", "PRUDENCE", "HEROISM", "THE OVER-SOUL", "CIRCLES",
          "INTELLECT", "ART"]
def split_emerson(text):
    lines = text.split("\n")
    idx = [(i, ln.strip().rstrip(".")) for i, ln in enumerate(lines)
           if ln.strip().rstrip(".") in ESSAYS]
    chunks = {}
    for j, (i, title) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        chunks[title] = "\n".join(lines[i + 1:end])
    return chunks
em = split_emerson(texts["emerson_essays1"])
print("\nEmerson essay fingerprints (gita / upan / analects / kjv / sartor):")
em_fp = {}
for title, chunk in em.items():
    if len(words(chunk)) < 200:
        continue
    fp = fp_share(chunk)
    em_fp[title.title()] = fp
    print(f"  {title.title():18s} {fp}")

json.dump({"containment": final, "emerson_essay_fingerprints": em_fp},
          open(os.path.join(OUT, "results.json"), "w"), indent=2)
print("\nANALYSIS V3 DONE")
