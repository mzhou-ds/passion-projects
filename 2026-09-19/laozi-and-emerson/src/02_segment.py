"""Segment the 4 corpus texts into analysis units: sentences within sections.

Sections:
  - Tao Te Ching: 81 chapters ("Ch. N")
  - Dhammapada: 26 chapters, unit = verse (chapter + verse number)
  - Emerson Essays: 12 essays
  - Walden: chapters (Economy, ...)

Output: data/units.csv with columns:
  unit_id, work, tradition, section, sub_id (chapter/verse no. where known),
  sent_idx (position within section), text, n_words
"""
import re
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
TEXTS = DATA / "texts"

ABBREV = {"mr", "mrs", "ms", "dr", "st", "jr", "sr", "vs", "etc", "no", "i.e", "e.g",
          "prof", "rev", "hon", "gov", "sen", "rep", "gen", "col", "capt", "lt",
          "vol", "ch", "fig", "dept", "univ", "ave", "blvd", "rd", "co", "inc"}


def split_sentences(text):
    # normalize whitespace, protect abbreviations, then split on end punctuation
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split(" ")
    out, buf = [], []
    for tok in tokens:
        buf.append(tok)
        core = tok.strip('"\u201c\u201d\'()[]').rstrip(".,;:!?").lower()
        bare = re.sub(r"[^a-z.]", "", tok.lower())
        is_abbrev = core in ABBREV or re.fullmatch(r"[a-z]\.", bare or "")
        if re.search(r"[.!?…][\"'\u201d)]*$", tok) and not is_abbrev:
            out.append(" ".join(buf).strip())
            buf = []
    if buf:
        out.append(" ".join(buf).strip())
    return [s for s in out if s]


def words(s):
    return len(re.findall(r"[A-Za-z']+", s))


def clean_paragraph(p):
    p = re.sub(r"\s+", " ", p).strip()
    # drop Gutenberg-ish artifacts and page markers
    p = re.sub(r"\[Pg \d+\]", "", p)
    return p.strip()


def split_chapters_tao(text):
    # chapter markers: "Ch. N. 1." / "N. 1." normally; chapters 6, 21, 68 use
    # "N." alone on a line; chapters 11, 24 use "N." + text. Verse markers
    # ("N." + text, or "N." alone mid-chapter) are disambiguated by tracking
    # the expected chapter number in document order.
    text = re.sub(r"\bCh\.\s*(\d{1,2})\.", r"\1.", text)
    marks = []
    for m in re.finditer(r"(?m)^\s*(\d{1,2})\.[^\S\n]*(1\.)?([^\n]*)", text):
        rest = m.group(3).strip()
        marks.append((m.start(), int(m.group(1)), bool(m.group(2)),
                      rest == ""))
    bounds, expected = [], 1
    for pos, num, has_one, alone in marks:
        if num == expected and (has_one or alone or num in (11, 24)):
            bounds.append((expected, pos))
            expected += 1
    bounds.append((82, len(text)))
    chapters = []
    for i in range(len(bounds) - 1):
        n, start = bounds[i]
        body = text[start:bounds[i + 1][1]]
        body = re.sub(r"^\s*\d{1,2}\.\s*(1\.)?", "", body, count=1)
        body = re.sub(r"(?m)^\s*\d+\.\s*", " ", body)  # strip verse numbers
        chapters.append((f"Ch. {n}", n, body))
    assert [c[1] for c in chapters] == list(range(1, 82)), \
        f"tao chapters parsed: {[c[1] for c in chapters]}"
    return chapters


def split_chapters_dhammapada(text):
    parts = re.split(r"\n\s*(?=CHAPTER\s+[IVXLC]+\.)", text, flags=re.I)
    out = []
    for part in parts:
        m = re.match(r"\s*CHAPTER\s+([IVXLC]+)\.\s*([^\n]*)", part, flags=re.I)
        if not m:
            continue
        title = f"Ch. {m.group(1)} {m.group(2).strip().title()}"
        body = part[m.end():]
        # verses numbered "1. ...", "2. ..." at line starts
        verses = re.split(r"\n\s*(?=\d{1,3}\.\s)", body)
        for v in verses:
            vm = re.match(r"\s*(\d{1,3})\.\s*(.*)", v, flags=re.S)
            if vm:
                out.append((title, int(vm.group(1)), clean_paragraph(vm.group(2))))
    return out


