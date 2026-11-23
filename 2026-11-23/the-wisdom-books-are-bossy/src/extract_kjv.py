"""Extract Ecclesiastes and Proverbs from the KJV text (Gutenberg #10).

The KJV file is the Nov 14 build's verified Gutenberg #10 download, reused
here. Books are delimited by lines like 'The Book of Ecclesiastes' /
'The Proverbs'. Chapter/verse numbers are stripped for sentence analysis.
"""
import re, json

txt = open("data/raw/kjv.txt", encoding="utf-8").read()

def extract(book_start, book_end):
    # headings appear twice: once in the table of contents, once in the body.
    # Take the LAST standalone-line occurrence, which is the body heading.
    import re as _re
    occ = [m.start() for m in _re.finditer(r"(?m)^" + _re.escape(book_start) + r"\s*$", txt)]
    i = occ[-1]
    j = txt.index(book_end, i)
    seg = txt[i:j]
    # drop the book title line itself
    seg = seg[len(book_start):]
    # strip chapter/verse markers like '1:1 ' or '12:13 ' at line starts
    seg = re.sub(r"(?m)^\s*\d+:\d+\s*", "", seg)
    # strip bare chapter numbers on their own lines
    seg = re.sub(r"(?m)^\s*\d+\s*$", "", seg)
    return seg.strip()

eccl = extract("Ecclesiastes", "The Song of Solomon")
prov = extract("The Proverbs", "Ecclesiastes")
open("data/raw/ecclesiastes_kjv.txt", "w").write(eccl)
open("data/raw/proverbs_kjv.txt", "w").write(prov)
print("ecclesiastes:", len(eccl.split()), "words")
print("proverbs:", len(prov.split()), "words")
print("eccl head:", eccl[:200].replace("\n", " "))
print("prov head:", prov[:200].replace("\n", " "))
