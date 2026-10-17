"""Segment each translation into its 81 chapters.

Each source needs its own strategy (documented inline):
  chinese   - headings are 第X章 with Chinese numerals.
  chalmers  - headings are Roman numerals + an em dash + a title; OCR is
              noisy (Google Books scan), running heads and 'Digitized by'
              watermarks are stripped. Some headings are too garbled to
              recover; those chapters are reported missing, never invented.
  legge     - chapters open with a paragraph 'N. 1. ...' where N is the
              chapter number and 1 is the first verse; chapter 1 is
              'Ch. 1. 1. ...'. We walk paragraphs expecting N = 1..81.
  carus     - headings are 'N. TITLE IN CAPS.'; walk expecting N = 1..81.
  linnell   - EPUB, verse lines; chapters are headed by the number spelled
              out as a word ('One', 'Two', ...) alone on a line. Walk
              expecting 1..81 across the EPUB parts in numeric order.
  meditations (control) - split into the 12 BOOKs where headings allow,
              otherwise kept as one whole-text row.

Output: data/chapters/tao_chapters.csv, data/chapters/meditations.csv,
        data/chapters/coverage.json
"""
import csv
import html
import json
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "chapters"

WORDS = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
HAN = re.compile(r"[一-鿿]")


def n_words(text: str) -> int:
    return len(WORDS.findall(text))


def gut_body(text: str) -> str:
    """Strip Project Gutenberg header/footer."""
    m = re.search(r"\*\*\* START OF THE PROJECT GUTENBERG.*?\*\*\*", text, re.S)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\* END OF THE PROJECT GUTENBERG", text)
    if m:
        text = text[: m.start()]
    return text


# ---------------------------------------------------------------- chinese
CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
             "八": 8, "九": 9}


def cn_num(s: str) -> int:
    if s == "十":
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        tens = CN_DIGITS.get(left, 1) if left else 1
        ones = CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return CN_DIGITS[s]


def seg_chinese(text: str) -> dict[int, str]:
    text = gut_body(text)
    parts = re.split(r"第([一二三四五六七八九十]+)章", text)
    chapters = {}
    # parts: [pre, num, body, num, body, ...]
    for i in range(1, len(parts) - 1, 2):
        n = cn_num(parts[i])
        body = parts[i + 1]
        # cut at the next book division marker if present
        body = re.split(r"老子(道經|德經)", body)[0]
        chapters[n] = body.strip()
    return chapters


# ---------------------------------------------------------------- legge
def seg_legge(text: str) -> dict[int, str]:
    text = gut_body(text)
    paras = re.split(r"\n\s*\n", text)
    chapters: dict[int, list[str]] = {}
    expected = 1
    cur = None
    for p in paras:
        flat = re.sub(r"\s+", " ", p).strip()
        if not flat:
            continue
        m = re.match(r"(?:Ch\.\s*)?(\d{1,2})\.\s+1\.\s", flat)
        bare = re.fullmatch(r"(\d{1,2})\.", flat)
        # (a) 'N. 1. ...' - standard opening; allow resync up to 3 ahead
        if m and expected <= int(m.group(1)) <= min(expected + 3, 81):
            cur = int(m.group(1))
            chapters[cur] = [flat]
            expected = cur + 1
            continue
        # (b) verse-only chapters open with the chapter number alone
        if bare and int(bare.group(1)) == expected and expected <= 81:
            cur = expected
            chapters[cur] = []
            expected += 1
            continue
        # (c) single-paragraph chapters (e.g. ch. 11) open 'N. <text>' with
        # no verse number; verse counts never reach 10 in this edition, so
        # this is only trusted once the expected chapter is >= 10.
        long_open = re.match(r"(\d{1,2})\.\s+[A-Z(]", flat)
        if (long_open and int(long_open.group(1)) == expected
                and expected >= 10 and len(flat.split()) > 25
                and cur is not None and len(chapters[cur]) >= 2):
            cur = expected
            chapters[cur] = [flat]
            expected += 1
            continue
        if cur is not None:
            chapters[cur].append(flat)
    return {k: " ".join(v) for k, v in chapters.items()}


