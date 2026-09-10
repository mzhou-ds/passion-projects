"""Download the philosophy corpus from Project Gutenberg.

12 public-domain texts spanning ~2,300 years (399 BCE - 1912 CE).
Each text is cleaned of Gutenberg boilerplate and saved as plain text.

Data source: Project Gutenberg (https://www.gutenberg.org), public domain.
"""
import re
import time
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
TEXTS = DATA / "texts"
TEXTS.mkdir(parents=True, exist_ok=True)

# (slug, title, author, year, era, gutenberg_id)
CORPUS = [
    ("plato-apology", "Apology", "Plato", -399, "Ancient", 1656),
    ("aristotle-ethics", "Nicomachean Ethics", "Aristotle", -350, "Ancient", 8438),
    ("aurelius-meditations", "Meditations", "Marcus Aurelius", 180, "Ancient", 2680),
    ("augustine-confessions", "Confessions", "Augustine of Hippo", 400, "Ancient", 3296),
    ("descartes-discourse", "Discourse on the Method", "Rene Descartes", 1637, "Early Modern", 59),
    ("spinoza-ethics", "Ethics", "Baruch Spinoza", 1677, "Early Modern", 3800),
    ("hume-enquiry", "An Enquiry Concerning Human Understanding", "David Hume", 1748, "Early Modern", 9662),
    ("kant-critique", "Critique of Pure Reason", "Immanuel Kant", 1781, "Modern", 4280),
    ("mill-utilitarianism", "Utilitarianism", "John Stuart Mill", 1863, "Modern", 11224),
    ("nietzsche-bge", "Beyond Good and Evil", "Friedrich Nietzsche", 1886, "Modern", 4363),
    ("james-pragmatism", "Pragmatism", "William James", 1907, "Modern", 5116),
    ("russell-problems", "The Problems of Philosophy", "Bertrand Russell", 1912, "Modern", 5827),
]

HEADERS = {"User-Agent": "passion-projects philosophy-in-data (personal research project)"}


def fetch(gid):
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}.txt",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200 and len(r.text) > 20_000:
                return r.text
        except requests.RequestException:
            continue
    return None


def strip_boilerplate(text):
    # Cut everything before the START marker and after the END marker.
    start = re.search(
        r"\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if start:
        text = text[start.end():]
    end = re.search(
        r"\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if end:
        text = text[:end.start()]
    # Drop translator/preface front matter that precedes the body: many PG
    # editions include long introductions. Heuristic: drop lines until the
    # first all-caps chapter heading appears? Too aggressive; keep as-is but
    # remove obvious CONTENTS tables.
    lines = text.splitlines()
    lines = [ln for ln in lines if not re.fullmatch(r"\s*[.\s]{10,}\d+\s*", ln)]
    text = "\n".join(lines)
    # Normalize whitespace, drop illustration markers.
    text = re.sub(r"\[Illustration[^\]]*\]", "", text)
    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    rows = []
    for slug, title, author, year, era, gid in CORPUS:
        out = TEXTS / f"{slug}.txt"
        if out.exists():
            raw = out.read_text(encoding="utf-8")
            print(f"cached  {slug}: {len(raw.split()):,} words")
        else:
            raw = fetch(gid)
            if raw is None:
                raise SystemExit(f"FAILED to download Gutenberg id {gid} ({slug})")
            cleaned = strip_boilerplate(raw)
            out.write_text(cleaned, encoding="utf-8")
            print(f"saved   {slug}: {len(cleaned.split()):,} words")
            time.sleep(1)  # be polite to Gutenberg
        rows.append({"slug": slug, "title": title, "author": author,
                     "year": year, "era": era, "gutenberg_id": gid,
                     "words": len(out.read_text(encoding="utf-8").split())})
    pd.DataFrame(rows).to_csv(DATA / "corpus.csv", index=False)
    print("corpus.csv written")


if __name__ == "__main__":
    main()
