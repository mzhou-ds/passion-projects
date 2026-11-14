#!/usr/bin/env python3
"""Build #68 analysis v2: exact-word mentions, quotation inspection,
vocabulary fingerprints, chapter-level TF-IDF."""
import json, os, re
import numpy as np
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
CD_START = walden_full.find("I heartily accept the motto")
walden = walden_full[:CD_START] if CD_START > 0 else walden_full
print(f"Walden truncated: {len(words(walden)):,} words (Civil Disobedience removed)")
texts = {
    "walden": walden,
    "emerson_essays1": load("emerson_essays1"),
    "emerson_nature": load("emerson_nature"),
    "gita_arnold": load("gita_arnold"),
    "upanishads_muller": load("upanishads_muller"),
    "vishnu_purana": load("vishnu_purana"),
    "kjv": load("kjv"),
    "sartor": load("sartor"),
}

# ---------------------------------------------------------------- 1. mentions
EAST = ["Bhagavat", "Geeta", "Gita", "Veda", "Vedanta", "Menu", "Manu", "Brahma",
        "Brahman", "Krishna", "Buddha", "Buddhist", "Confucius", "Zoroaster",
        "Zendavesta", "Koran", "Mohammed", "Mahomet", "Tao", "Hindoo", "Hindu",
        "Upanishad", "Purana", "Sakuntala", "Vishnu", "Shiva", "Yoga", "Nirvana"]
WEST = ["Bible", "Testament", "Moses", "Jesus", "Christ", "Gospel", "Psalm",
        "Apostle", "Scripture", "Jehovah", "Sabbath", "Christian", "Christianity"]

def exact_count(text, word):
    return len(re.findall(rf"\b{re.escape(word)}\b", text, re.I))

mention_rows = {}
contexts = defaultdict(list)
for t in ["walden", "emerson_essays1", "emerson_nature"]:
    row = {"words": len(words(texts[t])), "east": {}, "west": {}}
    for w in EAST:
        c = exact_count(texts[t], w)
        if c:
            row["east"][w] = c
            for m in re.finditer(rf"\b{re.escape(w)}\b", texts[t], re.I):
                s = max(0, m.start() - 160); e = min(len(texts[t]), m.end() + 160)
                contexts[f"{t} :: EAST :: {w}"].append(
                    re.sub(r"\s+", " ", texts[t][s:e]).strip())
    for w in WEST:
        c = exact_count(texts[t], w)
        if c:
            row["west"][w] = c
    row["east_total"] = sum(row["east"].values())
    row["west_total"] = sum(row["west"].values())
    mention_rows[t] = row
    print(f"\n== {t} ==")
    print("  EAST:", row["east"], "TOTAL", row["east_total"])
    print("  WEST:", row["west"], "TOTAL", row["west_total"])
    print(f"  per 10k words: east {10000*row['east_total']/row['words']:.2f}  west {10000*row['west_total']/row['words']:.2f}")

json.dump(mention_rows, open(os.path.join(OUT, "mentions.json"), "w"), indent=2)
json.dump({k: v[:40] for k, v in contexts.items()},
          open(os.path.join(OUT, "mention_contexts.json"), "w"), indent=2)
print("\n--- Eastern mention contexts (Walden) ---")
for k, v in contexts.items():
    if k.startswith("walden :: EAST"):
        for c in v[:2]:
            print(f"[{k}] ...{c}...")

# ---------------------------------------------------------------- 2. quotation inspection (KJV 6-grams in Walden)
src_grams = {s: {6: ngrams(words(texts[s]), 6), 8: ngrams(words(texts[s]), 8)}
             for s in ["gita_arnold", "upanishads_muller", "vishnu_purana", "kjv", "sartor"]}
tw = words(texts["walden"])
for s in ["kjv", "gita_arnold", "upanishads_muller", "vishnu_purana"]:
    hits = ngrams(tw, 6) & src_grams[s][6]
    print(f"\nWalden 6-gram hits vs {s}: {len(hits)}")
    for h in sorted(hits)[:25]:
        print("   ", " ".join(h))
ts = sentences(texts["walden"])
kjv_sent = [x for x in ts if len(words(x)) >= 6 and (ngrams(words(x), 6) & src_grams["kjv"][6])]
print(f"\nWalden sentences containing a KJV 6-gram: {len(kjv_sent)}")
for x in kjv_sent[:12]:
    print("  -", x[:220])

# ---------------------------------------------------------------- 3. Emerson essay split (ALL-CAPS headings)
ESSAYS = ["HISTORY", "SELF-RELIANCE", "COMPENSATION", "SPIRITUAL LAWS", "LOVE",
          "FRIENDSHIP", "PRUDENCE", "HEROISM", "THE OVER-SOUL", "CIRCLES",
          "INTELLECT", "ART"]
def split_emerson(text):
    lines = text.split("\n")
    idx = []
    for i, ln in enumerate(lines):
        s = ln.strip().rstrip(".")
        if s in ESSAYS:
            idx.append((i, s))
    chunks = {}
    for j, (i, title) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        # skip the contents listing: keep the LAST occurrence's chunk
        chunks[title] = "\n".join(lines[i + 1:end])
    return chunks
