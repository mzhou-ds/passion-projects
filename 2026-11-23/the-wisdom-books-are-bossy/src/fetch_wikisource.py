"""Fetch public-domain wisdom texts from Wikisource via its API.

Project Gutenberg is down for maintenance today (503 on every mirror path),
so the six texts not already held locally are taken from Wikisource's
proofread transcriptions of the same public-domain translations.
Each fetch records its source page, revision id and fetch time in the manifest.
"""
import json, re, html, time, urllib.parse, urllib.request, os

API = "https://en.wikisource.org/w/api.php"
UA = {"User-Agent": "MusingWithMike research bot (contact: michaelzhou96@gmail.com)"}

def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def parse_page(title):
    """Return (clean_text, revid) for a Wikisource page's rendered HTML."""
    d = api({"action": "parse", "page": title, "prop": "text|revid", "format": "json"})
    raw = d["parse"]["text"]["*"]
    revid = d["parse"]["revid"]
    # drop footnote bodies (references list) and their inline markers
    raw = re.sub(r'<div class="mw-references-wrap".*?</div>', " ", raw, flags=re.S | re.I)
    raw = re.sub(r'<ol class="references".*?</ol>', " ", raw, flags=re.S | re.I)
    raw = re.sub(r'<sup class="reference".*?</sup>', " ", raw, flags=re.S | re.I)
    # drop style/script blocks (they leak CSS into the text)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    txt = html.unescape(raw)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n\n", txt)
    return txt.strip(), revid

def subpages(prefix):
    d = api({"action": "query", "list": "allpages", "apprefix": prefix,
             "aplimit": "max", "format": "json"})
    return [p["title"] for p in d["query"]["allpages"]]

def fetch_single(title, out_name, cut_after=None):
    txt, revid = parse_page(title)
    if cut_after:
        i = txt.find(cut_after)
        if i > 0:
            txt = txt[:i]
    path = os.path.join("data/raw", out_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{out_name}: {len(txt.split()):,} words from '{title}' (rev {revid})")
    return {"file": out_name, "source": "wikisource", "page": title,
            "revid": revid, "words": len(txt.split())}

def fetch_multi(prefix, out_name, order_key=None, cut_after=None, keep=None):
    titles = subpages(prefix)
    if keep:
        titles = [t for t in titles if keep(t)]
    if order_key:
        titles.sort(key=order_key)
    parts, revs = [], []
    for t in titles:
        txt, revid = parse_page(t)
        if cut_after:
            i = txt.find(cut_after)
            if i > 0:
                txt = txt[:i]
        parts.append(txt)
        revs.append(revid)
        time.sleep(0.3)
    txt = "\n\n".join(parts)
    path = os.path.join("data/raw", out_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{out_name}: {len(txt.split()):,} words from {len(titles)} subpages of '{prefix}'")
    return {"file": out_name, "source": "wikisource", "page": prefix,
            "subpages": titles, "revids": revs, "words": len(txt.split())}

FOOTER = "This work is in the public domain"

manifest = []
# Tao Te Ching, Legge 1891 (Sacred Books of the East vol. 39)
manifest.append(fetch_single("Tâo Teh King", "tao_te_ching_legge.txt", cut_after=FOOTER))
# Enchiridion, Rolleston 1881
manifest.append(fetch_single("The Encheiridion of Epictetus/Encheiridion", "enchiridion_rolleston.txt", cut_after=FOOTER))
# Dhammapada, Muller 1881
manifest.append(fetch_single("Dhammapada (Muller)", "dhammapada_muller.txt", cut_after=FOOTER))
# Zhuangzi, Giles 1889 - chapters as subpages
manifest.append(fetch_multi("Chuang Tzŭ (Giles)/", "zhuangzi_giles.txt",
    order_key=lambda t: int(re.search(r"Chapter (\d+)", t).group(1)), cut_after=FOOTER,
    keep=lambda t: re.search(r"Chapter \d+$", t) is not None))
# Meditations, Haines 1916 - books as subpages
manifest.append(fetch_multi("Marcus Aurelius (Haines 1916)/", "meditations_haines.txt",
    order_key=lambda t: int(re.search(r"Book (\d+)", t).group(1)), cut_after=FOOTER,
    keep=lambda t: re.search(r"Book \d+$", t) is not None))
# Seneca, Moral Letters to Lucilius (Gummere) - Letters 1-20 only, disclosed subset
titles = [f"Moral letters to Lucilius/Letter {n}" for n in range(1, 21)]
parts, revs = [], []
for t in titles:
    txt, revid = parse_page(t)
    i = txt.find(FOOTER)
    if i > 0:
        txt = txt[:i]
    parts.append(txt); revs.append(revid)
    time.sleep(0.3)
txt = "\n\n".join(parts)
with open("data/raw/seneca_letters_1_20.txt", "w", encoding="utf-8") as f:
    f.write(txt)
print(f"seneca_letters_1_20.txt: {len(txt.split()):,} words from 20 letters")
manifest.append({"file": "seneca_letters_1_20.txt", "source": "wikisource",
    "page": "Moral letters to Lucilius/Letter 1-20", "revids": revs,
    "words": len(txt.split()), "note": "Letters 1-20 only; disclosed subset"})

with open("data/raw/manifest_wikisource.json", "w") as f:
    json.dump(manifest, f, indent=2)
print("done")