# ---------------------------------------------------------------- carus
def seg_carus(text: str) -> dict[int, str]:
    # Translation proper begins at the first chapter heading.
    start = text.find("REASON'S   REALIZATION")
    if start == -1:
        start = text.find("REASON'S  REALIZATION")
    head = re.compile(r"^\s*(\d{1,2})\.\s+[A-Z][A-Z'’\- ]{3,}[.?!]\s*$")
    chapters: dict[int, list[str]] = {}
    expected = 1
    cur = None
    for line in text[start - 20:].splitlines():
        s = line.strip()
        if re.match(r"^\d+\s+Canon\s+of\s+Reason", s) or \
           re.match(r"^Canon\s+of\s+Reason.*\d+$", s) or \
           re.fullmatch(r"\d+", s) or re.fullmatch(r"(I|II)\.", s):
            continue  # running heads, page numbers, part markers
        m = head.match(line)
        if m and expected <= int(m.group(1)) <= min(expected + 2, 81):
            cur = int(m.group(1))
            chapters[cur] = []
            expected = cur + 1
            continue
        if cur is not None:
            chapters[cur].append(line)
        if expected > 81 and cur == 81 and len(chapters.get(81, [])) > 60:
            break
    out = {}
    for k, lines in chapters.items():
        body = " ".join(l.strip() for l in lines)
        body = re.sub(r"\s+", " ", body).strip()
        out[k] = body
    return out


