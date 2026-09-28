"""Build a passage-level corpus from 14 public-domain wisdom & self-help texts.

Sources: Project Gutenberg (IDs recorded in WORKS). Four texts reuse the
cleaned copies from the 2026-09-19 build (tao, dhammapada, emerson, walden);
the rest are downloaded fresh and verified by title header.

Output: data/corpus.csv with columns:
  passage_id, work, title, author, year, tradition, group, passage, n_chars
group in {canon, philosophy, selfhelp}:
  canon      = ancient wisdom traditions (the "originals")
  philosophy = 19th-c. transcendentalism (the bridge)
  selfhelp   = 1859-1915 commercial self-help (the "industry")
"""
import csv, re, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
TEXTS = os.path.join(PROJ, "data", "texts")
OLD = os.path.expanduser("~/workspace/passion-projects/2026-09-19/laozi-and-emerson/data/texts")

WORKS = [
    # work, file, title, author, year, tradition, group
    ("tao-te-ching",      f"{OLD}/tao-te-ching.txt",   "Tao Te Ching", "Laozi", -400, "taoist", "canon"),
    ("analects",          f"{TEXTS}/pg4094.txt",        "Analects", "Confucius (tr. Legge)", -479, "confucian", "canon"),
    ("dhammapada",        f"{OLD}/dhammapada.txt",       "Dhammapada", "Buddha (tr. Müller)", -300, "buddhist", "canon"),
    ("bhagavad-gita",     f"{TEXTS}/pg2388.txt",        "Bhagavad Gita", "Vyasa (tr. Arnold)", -200, "hindu", "canon"),
    ("art-of-war",        f"{TEXTS}/pg132.txt",         "The Art of War", "Sun Tzu (tr. Giles)", -500, "strategist", "canon"),
    ("proverbs",          f"{TEXTS}/pg10.txt",          "Proverbs (KJV)", "Solomon (trad.)", -700, "hebrew", "canon"),
    ("ecclesiastes",      f"{TEXTS}/pg10.txt",          "Ecclesiastes (KJV)", "Qoheleth (trad.)", -300, "hebrew", "canon"),
    ("meditations",       f"{TEXTS}/pg2680.txt",        "Meditations", "Marcus Aurelius (tr. Long)", 180, "stoic", "canon"),
    ("emerson-essays",    f"{OLD}/emerson-essays.txt",  "Essays, First Series", "Ralph Waldo Emerson", 1841, "transcendentalist", "philosophy"),
    ("thoreau-walden",    f"{OLD}/thoreau-walden.txt",  "Walden", "Henry David Thoreau", 1854, "transcendentalist", "philosophy"),
    ("smiles-self-help",  f"{TEXTS}/pg935.txt",         "Self-Help", "Samuel Smiles", 1859, "selfhelp", "selfhelp"),
    ("barnum-money",      f"{TEXTS}/pg8581.txt",        "The Art of Money Getting", "P. T. Barnum", 1880, "selfhelp", "selfhelp"),
    ("allen-thinketh",    f"{TEXTS}/pg4507.txt",        "As a Man Thinketh", "James Allen", 1903, "selfhelp", "selfhelp"),
    ("wattles-rich",      f"{TEXTS}/pg59844.txt",       "The Science of Getting Rich", "Wallace D. Wattles", 1910, "selfhelp", "selfhelp"),
    ("conwell-acres",     f"{TEXTS}/pg34258.txt",       "Acres of Diamonds", "Russell Conwell", 1915, "selfhelp", "selfhelp"),
]

START_RE = re.compile(r"\*\*\* ?START OF (THIS|THE) PROJECT GUTENBERG EBOOK", re.I)
END_RE = re.compile(r"\*\*\* ?END OF (THIS|THE) PROJECT GUTENBERG EBOOK", re.I)

def strip_gutenberg(text):
    lines = text.splitlines()
    start, end = 0, len(lines)
    for i, ln in enumerate(lines):
        if START_RE.search(ln):
            start = i + 1
            break
    for i, ln in enumerate(lines):
        if END_RE.search(ln):
            end = i
            break
    return "\n".join(lines[start:end])