em = split_emerson(texts["emerson_essays1"])
print(f"\nEmerson essays found: {len(em)} -> {list(em)}")
em_rows = []
for title, chunk in em.items():
    ew = words(chunk)
    if len(ew) < 200:
        continue
    d = {"essay": title.title(), "words": len(ew)}
    for s in ["gita_arnold", "upanishads_muller", "vishnu_purana", "kjv", "sartor"]:
        c6 = len(ngrams(ew, 6) & src_grams[s][6])
        d[s] = {"ngram6_hits": c6}
    d["east_mentions"] = sum(exact_count(chunk, w) for w in EAST)
    d["west_mentions"] = sum(exact_count(chunk, w) for w in WEST)
    em_rows.append(d)
    print(f"  {d['essay']:18s} {len(ew):6d}w  kjv6={d['kjv']['ngram6_hits']:3d}"
          f"  gita6={d['gita_arnold']['ngram6_hits']} upan6={d['upanishads_muller']['ngram6_hits']}"
          f"  east_ment={d['east_mentions']} west_ment={d['west_mentions']}")
json.dump(em_rows, open(os.path.join(OUT, "emerson_essays.json"), "w"), indent=2)

# ---------------------------------------------------------------- 4. vocabulary fingerprint
# distinctive words per source: top TF-IDF terms of source vs the other sources
sources = ["gita_arnold", "upanishads_muller", "vishnu_purana", "kjv", "sartor"]
vec = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 1))
X = vec.fit_transform([texts[s] for s in sources])
vocab = np.array(vec.get_feature_names_out())
finger = {}
for i, s in enumerate(sources):
    row = X[i].toarray()[0]
    top = vocab[np.argsort(row)[-150:][::-1]]
    finger[s] = set(top.tolist())
    print(f"{s}: fingerprint e.g. {sorted(finger[s])[:12]}")

def fingerprint_share(text):
    ws = [w for w in words(text) if w.isalpha()]
    c = Counter(ws)
    tot = sum(c.values())
    return {s: round(100 * sum(c[w] for w in finger[s]) / tot, 3) for s in sources}

print("\nVocabulary fingerprint: % of content words in each source's top-150 distinctive words")
for t in ["walden", "emerson_essays1", "emerson_nature"]:
    print(f"  {t}: {fingerprint_share(texts[t])}")

# Walden chapters fingerprint
WALDEN_CHAPTERS = ["Economy", "Where I Lived, and What I Lived For", "Reading",
    "Sounds", "Solitude", "Visitors", "The Bean-Field", "The Village",
    "The Ponds", "Baker Farm", "Higher Laws", "Brute Neighbors",
    "House-Warming", "Former Inhabitants; and Winter Visitors",
    "Winter Animals", "The Pond in Winter", "Spring", "Conclusion"]
def split_walden(text):
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
wch = split_walden(walden)
print(f"Walden chapters: {len(wch)}")
chap_fp = []
for ch in WALDEN_CHAPTERS:
    if ch not in wch:
        continue
    fp = fingerprint_share(wch[ch])
    east_ment = sum(exact_count(wch[ch], w) for w in EAST)
    west_ment = sum(exact_count(wch[ch], w) for w in WEST)
    chap_fp.append({"chapter": ch, "words": len(words(wch[ch])),
                    "fingerprint": fp, "east_mentions": east_ment,
                    "west_mentions": west_ment})
    print(f"  {ch:45s} {len(words(wch[ch])):6d}w  fp={fp}  east={east_ment} west={west_ment}")
json.dump(chap_fp, open(os.path.join(OUT, "walden_chapters_fp.json"), "w"), indent=2)

# ---------------------------------------------------------------- 5. chapter-level TF-IDF max similarity
# split Gita into discourses, Upanishads into books, Sartor into chapters
def split_gita(text):
    parts = re.split(r"\n\s*DISCOURSE [IVX]+\.?\s*\n", text)
    return [p for p in parts if len(p.split()) > 300]
def split_generic(text, pat):
    parts = re.split(pat, text)
    return [p for p in parts if len(p.split()) > 300]

subdocs = {}
for i, p in enumerate(split_gita(texts["gita_arnold"])):
    subdocs[f"gita_disc{i+1}"] = p
up = split_generic(texts["upanishads_muller"], r"\n\s*(?:THE )?(?:CHHÂNDOGYA|BRIHADÂRANYAKA|TAITTIRÎYA|AITERAYA|KAUSHI|KATHA|MUNDAKA|SVETASVATARA|PRASNA|MAITRÂYANÎYA)[^\n]*\n")
for i, p in enumerate(up):
    subdocs[f"upan_{i+1}"] = p
sa = split_generic(texts["sartor"], r"\n\s*CHAPTER [IVX]+\.?\s*\n")
for i, p in enumerate(sa):
    subdocs[f"sartor_ch{i+1}"] = p
print(f"subdocs: gita {len(split_gita(texts['gita_arnold']))}, upan {len(up)}, sartor {len(sa)}")

docs = {f"walden::{ch}": wch[ch] for ch in WALDEN_CHAPTERS if ch in wch}
docs.update(subdocs)
keys = list(docs.keys())
v2 = TfidfVectorizer(max_features=20000, stop_words="english", ngram_range=(1, 2))
X2 = v2.fit_transform([docs[k] for k in keys])
S2 = cosine_similarity(X2)
rows = []
for i, k in enumerate(keys):
    if not k.startswith("walden::"):
        continue
    ch = k.split("::", 1)[1]
    best = {}
    for grp in ["gita_disc", "upan_", "sartor_ch"]:
        sims = [float(S2[i, j]) for j, k2 in enumerate(keys) if k2.startswith(grp)]
        best[grp] = round(max(sims), 3) if sims else 0.0
    rows.append({"chapter": ch, **best})
    print(f"  {ch:45s} max-sim gita={best['gita_disc']:.3f} upan={best['upan_']:.3f} sartor={best['sartor_ch']:.3f}")
json.dump(rows, open(os.path.join(OUT, "walden_chapter_maxsim.json"), "w"), indent=2)
print("\nANALYSIS V2 DONE")
