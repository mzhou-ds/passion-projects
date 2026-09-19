"""Download the East-meets-West philosophy corpus from Project Gutenberg.

4 public-domain texts, unit of analysis = sentences:
  - Tao Te Ching (Laozi, ~6th c. BCE; James Legge translation, 1891) -- PG #216
  - Dhammapada (Buddha, ~3rd c. BCE; F. Max Muller translation, 1881) -- PG #2017
  - Essays, First Series (Emerson, 1841) -- PG #2944
  - Walden (Thoreau, 1854) -- PG #205 (Walden portion only; drops "Civil Disobedience")

Boilerplate stripped; Walden split from Civil Disobedience; cleaned texts saved
to data/texts/. A corpus.csv records metadata.

Sources (all public domain in the US):
  https://www.gutenberg.org/ebooks/216
  https://www.gutenberg.org/ebooks/2017
  https://www.gutenberg.org/ebooks/2944
  https://www.gutenberg.org/ebooks/205
"""
import re
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
TEXTS = DATA / "texts"
TEXTS.mkdir(parents=True, exist_ok=True)

# (slug, title, author, year, tradition, gutenberg_id)
CORPUS = [
    ("tao-te-ching", "Tao Te Ching", "Laozi", -600, "East", 216),
    ("dhammapada", "Dhammapada", "Buddha", -300, "East", 2017),
    ("emerson-essays", "Essays, First Series", "Ralph Waldo Emerson", 1841, "West", 2944),
    ("thoreau-walden", "Walden", "Henry David Thoreau", 1854, "West", 205),
]

HEADERS = {"User-Agent": "passion-projects laozi-and-emerson (personal research project)"}


def fetch(gid):
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}.txt",
    ]
    last = None
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and len(r.text) > 10_000:
                return r.text
            last = f"{url} -> {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = f"{url} -> {e}"
    raise RuntimeError(f"could not fetch {gid}: {last}")


def strip_boilerplate(text):
    # NOTE: end marker must be searched AFTER the start slice, otherwise its
    # original-text coordinate overshoots and keeps ~800 chars of license.
    start = re.search(r"\*\*\* START OF (THIS|THE) PROJECT GUTENBERG", text)
    if start:
        text = text[start.end():]
    # drop the marker line's remainder, e.g. "EBOOK WALDEN, AND ... ***"
    text = re.sub(r"^\s*EBOOK .*?\*\*\*\s*\n", "", text, count=1)
    end = re.search(r"\*\*\* END OF (THIS|THE) PROJECT GUTENBERG", text)
    if end:
        text = text[: end.start()]
    return text.strip()


def clean_walden(text):
    """Keep only the Walden portion of ebook #205 (drop Civil Disobedience).

    The phrase also appears in the ebook's title line and Contents, so cut at
    the LAST standalone occurrence, which is the actual section heading that
    follows "THE END" of Walden.
    """
    marks = list(re.finditer(r"\r?\n\s*ON THE DUTY OF CIVIL DISOBEDIENCE\s*\r?\n", text))
    if marks:
        text = text[: marks[-1].start()]
    return text.strip()


def main():
    rows = []
    for slug, title, author, year, tradition, gid in CORPUS:
        print(f"fetching {slug} (PG #{gid})...")
        text = strip_boilerplate(fetch(gid))
        if slug == "thoreau-walden":
            text = clean_walden(text)
            rows.append((slug, title, author, year, tradition, gid, "Civil Disobedience removed"))
        else:
            rows.append((slug, title, author, year, tradition, gid, ""))
        (TEXTS / f"{slug}.txt").write_text(text, encoding="utf-8")
        print(f"  {len(text):,} chars -> data/texts/{slug}.txt")
    pd.DataFrame(
        rows,
        columns=["slug", "title", "author", "year", "tradition", "gutenberg_id", "notes"],
    ).to_csv(DATA / "corpus.csv", index=False)
    print("wrote data/corpus.csv")


if __name__ == "__main__":
    main()
