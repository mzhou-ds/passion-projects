"""Fetch live job postings from public Greenhouse boards (no auth needed).

Greenhouse exposes a public Job Board API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
We pull title, location, departments, offices, first_published/updated_at and the
posting text (content=true), then store a compact extract. Raw responses are kept
in /tmp (too large for the repo); only the compact extract is committed.
Boards that 404 (company moved to Workday/Lever/Ashby or another ATS) are recorded
in data/board_status.json so coverage is auditable.
"""
import json, os, re, time, urllib.request, html

BOARDS = [
    # Big tech / late-stage, Greenhouse-hosted (verified live 2026-11-18)
    "airbnb", "stripe", "databricks", "coinbase", "robinhood", "figma", "lyft",
    "pinterest", "reddit", "block", "dropbox", "asana", "twilio", "datadog",
    "duolingo", "instacart", "roblox", "mongodb", "elastic", "gitlab", "okta",
    "cloudflare", "brex", "chime", "sofi", "affirm", "toast", "anthropic",
    "scaleai", "vercel", "fivetran", "launchdarkly", "cockroachlabs", "airtable",
    "intercom", "gusto", "discord", "wise", "ramp", "netlify",
]
RAW_DIR = "/tmp/gh_raw"
OUT = "/tmp/gh_raw.jsonl"  # kept out of the repo: 36MB of posting text
STATUS = os.path.join(os.path.dirname(__file__), "..", "data", "board_status.json")

def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()

def fetch_board(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; MusingWithMike)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    status, n_total = {}, 0
    with open(OUT, "w") as fh:
        for slug in BOARDS:
            try:
                data = fetch_board(slug)
                jobs = data.get("jobs", [])
                with open(os.path.join(RAW_DIR, f"{slug}.json"), "w") as rf:
                    json.dump(data, rf)
                for j in jobs:
                    fh.write(json.dumps({
                        "company": slug,
                        "id": j.get("id"),
                        "title": j.get("title"),
                        "location": (j.get("location") or {}).get("name"),
                        "departments": [d.get("name") for d in j.get("departments") or []],
                        "offices": [o.get("name") for o in j.get("offices") or []],
                        "first_published": j.get("first_published"),
                        "updated_at": j.get("updated_at"),
                        "url": j.get("absolute_url"),
                        "description": strip_html(j.get("content"))[:4000],
                    }) + "\n")
                status[slug] = {"ok": True, "n": len(jobs)}
                n_total += len(jobs)
                print(f"{slug}: {len(jobs)}")
            except Exception as e:
                status[slug] = {"ok": False, "error": str(e)[:120]}
                print(f"{slug}: ERROR {e}")
            time.sleep(0.4)
    with open(STATUS, "w") as f:
        json.dump(status, f, indent=2)
    print("TOTAL JOBS:", n_total, "| boards ok:", sum(1 for v in status.values() if v["ok"]))

if __name__ == "__main__":
    main()
