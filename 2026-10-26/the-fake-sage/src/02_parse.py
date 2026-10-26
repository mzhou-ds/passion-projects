"""Parse Wikiquote wikitext into a quote-level dataset.

Section taxonomy (top-level == == headings, with everything under them):
  sourced      - 'Quotes' and its subsections, plus work-titled quote sections
  disputed     - 'Disputed'
  misattributed- 'Misattributed', 'Apocryphal'
  unsourced    - 'Attributed' (claimed, no source given) -- kept separate
Excluded: 'Quotes about X', 'See also', 'References', 'External links',
'In popular culture' style sections and anything after them at same level.

A quote entry is a top-level bullet line ('* ' but not '**'). Sub-bullets are
source notes / commentary and are folded away. Markup is stripped: templates,
links, refs, italics/bold.
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

EXCLUDE_TOKENS = ["quotes about", "see also", "references", "external links",
                  "in popular culture", "misquotations in", "gallery", "notes"]

def classify(heading: str):
    h = heading.strip().lower()
    if any(t in h for t in EXCLUDE_TOKENS):
        return None
    if "misattributed" in h or "apocryph" in h or "misquote" in h:
        return "misattributed"
    if "disputed" in h:
        return "disputed"
    if h in ("attributed", "attributed quotes", "unsourced", "unsourced quotes"):
        return "unsourced"
    if "quote" in h or h not in ("introduction", "biography", "life"):
        # work-titled sections under the Quotes umbrella count as sourced
        return "sourced"
    return None

def clean(text: str) -> str:
    t = text
    t = re.sub(r"<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", " ", t)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    # templates (one nesting level is enough for quote bullets)
    for _ in range(3):
        t2 = re.sub(r"\{\{[^{}]*\}\}", " ", t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\]", " ", t)
    t = t.replace("'''", "").replace("''", "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" *")
    return t

HEADING = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")

def parse_file(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    quotes, current = [], None  # current = status of the enclosing level-2 section
    in_quotes_umbrella = False
    for ln in lines:
        m = HEADING.match(ln)
        if m:
            level, title = len(m.group(1)), m.group(2)
            if level == 2:
                c = classify(title)
                current = c
                in_quotes_umbrella = (c == "sourced")
            # deeper headings keep the level-2 status
            continue
        if current is None:
            continue
        if ln.startswith("* ") or ln.rstrip() == "*":
            body = clean(ln[1:])
            # drop pure source-note bullets and empty shells
            if len(body) < 12:
                continue
            if body.lower().startswith(("as quoted", "quoted in", "cited in", "source:")):
                continue
            quotes.append({"status": current, "text": body})
    return quotes

def main():
    log = json.loads((RAW / "fetch_log.json").read_text(encoding="utf-8"))
    rows, audit = [], []
    for entry in log:
        if not entry["wikiquote_ok"]:
            audit.append({**entry, "parsed": 0})
            continue
        fname = RAW / f"wikiquote_{re.sub(r'[^A-Za-z0-9]+','_',entry['name'])}.txt"
        qs = parse_file(fname)
        counts = {}
        for q in qs:
            counts[q["status"]] = counts.get(q["status"], 0) + 1
            rows.append({"thinker": entry["name"], "tradition": entry["tradition"],
                         "status": q["status"], "text": q["text"]})
        audit.append({**entry, "parsed": len(qs), "counts": counts})
        print(entry["name"], counts)
    out = ROOT / "data" / "quotes.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["thinker", "tradition", "status", "text"])
        w.writeheader(); w.writerows(rows)
    (RAW / "parse_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False), encoding="utf-8")
    print("total quotes:", len(rows))

if __name__ == "__main__":
    main()