def split_essays_emerson(text):
    heads = ["HISTORY", "SELF-RELIANCE", "COMPENSATION", "SPIRITUAL LAWS", "LOVE",
             "FRIENDSHIP", "PRUDENCE", "HEROISM", "THE OVER-SOUL", "CIRCLES",
             "INTELLECT", "ART"]
    # body headings are a roman numeral alone on a line, then the title alone
    # on the next line (the contents list puts them on one line, so this
    # pattern only matches real section starts)
    pat = re.compile(r"(?m)^\s*X{0,3}(?:IX|IV|V?I{0,3})\.\s*\n\s*(" +
                     "|".join(heads) + r")\s*$")
    matches = list(pat.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1).title(), None, text[m.end():end]))
    return out


def split_chapters_walden(text):
    heads = ["Economy", "Where I Lived, and What I Lived For", "Reading",
             "Sounds", "Solitude", "Visitors", "The Bean-Field", "The Village",
             "The Ponds", "Baker Farm", "Higher Laws", "Brute Neighbors",
             "House-Warming", "Former Inhabitants and Winter Visitors",
             "Winter Animals", "The Pond in Winter", "Spring", "Conclusion"]
    # drop the front matter (contents + epigraph); real chapters start after it
    anchor = text.find("wake my neighbors up")
    if anchor != -1:
        text = text[anchor:]
    pat = re.compile(r"(?m)^\s*(" + "|".join(re.escape(h) for h in heads) + r")\s*$")
    matches = list(pat.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), None, text[m.end():end]))
    return out


SEGMENTERS = {
    "tao-te-ching": ("Tao Te Ching", "East", split_chapters_tao, True),
    "dhammapada": ("Dhammapada", "East", split_chapters_dhammapada, True),
    "emerson-essays": ("Essays, First Series", "West", split_essays_emerson, False),
    "thoreau-walden": ("Walden", "West", split_chapters_walden, False),
}

MIN_W, MAX_W = 6, 60


def main():
    rows, uid = [], 0
    for slug, (work, tradition, seg, join_lines) in SEGMENTERS.items():
        text = (TEXTS / f"{slug}.txt").read_text(encoding="utf-8")
        sections = seg(text)
        print(f"{slug}: {len(sections)} sections")
        for section, sub_id, body in sections:
            if join_lines:
                # verse-style texts (Tao, Dhammapada): hard line-wraps fall
                # mid-sentence, so normalize the whole section to one flow of
                # text before sentence-splitting. (Filtering short *lines*
                # before joining truncated sentences -- do not do that.)
                chunks = [(0, s) for s in split_sentences(clean_paragraph(body))]
            else:
                # prose texts (Emerson, Walden): paragraphs are separated by
                # blank lines; hard-wrapped lines inside a paragraph are
                # joined before sentence-splitting.
                paras = [clean_paragraph(p)
                         for p in re.split(r"\n\s*\n", body)]
                paras = [p for p in paras if p]
                chunks = [(pi, s) for pi, p in enumerate(paras)
                          for s in split_sentences(p)]
            si = 0
            for pi, s in chunks:
                nw = words(s)
                if MIN_W <= nw <= MAX_W and not re.fullmatch(r"[\d\W]+", s):
                    rows.append({
                        "unit_id": uid,
                        "work": work,
                        "tradition": tradition,
                        "section": section,
                        "sub_id": sub_id if sub_id is not None else "",
                        "sent_idx": f"{pi}.{si}",
                        "text": s,
                        "n_words": nw,
                    })
                    uid += 1
                    si += 1
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "units.csv", index=False)
    print(f"wrote data/units.csv: {len(df)} sentences")
    print(df.groupby(["work"]).size())


if __name__ == "__main__":
    main()
