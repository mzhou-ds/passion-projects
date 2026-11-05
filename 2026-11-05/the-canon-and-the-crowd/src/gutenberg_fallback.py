"""Fallback Gutenberg fetcher.

Gutendex 503s under load, so this downloads the still-missing texts
straight from gutenberg.org by ebook id and verifies each file's
Title/Author header before accepting it. Rebuilds gutenberg_meta.json
from everything on disk. Safe to re-run: it never re-downloads a file
whose header already matches.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"

# figure -> (gutenberg id, expected title fragment, expected author fragment)
WANTED = {
    "Seneca the Younger": (3794, "Letters from a Stoic", "Seneca"),
    "Laozi": (216, "Tao Teh King", "Laozi"),  # Legge's title on Gutenberg
    "Friedrich Nietzsche": (4363, "Beyond Good and Evil", "Nietzsche"),
    "Immanuel Kant": (4280, "Critique of Pure Reason", "Kant"),
    "David Hume": (9662, "Enquiry Concerning Human Understanding", "Hume"),
    "René Descartes": (59, "Meditations on First Philosophy", "Descartes"),
    "Plato": (1497, "Republic", "Plato"),
    "Aristotle": (8438, "Nicomachean Ethics", "Aristotle"),
    "Arthur Schopenhauer": (10732, "Studies in Pessimism", "Schopenhauer"),
    "Mencius": (39408, "Mencius", "Mencius"),
}

UA = {"User-Agent": "MusingWithMike/1.0 (research; contact: mzhou@example.com)"}


def header_info(text):
    title = re.search(r"^Title:\s*(.+)$", text, re.M)
    author = re.search(r"^Author:\s*(.+)$", text, re.M)
    lang = re.search(r"^Language:\s*(.+)$", text, re.M)
    return (
        title.group(1).strip() if title else "",
        author.group(1).strip() if author else "",
        lang.group(1).strip() if lang else "",
    )


def already_have():
    have = {}
    for f in CACHE.glob("gutenberg_*.txt"):
        text = f.read_text(errors="replace")
        title, author, lang = header_info(text)
        have[f.name] = {"title": title, "author": author, "language": lang}
    return have


def download(gid):
    url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    have = already_have()
    for name, info in have.items():
        print(f"on disk {name}: {info['title'][:60]!r} / {info['author'][:40]} / {info['language']}")
    meta = {}
    # map disk files to figures by matching title/author fragments
    for figure, (gid, want_title, want_author) in WANTED.items():
        found = None
        for fname, info in have.items():
            if (want_title.lower() in info["title"].lower()
                    and want_author.lower() in info["author"].lower()
                    and info["language"].lower().startswith("english")):
                found = fname
                break
        if found:
            meta[figure] = {"gutenberg_id": int(found.split("_")[1].split(".")[0]),
                            "title": have[found]["title"], "file": found}
            print(f"  {figure}: already have {found}")
            continue
        print(f"  {figure}: downloading id {gid} ...", flush=True)
        ok = False
        for attempt in range(3):
            try:
                text = download(gid)
                title, author, lang = header_info(text)
                if (want_title.lower() in title.lower()
                        and want_author.lower() in author.lower()
                        and lang.lower().startswith("english")):
                    fname = f"gutenberg_{gid}.txt"
                    (CACHE / fname).write_text(text)
                    meta[figure] = {"gutenberg_id": gid, "title": title, "file": fname}
                    print(f"    ok: {title!r} ({len(text):,} chars)")
                    ok = True
                else:
                    print(f"    WRONG BOOK: title={title!r} author={author!r} lang={lang!r}")
                break
            except Exception as e:
                print(f"    attempt {attempt + 1} failed: {e}")
                time.sleep(3 * (attempt + 1))
        if not ok:
            print(f"  {figure}: FAILED, leaving out of the Gutenberg panel")
        time.sleep(1)

    # keep the already-good disk files that are not in WANTED (Epictetus,
    # Marcus Aurelius, Confucius, Zhuangzi, Dhammapada) by matching the
    # panel list in panel.py
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from panel import GUTENBERG
    for figure, title, author in GUTENBERG:
        if figure in meta:
            continue
        for fname, info in have.items():
            if (title.split(":")[0].lower() in info["title"].lower()
                    and info["language"].lower().startswith("english")):
                meta[figure] = {"gutenberg_id": int(fname.split("_")[1].split(".")[0]),
                                "title": info["title"], "file": fname}
                print(f"  {figure}: matched disk file {fname}")
                break
    (CACHE / "gutenberg_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"meta written: {len(meta)} texts")
    print("MISSING:", [f for f, _, _ in GUTENBERG if f not in meta])


if __name__ == "__main__":
    main()
