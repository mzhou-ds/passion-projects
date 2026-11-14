#!/usr/bin/env python3
"""Build #68: The Eastern DNA of Transcendentalism.

Question: how much of Emerson and Thoreau is, literally, Eastern scripture?
Method: word n-gram containment (quotation) + TF-IDF cosine (absorption)
of three transcendentalist targets against four Eastern sources and two
Western controls, all public-domain Project Gutenberg editions.
"""
import json, os, re, math, random
import numpy as np
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "data")
CHARTS = os.path.join(BASE, "charts")
os.makedirs(CHARTS, exist_ok=True)

random.seed(68)

TARGETS = ["walden", "emerson_essays1", "emerson_nature"]
SOURCES = ["gita_arnold", "upanishads_muller", "vishnu_purana"]
CONTROLS = ["kjv", "sartor"]

# ---------------------------------------------------------------- cleaning
def clean(text):
    # strip Gutenberg header/footer
    m = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.S)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.S)
    if m:
        text = text[:m.start()]
    # drop footnote markers / page numbers / illustration captions are left in;
    # they are rare and symmetric across texts, so they add noise, not bias.
    return text

def words(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.split()

def sentences(text):
    # crude sentence split on . ! ? followed by space+capital; good enough
    # for containment counts (both sides get the same treatment).
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]

def ngrams(ws, n):
    return set(tuple(ws[i:i + n]) for i in range(len(ws) - n + 1))

def load(key):
    with open(os.path.join(RAW, f"{key}.txt"), encoding="utf-8", errors="ignore") as f:
        return clean(f.read())

# ---------------------------------------------------------------- load
texts = {}
for k in TARGETS + SOURCES + CONTROLS:
    p = os.path.join(RAW, f"{k}.txt")
    if not os.path.exists(p):
        print(f"MISSING {k}")
        continue
    texts[k] = load(k)
    print(f"{k}: {len(texts[k]):,} chars, {len(words(texts[k])):,} words")

# source n-gram sets (6 and 8) and sentence sets
src_grams = {}
for s in SOURCES + CONTROLS:
    w = words(texts[s])
    src_grams[s] = {6: ngrams(w, 6), 8: ngrams(w, 8)}
    print(f"{s}: {len(src_grams[s][6]):,} distinct 6-grams, {len(src_grams[s][8]):,} distinct 8-grams")

# ---------------------------------------------------------------- main table
def containment(target_words, src, n):
    tg = ngrams(target_words, n)
    if not tg:
        return 0.0, 0, len(tg)
    hit = len(tg & src_grams[src][n])
    return hit / len(tg), hit, len(tg)

results = {}
for t in TARGETS:
    tw = words(texts[t])
    ts = sentences(texts[t])
    row = {"words": len(tw), "sentences": len(ts)}
    for s in SOURCES + CONTROLS:
        c6, h6, tot6 = containment(tw, s, 6)
        c8, h8, tot8 = containment(tw, s, 8)
        # sentence-level: share of target sentences containing a 6-gram hit
        sw = [words(x) for x in ts]
        sent_hits = 0
        for wlist in sw:
            if len(wlist) >= 6 and (ngrams(wlist, 6) & src_grams[s][6]):
                sent_hits += 1
        row[s] = {
            "ngram6_share": round(c6, 5), "ngram6_hits": h6, "ngram6_total": tot6,
            "ngram8_share": round(c8, 5), "ngram8_hits": h8, "ngram8_total": tot8,
            "sentence_share": round(sent_hits / max(len(ts), 1), 4),
            "sentences_hit": sent_hits,
        }
    results[t] = row
    print(f"\n== {t} ==")
    for s in SOURCES + CONTROLS:
        r = row[s]
        print(f"  {s:18s} 6g {r['ngram6_share']:.4%} ({r['ngram6_hits']}/{r['ngram6_total']})"
              f"  8g {r['ngram8_share']:.4%}  sent {r['sentence_share']:.2%}")

with open(os.path.join(OUT, "containment.json"), "w") as f:
    json.dump(results, f, indent=2)

# ---------------------------------------------------------------- Walden chapters
WALDEN_CHAPTERS = ["Economy", "Where I Lived, and What I Lived For", "Reading",
    "Sounds", "Solitude", "Visitors", "The Bean-Field", "The Village",
    "The Ponds", "Baker Farm", "Higher Laws", "Brute Neighbors",
    "House-Warming", "Former Inhabitants; and Winter Visitors",
    "Winter Animals", "The Pond in Winter", "Spring", "Conclusion"]

def split_walden(text):
    # Gutenberg #205 headings are like "\n\nEconomy.\n" or in caps; find each
    # chapter title as a standalone line (allowing trailing period).
    lines = text.split("\n")
    idx = []
    for i, ln in enumerate(lines):
        s = ln.strip().rstrip(".")
        if s in WALDEN_CHAPTERS:
            idx.append((i, s))
    chunks = {}
    for j, (i, title) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        chunks[title] = "\n".join(lines[i + 1:end])
    return chunks

walden_chapters = split_walden(texts["walden"])
print(f"\nWalden chapters found: {len(walden_chapters)} / {len(WALDEN_CHAPTERS)}")
print("missing:", [c for c in WALDEN_CHAPTERS if c not in walden_chapters])

