"""01_fetch.py — Download the Billboard Hot 100 weekly history and build the EDM roster.

Data: Billboard Hot 100 weekly charts, 1958-2026, compiled by Christian McDonald
(UT Austin) from Kaggle user Dhruvil Dave's scrape plus additional merging, hosted at
https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/hot100_assignment.csv
(341k+ rows; verified 2026-11-12 to run through the chart dated 2026-11-14).

Roster: curated EDM/DJ-producer acts. Starts from the 149-artist list built for the
2026-10-06 subgenre build (hidden_files/edm_artist_list.json) plus chart-era headliners.
Explicitly excluded: vocalists/songwriters who only sing on dance tracks (Kimbra,
MNEK, Sophie Ellis-Bextor), rappers (French Montana, Baby Tate), and non-dance acts
that collide on names (Gotye, Kirk Franklin). Single-token short names (ZHU, ATB, GTA,
Ame) are excluded from matching: they cannot be matched safely by token and none of
them has a Hot 100 entry as a credited performer in 2010-2026 (verified in 02_classify).
Boundary calls (documented, not hidden): LMFAO excluded (party-pop duo, not DJ/producers);
Clean Bandit and Rudimental included (electronic-led acts whose chart entries are
produced as dance records); Disciples and Tujamo included (dance production acts).
Grey (the duo) excluded despite two real entries, because the token "grey" also
matches Capella Grey and Skylar Grey and creates false positives; both real Grey
entries still match through their other credited EDM act (Zedd).
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)

HOT100_URL = "https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/hot100_assignment.csv"

BASE_LIST = "/home/hatch/workspace/goals/daily-builds-passion-projects-on-github/hidden_files/edm_artist_list.json"

EXTRA = """Avicii, Calvin Harris, David Guetta, Zedd, Skrillex, Diplo, Major Lazer, The Chainsmokers,
Marshmello, Martin Garrix, Tiësto, deadmau5, Disclosure, Flume, Kygo, Alan Walker, DJ Snake, Steve Aoki,
Afrojack, Hardwell, Alesso, Swedish House Mafia, Axwell, Sebastian Ingrosso, Steve Angello, Eric Prydz,
Kaskade, Porter Robinson, Madeon, Dillon Francis, RL Grime, Baauer, Flosstradamus, Yellow Claw,
Knife Party, Nero, Chase & Status, Rudimental, Clean Bandit, Duke Dumont, Gorgon City, Sonny Fodera,
Fisher, Dom Dolla, John Summit, Fred again.., Peggy Gou, Anyma, Tale Of Us, Charlotte de Witte,
Amelie Lens, Meduza, Joel Corry, Jax Jones, Sigala, Jonas Blue, Galantis, Cheat Codes, NOTD, Loud Luxury,
R3hab, Don Diablo, Oliver Heldens, Tchami, Malaa, Habstrakt, Valentino Khan, Kayzo, Illenium, Seven Lions,
Excision, Zeds Dead, Adventure Club, Gryffin, Said The Sky, San Holo, What So Not, ODESZA, Big Gigantic,
Louis The Child, Whethan, Jai Wolf, Petit Biscuit, Kaytranada, SG Lewis, Elderbrook, Bonobo, Four Tet,
Bicep, Caribou, Jamie xx, Jack Ü, Silk City, AlunaGeorge, KSHMR, Nicky Romero, W&W, Dash Berlin,
Armin van Buuren, Above & Beyond, Gareth Emery, Ferry Corsten, Paul van Dyk, Tiesto,
Disciples, Tujamo"""

# Names that look dance-adjacent but are vocalists, rappers, or non-dance acts.
EXCLUDE = {
    "French Montana", "Gotye", "Kimbra", "Baby Tate", "Kirk", "Sophie Ellis-Bextor",
    "MNEK", "Cake", "Goldie", "Nafe Smallz", "95 South", "54 Ultra", "LaBritney",
    "Natalie Williams", "Poppy Baskcomb", "Lizwi", "Joni", "Desmond", "Kirk Franklin",
    "Mili", "Kenny Beats", "Grey",
}


def main():
    out = RAW / "hot100.csv"
    print("downloading Hot 100 history ...")
    req = urllib.request.Request(HOT100_URL, headers={"User-Agent": "MusingWithMike/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    out.write_bytes(data)
    print(f"wrote {out} ({len(data)/1e6:.1f} MB)")

    base = json.load(open(BASE_LIST))
    names = set()
    for a in base:
        a = re.sub(r"\s*\([^)]*\)", "", a).strip()
        if a and a not in EXCLUDE:
            names.add(a)
    for a in EXTRA.split(","):
        a = a.strip()
        if a and a not in EXCLUDE:
            names.add(a)
    roster = sorted(names)
    (DATA / "edm_roster.json").write_text(json.dumps(roster, indent=1, ensure_ascii=False))
    print(f"roster: {len(roster)} EDM acts -> data/edm_roster.json")


if __name__ == "__main__":
    main()
