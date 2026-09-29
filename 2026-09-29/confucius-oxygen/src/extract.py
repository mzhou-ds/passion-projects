"""Extract English passages from Legge's Analects (PG #4094) and pre-filter
leadership/governance/management-relevant ones for hand verification.

Input : 2026-09-28/wisdom-arbitrage/data/texts/pg4094.txt (same repo)
Output: data/candidates.tsv  (leadership-relevant, for hand verification)
        data/all_passages.tsv (everything, for baseline comparisons)
"""
import re
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SRC = os.path.expanduser(
    "~/workspace/passion-projects/2026-09-28/wisdom-arbitrage/data/texts/pg4094.txt")
DATA = os.path.join(PROJ, "data")
os.makedirs(DATA, exist_ok=True)

lines = open(SRC, encoding="utf-8", errors="replace").read().splitlines()

start = next(i for i, l in enumerate(lines) if l.startswith("BOOK I."))
end = next((i for i, l in enumerate(lines)
            if i > start and "END OF THE PROJECT GUTENBERG EBOOK" in l), len(lines))
body = lines[start:end]

CHAP = re.compile(r"^\s*CHAP\.\s*(.*)$")
BOOK = re.compile(r"^BOOK ([IVXLC]+)\.")
CHINESE = re.compile(r"^[一-鿿、，。；：「」『』\s\dIVXLC.\[\]【】]*$")
CJK = re.compile(r"[一-鿿]")

passages = []
book = "?"
chap_no = "?"
cur = None

def flush():
    global cur
    if cur is not None:
        txt = " ".join(cur).strip()
        txt = re.sub(r"\s+", " ", txt)
        txt = CJK.sub("", txt).strip()
        txt = re.sub(r"\s+", " ", txt)
        if len(txt) > 40:
            passages.append((book, chap_no, txt))
        cur = None

for ln in body:
    m = BOOK.match(ln)
    if m:
        flush()
        book = m.group(1)
        chap_no = "?"
        continue
    s = ln.strip()
    if not s or CHINESE.match(s):
        continue
    m = CHAP.match(ln)
    if m:
        flush()
        rest = m.group(1)
        cm = re.match(r"([IVXLC]+)\.\s*(.*)$", rest)
        if cm:
            chap_no = cm.group(1)
            cur = [cm.group(2)]
        else:
            cur = [rest]
        continue
    if cur is not None:
        cur.append(s)
flush()

seen = set()
uniq = []
for p in passages:
    if p[2] not in seen:
        seen.add(p[2])
        uniq.append(p)

with open(os.path.join(DATA, "all_passages.tsv"), "w", encoding="utf-8") as f:
    f.write("passage_id\tbook\tchap\ttext\n")
    for i, (b, c, t) in enumerate(uniq):
        f.write("analects-%04d\t%s\t%s\t%s\n" % (i, b, c, t))
print("total english passages: %d" % len(uniq))

LEAD = re.compile(
    r"\b(rule|ruler|ruling|govern|government|minister|ministers|office|officer|"
    r"officers|employ|employed|promote|promoted|appoint|appointment|instruct|"
    r"instruction|teach|teacher|reward|punish|punishment|punishments|salary|"
    r"emolument|superior man|inferior man|superiors|inferiors|serve|service|"
    r"lead|leader|people|subjects|king|prince|throne|state|states|country|"
    r"kingdom|administration|administrative|dignity|remonstrat|subordinate|"
    r"magistrate|counsel|counselled|kingly|wages|stipend)\b", re.I)

cands = [(i, b, c, t) for i, (b, c, t) in enumerate(uniq) if LEAD.search(t)]
with open(os.path.join(DATA, "candidates.tsv"), "w", encoding="utf-8") as f:
    f.write("idx\tbook\tchap\ttext\n")
    for i, b, c, t in cands:
        f.write("analects-%04d\t%s\t%s\t%s\n" % (i, b, c, t))
print("leadership candidates: %d" % len(cands))