chap_rows = []
for ch in WALDEN_CHAPTERS:
    if ch not in walden_chapters:
        continue
    cw = words(walden_chapters[ch])
    cs = sentences(walden_chapters[ch])
    d = {"chapter": ch, "words": len(cw), "sentences": len(cs)}
    for s in SOURCES + CONTROLS:
        c6, h6, _ = containment(cw, s, 6)
        c8, h8, _ = containment(cw, s, 8)
        d[s] = {"ngram6_share": round(c6, 5), "ngram6_hits": h6,
                "ngram8_share": round(c8, 5), "ngram8_hits": h8}
    chap_rows.append(d)
    print(f"  {ch:45s} {len(cw):6d}w  gita6 {d['gita_arnold']['ngram6_share']:.4%}"
          f"  upan6 {d['upanishads_muller']['ngram6_share']:.4%}  kjv6 {d['kjv']['ngram6_share']:.4%}")

with open(os.path.join(OUT, "walden_chapters.json"), "w") as f:
    json.dump(chap_rows, f, indent=2)

# permutation test: is Higher Laws' eastern 6-gram share above the book mean?
# Shuffle sentences across chapters, recompute Higher Laws share, 2000 draws.
east = ["gita_arnold", "upanishads_muller", "vishnu_purana"]
all_sents = []
chap_sent_count = {}
for ch in WALDEN_CHAPTERS:
    if ch not in walden_chapters:
        continue
    ss = sentences(walden_chapters[ch])
    chap_sent_count[ch] = len(ss)
    all_sents.extend(ss)
hl_n = chap_sent_count.get("Higher Laws", 0)
hl_text = walden_chapters.get("Higher Laws", "")
hl_words = words(hl_text)
obs = sum(containment(hl_words, s, 6)[0] for s in east)

def east_share_of_wordlist(wl):
    return sum(containment(wl, s, 6)[0] for s in east)

null = []
for _ in range(2000):
    samp = random.sample(all_sents, hl_n)
    wl = words(" ".join(samp))
    null.append(east_share_of_wordlist(wl))
null = np.array(null)
p = (np.sum(null >= obs) + 1) / (len(null) + 1)
print(f"\nHigher Laws eastern 6g share sum = {obs:.5f}; null mean {null.mean():.5f}, "
      f"95th pct {np.percentile(null, 95):.5f}; permutation p = {p:.4f}")

# ---------------------------------------------------------------- TF-IDF absorption
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

docs = {}
for ch in WALDEN_CHAPTERS:
    if ch in walden_chapters:
        docs[f"walden::{ch}"] = walden_chapters[ch]
for s in SOURCES + CONTROLS:
    docs[f"source::{s}"] = texts[s]

vec = TfidfVectorizer(max_features=20000, stop_words="english", ngram_range=(1, 2))
X = vec.fit_transform(list(docs.values()))
keys = list(docs.keys())
sim = cosine_similarity(X)
tfidf_rows = []
for i, k in enumerate(keys):
    if not k.startswith("walden::"):
        continue
    ch = k.split("::", 1)[1]
    d = {"chapter": ch}
    for j, k2 in enumerate(keys):
        if k2.startswith("source::"):
            d[k2.split("::", 1)[1]] = round(float(sim[i, j]), 4)
    tfidf_rows.append(d)
with open(os.path.join(OUT, "walden_tfidf.json"), "w") as f:
    json.dump(tfidf_rows, f, indent=2)
print("\nTF-IDF chapter x source cosine (top per chapter):")
for d in tfidf_rows:
    best = max((v, k) for k, v in d.items() if k != "chapter")
    print(f"  {d['chapter']:45s} best={best[1]} {best[0]:.3f}  gita={d['gita_arnold']:.3f} kjv={d['kjv']:.3f}")

# Emerson essays: split by essay if headings found
def split_emerson(text):
    essays = ["History", "Self-Reliance", "Compensation", "Spiritual Laws",
              "Love", "Friendship", "Prudence", "Heroism", "The Over-Soul",
              "Circles", "Intellect", "Art"]
    lines = text.split("\n")
    idx = []
    for i, ln in enumerate(lines):
        s = ln.strip().rstrip(".")
        if s in essays:
            idx.append((i, s))
    chunks = {}
    for j, (i, title) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        chunks[title] = "\n".join(lines[i + 1:end])
    return chunks

em_chunks = split_emerson(texts["emerson_essays1"])
print(f"\nEmerson essays found: {len(em_chunks)}")
em_rows = []
for title, chunk in em_chunks.items():
    ew = words(chunk)
    d = {"essay": title, "words": len(ew)}
    for s in SOURCES + CONTROLS:
        c6, h6, _ = containment(ew, s, 6)
        d[s] = {"ngram6_share": round(c6, 5), "ngram6_hits": h6}
    em_rows.append(d)
    print(f"  {title:18s} {len(ew):6d}w  gita6 {d['gita_arnold']['ngram6_share']:.4%}"
          f"  upan6 {d['upanishads_muller']['ngram6_share']:.4%}  kjv6 {d['kjv']['ngram6_share']:.4%}")
with open(os.path.join(OUT, "emerson_essays.json"), "w") as f:
    json.dump(em_rows, f, indent=2)

# ---------------------------------------------------------------- verbatim extracts
def matching_sentences(target_text, src, n=6, limit=12):
    out = []
    for sent in sentences(target_text):
        wl = words(sent)
        if len(wl) >= n and (ngrams(wl, n) & src_grams[src][n]):
            out.append(sent.strip())
            if len(out) >= limit:
                break
    return out

extracts = {}
for t in TARGETS:
    for s in SOURCES:
        ex = matching_sentences(texts[t], s)
        if ex:
            extracts[f"{t} :: {s}"] = ex
with open(os.path.join(OUT, "verbatim_extracts.json"), "w") as f:
    json.dump(extracts, f, indent=2)
print(f"\nextract groups with matches: {len(extracts)}")
for k, v in extracts.items():
    print(f"  {k}: {len(v)} sampled sentences")
    for s in v[:2]:
        print(f"    - {s[:200]}")

print("\nANALYSIS DONE")