# ---------------------------------------------------------------- chalmers
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_val(s: str) -> int | None:
    s = s.upper()
    if not s or any(c not in ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = ROMAN[c]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def seg_chalmers(text: str) -> dict[int, str]:
    start = text.find("THE CLASSIC OF TAU AND OF VIRTUE")
    text = text[start:]
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if "Digitized by" in s:
            continue
        # running heads: page number + TAU TEH KING in garbled OCR caps
        if re.match(r"^\d*\s*TAU\b.*KING\.?\s*\d*$", s, re.I) and len(s) < 34:
            continue
        if re.match(r"^\d+$", s):  # bare page numbers
            continue
        lines.append(line)
    head = re.compile(r"^\s*([IVXLivxl]{1,7}|[a-z]{1,4})\.?\s*[—–=-]\s*\S")
    # OCR garbles observed in this scan: 'n' for II, 'vin' for VIII,
    # 'xxin' for XXIII.
    garbles = {"n": 2, "vin": 8, "xxin": 23}
    chapters: dict[int, list[str]] = {}
    expected = 1
    cur = None
    for line in lines:
        m = head.match(line)
        if m and expected <= 81:
            token = m.group(1)
            val = garbles.get(token.lower())
            if val is None:
                val = roman_val(token)
            if val is not None and expected <= val <= min(expected + 2, 81):
                cur = val
                chapters[cur] = []
                expected = val + 1
                continue
        if cur is not None:
            chapters[cur].append(line)
    return {k: re.sub(r"\s+", " ", " ".join(v)).strip() for k, v in chapters.items()}


# ---------------------------------------------------------------- linnell
NUMWORDS = {}
_units = ["one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
          "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_tens = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty"]
for i, w in enumerate(_units, 1):
    NUMWORDS[w] = i
for ti, t in enumerate(_tens, 2):
    NUMWORDS[t] = ti * 10
    for ui, u in enumerate(_units[:9], 1):
        NUMWORDS[f"{t}-{u}"] = ti * 10 + ui
        NUMWORDS[f"{t} {u}"] = ti * 10 + ui
        NUMWORDS[f"{t}{u}"] = ti * 10 + ui


def linnell_lines(epub_path: pathlib.Path) -> list[str]:
    z = zipfile.ZipFile(epub_path)
    parts = []
    for name in z.namelist():
        m = re.search(r"-h-(\d+)\.htm\.html$", name)
        if m:
            parts.append((int(m.group(1)), name))
    lines: list[str] = []
    for _, name in sorted(parts):
        raw = z.read(name).decode("utf-8", errors="ignore")
        raw = re.sub(r"<(br|/p|/h\d|/div|/li)[^>]*>", "\n", raw)
        txt = html.unescape(re.sub(r"<[^>]+>", "", raw))
        for line in txt.split("\n"):
            s = line.strip()
            if s and "Project Gutenberg eBook" not in s:
                lines.append(s)
    return lines


def seg_linnell(epub_path: pathlib.Path) -> dict[int, str]:
    """Linnell's edition prints the translation grouped by his hypothesized
    textual layers (EARLY / LATE / POST-GUODIAN, ch. 2 separately at the
    end), not in canonical order. Headings are the chapter number spelled
    out, Title-case, alone on a line ('One', 'Eighty one'). We collect by
    heading value rather than walking in order. ALL-CAPS lines are
    section boundaries that close the current chapter."""
    lines = linnell_lines(epub_path)
    chapters: dict[int, list[str]] = {}
    cur = None
    for line in lines:
        s = line.strip()
        if "FULL PROJECT GUTENBERG" in s or "End of the Project" in s:
            break
        if re.fullmatch(r"[A-Z][A-Z \-]{2,}", s):  # EARLY / LATE / etc.
            cur = None
            continue
        key = s.lower()
        val = NUMWORDS.get(key)
        title_case = s[:1].isupper() and s[1:] == s[1:].lower()
        if val and title_case and re.fullmatch(r"[A-Za-z\- ]+", s):
            already = chapters.get(val)
            open_words = sum(len(x.split()) for x in chapters.get(cur, [])) if cur else 0
            if already is None or sum(len(x.split()) for x in already) < 40:
                if cur is None or open_words >= 15:
                    cur = val
                    chapters.setdefault(cur, [])
                    continue
        if cur is not None:
            chapters[cur].append(line)
    return {k: " ".join(v) for k, v in chapters.items()
            if sum(len(x.split()) for x in v) >= 25}


# ---------------------------------------------------------------- meditations
def seg_meditations(text: str) -> dict[int, str]:
    text = gut_body(text)
    # drop front matter: body starts at first BOOK I heading (indented)
    m = re.search(r"\n\s*BOOK I\.?\s*\n", text)
    if m:
        text = text[m.start():]
    parts = re.split(r"\n\s*BOOK\s+([IVX]{1,4})\.?\s*\n", text)
    books = {}
    for i in range(1, len(parts) - 1, 2):
        n = roman_val(parts[i])
        if n:
            body = re.sub(r"END OF THE [A-Z ]+ BOOK\.", "", parts[i + 1])
            books[n] = re.sub(r"\s+", " ", body).strip()
    if len(books) >= 12:
        return books
    # Long's edition instead marks books with a bare Roman numeral alone
    # on a line ('I.', 'II.', ...). Walk them in sequence, starting just
    # before Book I's distinctive opening line so the introductory
    # essay's own numerals are never picked up.
    anchor = text.find("From my grandfather Verus")
    if anchor != -1:
        text = text[max(0, anchor - 200):]
    books = {}
    expected = 1
    cur = None
    for line in text.splitlines():
        s = line.strip()
        m = re.fullmatch(r"([IVX]{1,4})\.", s)
        if m and roman_val(m.group(1)) == expected and expected <= 12:
            cur = expected
            books[cur] = []
            expected += 1
            continue
        if cur is not None:
            books[cur].append(line)
    books = {k: re.sub(r"\s+", " ", " ".join(v)).strip() for k, v in books.items()}
    if not books:
        books[0] = re.sub(r"\s+", " ", text).strip()
    return books


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    coverage = {}

    cn = seg_chinese((RAW / "chinese_source_gutenberg7337.txt").read_text(encoding="utf-8", errors="ignore"))
    coverage["chinese"] = sorted(cn)

    translators = [
        ("chalmers", 1868, seg_chalmers((RAW / "chalmers1868_archive.txt").read_text(encoding="utf-8", errors="ignore"))),
        ("legge", 1891, seg_legge((RAW / "legge1891_gutenberg216.txt").read_text(encoding="utf-8", errors="ignore"))),
        ("carus", 1898, seg_carus((RAW / "carus1898_archive.txt").read_text(encoding="utf-8", errors="ignore"))),
        ("linnell", 2015, seg_linnell(RAW / "linnell2015_gutenberg49965.epub")),
    ]

    rows = []
    for name, year, chapters in translators:
        coverage[name] = sorted(chapters)
        for ch in sorted(chapters):
            body = chapters[ch]
            cn_chars = len(HAN.findall(cn.get(ch, "")))
            rows.append({
                "translator": name, "year": year, "chapter": ch,
                "text": body, "n_words": n_words(body),
                "cn_chars": cn_chars,
                "words_per_cn_char": round(n_words(body) / cn_chars, 3) if cn_chars else "",
            })
    with open(OUT / "tao_chapters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    med_rows = []
    for name, year, fname in [
        ("long", 1862, "meditations_long1862_gutenberg15877.txt"),
        ("chrystal", 1902, "meditations_chrystal1902_gutenberg55317.txt"),
    ]:
        books = seg_meditations((RAW / fname).read_text(encoding="utf-8", errors="ignore"))
        coverage[f"meditations_{name}"] = sorted(books)
        for b in sorted(books):
            med_rows.append({"translator": name, "year": year, "book": b,
                             "text": books[b], "n_words": n_words(books[b])})
    with open(OUT / "meditations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(med_rows[0].keys()))
        w.writeheader()
        w.writerows(med_rows)

    (OUT / "coverage.json").write_text(json.dumps(
        {k: {"n": len(v), "chapters": v} for k, v in coverage.items()}, indent=1))
    for k, v in coverage.items():
        missing = [c for c in range(1, 82) if c not in v] if k != "chinese" else []
        print(f"{k}: {len(v)} units; missing chapters: {missing if missing else 'none'}")


if __name__ == "__main__":
    main()
