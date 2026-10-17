"""Fetch every source text for the Tao retranslation-drift study.

All sources are public domain and fetched from canonical locations:
  - Project Gutenberg plain texts / EPUB (www.gutenberg.org)
  - Internet Archive DjVu full texts (archive.org) for the two 19th/early-20th
    century translations that Gutenberg does not carry as plain text.

Run:  python3 src/fetch_data.py
Writes raw files into data/raw/ and a manifest (data/raw/SOURCES.md).
"""
import hashlib
import pathlib
import sys

import requests

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

SOURCES = [
    # filename, url, description
    (
        "chinese_source_gutenberg7337.txt",
        "https://www.gutenberg.org/cache/epub/7337/pg7337.txt",
        "Dao De Jing, Chinese source text (Project Gutenberg #7337).",
    ),
    (
        "legge1891_gutenberg216.txt",
        "https://www.gutenberg.org/cache/epub/216/pg216.txt",
        "James Legge translation, 1891, 'The Tao Teh King, or the Tao and its "
        "Characteristics' (Project Gutenberg #216, from Sacred Books of the East).",
    ),
    (
        "linnell2015_gutenberg49965.epub",
        "https://www.gutenberg.org/cache/epub/49965/pg49965.epub",
        "Bruce R. Linnell translation, 2015, 'Dao De Jing: A Minimalist "
        "Translation' (Project Gutenberg #49965, EPUB; no plain-text edition).",
    ),
    (
        "chalmers1868_archive.txt",
        "https://archive.org/download/speculationsonm00laogoog/"
        "speculationsonm00laogoog_djvu.txt",
        "John Chalmers translation, 1868, 'The Speculations on Metaphysics, "
        "Polity, and Morality, of the Old Philosopher Lau-tsze' - the first "
        "English translation of the Tao Te Ching (Internet Archive "
        "speculationsonm00laogoog, DjVu OCR text).",
    ),
    (
        "carus1898_archive.txt",
        "https://archive.org/download/thecanonofreason00caruuoft/"
        "thecanonofreason00caruuoft_djvu.txt",
        "Paul Carus translation, first published 1898; scanned edition is "
        "'The Canon of Reason and Virtue' (Open Court, 1913) (Internet "
        "Archive thecanonofreason00caruuoft, DjVu OCR text).",
    ),
    (
        "meditations_long1862_gutenberg15877.txt",
        "https://www.gutenberg.org/cache/epub/15877/pg15877.txt",
        "CONTROL: Marcus Aurelius, Meditations, George Long translation, "
        "1862 (Project Gutenberg #15877, 'Thoughts of Marcus Aurelius "
        "Antoninus').",
    ),
    (
        "meditations_chrystal1902_gutenberg55317.txt",
        "https://www.gutenberg.org/cache/epub/55317/pg55317.txt",
        "CONTROL: Marcus Aurelius, Meditations, George W. Chrystal "
        "translation, 1902 (Project Gutenberg #55317).",
    ),
]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# Source manifest\n"]
    for fname, url, desc in SOURCES:
        dest = RAW / fname
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"skip (exists): {fname}")
        else:
            print(f"downloading: {url}")
            r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"  -> {fname} ({len(r.content):,} bytes)")
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
        lines.append(f"- `{fname}` - {desc}\n  - URL: {url}\n  - sha256[:16]: {digest}\n")
    (RAW / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")
    print("manifest written to data/raw/SOURCES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
