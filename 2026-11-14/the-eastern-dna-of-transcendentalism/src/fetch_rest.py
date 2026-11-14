#!/usr/bin/env python3
"""Fetch the remaining texts by candidate Gutenberg ID, verifying each
download's header title/author before accepting it. Direct cache URLs are
fast; Gutendex is only used as a last resort for one title."""
import json, os, subprocess, time, re

OUT = "/home/hatch/workspace/passion-projects/2026-11-14/the-eastern-dna-of-transcendentalism/data/raw"
MANIFEST = os.path.join(OUT, "manifest.json")
manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}

# key -> (candidate ids in order, must-match regex on header, label)
CANDIDATES = {
    "emerson_nature":    ([29433], r"Nature", "Emerson"),
    "gita_arnold":       ([23842], r"Song Celestial", "Arnold"),
    "upanishads_muller": ([3283], r"Upanishads", "M"),
    "laws_manu":         ([12956], r"Laws of Manu", "Manu"),
    "vishnu_purana":     ([], r"Vishnu Purana", "Wilson"),
    "kjv":               ([10], r"King James", "Bible"),
    "sartor":            ([1051], r"Sartor Resartus", "Carlyle"),
}

def curl_bytes(url, path, timeout=90):
    for i in range(4):
        r = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), "-A",
                            "MusingWithMike research build (non-commercial)",
                            "-o", path, "-w", "%{http_code}", url],
                           capture_output=True, text=True, timeout=timeout + 10)
        if r.stdout.strip() == "200" and os.path.exists(path) and os.path.getsize(path) > 1000:
            return True
        print(f"  HTTP {r.stdout.strip()} for {url}", flush=True)
        time.sleep(3 * (i + 1))
    return False

def header_ok(path, pattern):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(6000)
        return re.search(pattern, head, re.I) is not None
    except Exception:
        return False

def gutendex_search(query, tries=6):
    for i in range(tries):
        r = subprocess.run(["curl", "-s", "-L", "-m", "60", "-A",
                            "MusingWithMike research build (non-commercial)",
                            "-w", "\n%{http_code}",
                            f"https://gutendex.com/books/?search={query.replace(' ', '%20')}"],
                           capture_output=True, text=True, timeout=75)
        body, _, code = r.stdout.rpartition("\n")
        if code.strip() == "200" and body:
            data = json.loads(body)
            for c in data.get("results", []):
                fmts = c.get("formats", {})
                txt = fmts.get("text/plain; charset=utf-8") or fmts.get("text/plain")
                if txt:
                    return c["id"], c["title"], txt
            return None
        print(f"  gutendex HTTP {code.strip()} (try {i+1})", flush=True)
        time.sleep(5 * (i + 1))
    return None

for key, (ids, pattern, label) in CANDIDATES.items():
    if key in manifest and "bytes" in manifest[key]:
        print(f"{key}: already have it", flush=True)
        continue
    print(f"resolving {key} ...", flush=True)
    got = None
    for gid in ids:
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        path = os.path.join(OUT, f"{key}.txt")
        if curl_bytes(url, path) and header_ok(path, pattern):
            with open(path, encoding="utf-8", errors="ignore") as f:
                head = f.read(3000)
            m = re.search(r"Title:\s*(.+)", head)
            got = {"id": gid, "title": (m.group(1).strip() if m else "?"), "url": url,
                   "bytes": os.path.getsize(path)}
            print(f"  -> #{gid} {got['title']}", flush=True)
            break
        print(f"  #{gid} failed header check or download", flush=True)
    if not got and key == "vishnu_purana":
        res = gutendex_search("Vishnu Purana Wilson")
        if res:
            gid, title, url = res
            path = os.path.join(OUT, f"{key}.txt")
            if curl_bytes(url, path) and header_ok(path, pattern):
                got = {"id": gid, "title": title, "url": url, "bytes": os.path.getsize(path)}
                print(f"  -> #{gid} {title}", flush=True)
    if got:
        manifest[key] = got
    else:
        manifest[key] = {"error": "unresolved"}
        print(f"  !! could not resolve {key}", flush=True)
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    time.sleep(1)

print("DONE")
print(json.dumps({k: v.get("id", v) for k, v in manifest.items()}, indent=2))