def kjv_slice(path, book):
    """Extract one KJV book (Proverbs/Ecclesiastes) by line markers."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    if book == "proverbs":
        lo = next(i for i, l in enumerate(lines) if l.strip() == "The Proverbs" and i > 50000)
        hi = next(i for i, l in enumerate(lines) if l.strip() == "Ecclesiastes" and i > lo)
    else:
        lo = next(i for i, l in enumerate(lines) if l.strip() == "Ecclesiastes" and i > 50000)
        hi = next(i for i, l in enumerate(lines) if l.strip() == "The Song of Solomon" and i > lo)
    return "\n".join(lines[lo:hi])

JUNK_PATTERNS = [
    r"^(chapter|book|part|section|contents?)\b",
    r"^\d+\s*$", r"^[ivxlcdm]+\.?\s*$",
    r"project gutenberg", r"^produced by", r"^transcriber",
]

def split_long(p, maxlen=550):
    """Split an over-long paragraph into sentence chunks <= maxlen chars."""
    if len(p) <= 700:
        return [p]
    sents = re.split(r"(?<=[.!?;])\s+", p)
    chunks, cur = [], ""
    for s in sents:
        if cur and len(cur) + 1 + len(s) > maxlen:
            chunks.append(cur); cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        chunks.append(cur)
    return chunks

CJK_RE = re.compile(r"[⺀-鿿　-〿＀-￯]")
GILES_JUNK = ("giles", "translation", "french jesuit", "commentator", "tu yu",
              "mei yao", "wang hsi", "chia lin", "tu mu", "ho yen", "chang y",
              "ts‘ao kung", "ch‘ên hao", "hsu lu", "pi i-hsun", "wu yueh")
INDEX_RE = re.compile(r"\d{1,4}–\d{1,4}|\(\d{1,4}\)")
MEDIT_JUNK_RE = re.compile(r"frag\.|\(nauck\)|teubner|rendall|fronto|stich|^[ivxlcdm]+\.\s*\"", re.I)

def clean_paragraphs(text, work):
    text = strip_gutenberg(text)
    # join hard-wrapped lines: a newline inside a paragraph is a space
    paras, buf = [], []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            if buf:
                paras.append(" ".join(buf)); buf = []
        else:
            buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    out = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if work == "analects":
            p = CJK_RE.sub("", p)  # drop untranslated Chinese, keep Legge's English
            p = re.sub(r"\s+", " ", p).strip()
        if len(p) < 40:
            continue
        low = p.lower()
        if any(re.search(pat, low) for pat in JUNK_PATTERNS):
            continue
        if len(p.split()) < 8:
            continue
        if work == "art-of-war" and any(j in low for j in GILES_JUNK):
            continue
        if work == "meditations" and MEDIT_JUNK_RE.search(p):
            continue
        if INDEX_RE.search(p):
            continue  # book index / table-of-contents entries
        for chunk in split_long(p):
            if len(chunk) >= 40 and len(chunk.split()) >= 8:
                # drop title/byline paragraphs (mostly uppercase) and footnotes
                alpha = [c for c in chunk if c.isalpha()]
                if alpha and sum(c.isupper() for c in alpha) / len(alpha) > 0.6:
                    continue
                if chunk.startswith("[") or "FN#" in chunk:
                    continue
                out.append(chunk)
    return out

def main():
    rows = []
    pid = 0
    for work, path, title, author, year, tradition, group in WORKS:
        if work in ("proverbs", "ecclesiastes"):
            raw = kjv_slice(path, work)
        else:
            raw = open(path, encoding="utf-8", errors="replace").read()
        paras = clean_paragraphs(raw, work)
        for p in paras:
            rows.append({
                "passage_id": f"{work}-{pid:05d}", "work": work, "title": title,
                "author": author, "year": year, "tradition": tradition,
                "group": group, "passage": p, "n_chars": len(p),
            })
            pid += 1
        print(f"{work:16s} {len(paras):5d} passages")
    out = os.path.join(PROJ, "data", "corpus.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"total {len(rows)} passages -> {out}")
    by_work = {}
    for r in rows:
        by_work.setdefault(r["work"], 0)
        by_work[r["work"]] += 1
    with open(os.path.join(PROJ, "data", "corpus_summary.json"), "w") as f:
        json.dump({"total": len(rows), "by_work": by_work}, f, indent=2)

if __name__ == "__main__":
    main()
