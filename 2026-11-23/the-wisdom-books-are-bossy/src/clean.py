"""Clean the raw texts into analysis-ready plain text.

Rules (documented, reproducible):
- Gutenberg texts: keep only between the START and END ebook markers.
- Wikisource texts: cut header/navigation junk before a per-text anchor,
  cut the public-domain license footer, drop footnote chunks (marked with
  the Wikisource footnote arrow), drop '[ edit ]' markers.
- KJV extracts: strip chapter:verse numbers wherever they occur.
- General: strip zero-width characters, collapse whitespace, keep one
  sentence per line-break structure (newlines preserved as single spaces
  inside paragraphs, paragraph breaks kept as blank lines).
"""
import re, os, json

RAW = "data/raw"
OUT = "data/processed/clean"
os.makedirs(OUT, exist_ok=True)

def gutenberg(txt):
    m = re.search(r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", txt, re.S)
    e = re.search(r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", txt, re.S)
    if m and e:
        return txt[m.end():e.start()]
    return txt

def wikisource(txt, anchor=None, footers=("This work was published before January 1, 1931",
                                          "This work is in the public domain")):
    if anchor:
        i = txt.find(anchor)
        assert i >= 0, f"anchor not found: {anchor}"
        txt = txt[i:]
    for f in footers:
        j = txt.find(f)
        if j > 0:
            txt = txt[:j]
    # stray footnote arrows left over from inline markers
    txt = txt.replace("↑", " ")
    txt = re.sub(r"\[\s*edit\s*\]", " ", txt)
    return txt

def general(txt):
    # spaced small-caps from Wikisource rendering: 'B e not puffed-up' -> 'Be not...'
    txt = re.sub(r"\b([A-Z]) ([a-z])\b", r"\1\2", txt)
    for a, b in [("W hen", "When"), ("T he", "The"), ("I f", "If"), ("A nd", "And"),
                 ("F or", "For"), ("S o", "So"), ("O f", "Of")]:
        txt = txt.replace(a, b)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = txt.replace("\u200b", "").replace("\ufeff", "").replace("\u00a0", " ")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def kjv_numbers(txt):
    txt = re.sub(r"\b\d+:\d+\b", " ", txt)          # verse numbers anywhere
    txt = re.sub(r"(?m)^\s*\d+\s*$", " ", txt)      # bare chapter numbers
    txt = re.sub(r"^or The Preacher\s*", "", txt)   # title-page leftover
    return txt

JOBS = [
    # (raw file, clean file, cleaner)
    ("tao_te_ching_legge.txt", "tao_te_ching.txt",
     lambda t: wikisource(t, anchor="The Tao that can be described")),
    ("enchiridion_rolleston.txt", "enchiridion.txt",
     lambda t: wikisource(t, anchor="things that exist, some depend upon ourselves")),
    ("dhammapada_muller.txt", "dhammapada.txt",
     lambda t: wikisource(t, anchor="All that we are is the result")),
    ("zhuangzi_giles.txt", "zhuangzi.txt",
     lambda t: wikisource(t, anchor="CHAPTER I.")),
    ("meditations_haines.txt", "meditations.txt",
     lambda t: wikisource(t, anchor="BOOK I")),
    ("seneca_letters_1_20.txt", "seneca_letters.txt",
     lambda t: wikisource(t, anchor="THE EPISTLES OF SENECA")),
    ("analects_legge.txt", "analects.txt", gutenberg),
    ("gita_arnold.txt", "gita.txt", gutenberg),
    ("upanishads_muller.txt", "upanishads.txt", gutenberg),
    ("emerson_essays1.txt", "emerson_essays.txt", gutenberg),
    ("walden.txt", "walden.txt", gutenberg),
    ("ecclesiastes_kjv.txt", "ecclesiastes.txt", kjv_numbers),
    ("proverbs_kjv.txt", "proverbs.txt", kjv_numbers),
]

report = {}
for raw, clean, fn in JOBS:
    txt = open(os.path.join(RAW, raw), encoding="utf-8").read()
    before = len(txt.split())
    txt = general(fn(txt))
    after = len(txt.split())
    open(os.path.join(OUT, clean), "w", encoding="utf-8").write(txt)
    report[clean] = {"raw_words": before, "clean_words": after}
    print(f"{clean}: {before:,} -> {after:,} words")

json.dump(report, open("data/processed/cleaning_report.json", "w"), indent=2)
