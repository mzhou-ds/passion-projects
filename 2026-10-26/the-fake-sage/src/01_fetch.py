"""Fetch Wikiquote wikitext + Wikipedia pageviews for a curated canon of 28 thinkers.

Wikiquote is the one place on the internet that sorts a thinker's quotations
into SOURCED, DISPUTED and MISATTRIBUTED buckets at scale. Nobody, to our
knowledge, has ever counted across the whole canon. Fresh requests.get per
call (keep-alive sessions hang through this proxy), paced at ~1.2s.
"""
import json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "MusingWithMike-research/1.0 (daily passion build; contact mzhou-ds)"}

# name, wikiquote page, wikipedia article, tradition
THINKERS = [
    ("Laozi", "Laozi", "Laozi", "east"),
    ("Confucius", "Confucius", "Confucius", "east"),
    ("Mencius", "Mencius", "Mencius", "east"),
    ("Zhuangzi", "Zhuangzi", "Zhuangzi", "east"),
    ("Buddha", "Gautama Buddha", "Buddha", "east"),
    ("Sun Tzu", "Sun Tzu", "Sun_Tzu", "east"),
    ("Rumi", "Rumi", "Rumi", "east"),
    ("Khalil Gibran", "Kahlil Gibran", "Kahlil_Gibran", "east"),
    ("Alan Watts", "Alan Watts", "Alan_Watts", "bridge"),
    ("Socrates", "Socrates", "Socrates", "west"),
    ("Plato", "Plato", "Plato", "west"),
    ("Aristotle", "Aristotle", "Aristotle", "west"),
    ("Heraclitus", "Heraclitus", "Heraclitus", "west"),
    ("Epicurus", "Epicurus", "Epicurus", "west"),
    ("Marcus Aurelius", "Marcus Aurelius", "Marcus_Aurelius", "west"),
    ("Epictetus", "Epictetus", "Epictetus", "west"),
    ("Seneca", "Seneca the Younger", "Seneca_the_Younger", "west"),
    ("Voltaire", "Voltaire", "Voltaire", "west"),
    ("Jean-Jacques Rousseau", "Jean-Jacques Rousseau", "Jean-Jacques_Rousseau", "west"),
    ("Immanuel Kant", "Immanuel Kant", "Immanuel_Kant", "west"),
    ("Arthur Schopenhauer", "Arthur Schopenhauer", "Arthur_Schopenhauer", "west"),
    ("Søren Kierkegaard", "Søren Kierkegaard", "Søren_Kierkegaard", "west"),
    ("Friedrich Nietzsche", "Friedrich Nietzsche", "Friedrich_Nietzsche", "west"),
    ("Ralph Waldo Emerson", "Ralph Waldo Emerson", "Ralph_Waldo_Emerson", "west"),
    ("Henry David Thoreau", "Henry David Thoreau", "Henry_David_Thoreau", "west"),
    ("William James", "William James", "William_James", "west"),
    ("John Stuart Mill", "John Stuart Mill", "John_Stuart_Mill", "west"),
    ("Bertrand Russell", "Bertrand Russell", "Bertrand_Russell", "west"),
]

def get(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=40)
            if r.status_code == 200:
                return r
            print("  status", r.status_code)
        except Exception as e:
            print("  retry", i, type(e).__name__)
        time.sleep(2.5 * (i + 1))
    return None

def main():
    log = []
    for name, wq_page, wp_article, trad in THINKERS:
        print(name)
        r = get("https://en.wikiquote.org/w/api.php",
                {"action": "parse", "page": wq_page, "prop": "wikitext", "format": "json"})
        ok = False
        if r is not None:
            d = r.json()
            if "parse" in d:
                wt = d["parse"]["wikitext"]["*"]
                (RAW / f"wikiquote_{re.sub(r'[^A-Za-z0-9]+','_',name)}.txt").write_text(wt, encoding="utf-8")
                ok = True
        log.append({"name": name, "wikiquote_page": wq_page, "wikipedia": wp_article,
                    "tradition": trad, "wikiquote_ok": ok})
        time.sleep(1.2)
        # 2025 pageviews (Jan-Sep full months available at run time) + full 2024
        views = {}
        for year, rng in [("2024", "2024010100/2024123100"), ("2025", "2025010100/2025093000")]:
            r = get(f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
                    f"en.wikipedia/all-access/all-agents/{wp_article}/monthly/{rng}")
            if r is not None:
                views[year] = sum(i["views"] for i in r.json().get("items", []))
            time.sleep(1.2)
        log[-1]["pageviews"] = views
        print("   views", views)
    (RAW / "fetch_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print("done", sum(x["wikiquote_ok"] for x in log), "of", len(log))

if __name__ == "__main__":
    main()
