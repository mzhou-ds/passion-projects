"""Download BBBike city PBF extracts (detached; logs to download.log)."""
import subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PBF = BASE / "data" / "pbf"
PBF.mkdir(parents=True, exist_ok=True)
NAMES = ["Vancouver", "Toronto", "Montreal", "Calgary", "Edmonton", "Ottawa",
         "Winnipeg", "Halifax", "SanFrancisco", "LosAngeles", "NewYork",
         "Seattle", "Boston", "Chicago", "Houston", "Portland"]
log = open(BASE / "download.log", "w")
for name in NAMES:
    out = PBF / f"{name}.osm.pbf"
    if out.exists() and out.stat().st_size > 100000:
        print(f"skip {name}", flush=True); log.write(f"skip {name}\n"); log.flush()
        continue
    url = f"https://download.bbbike.org/osm/bbbike/{name}/{name}.osm.pbf"
    r = subprocess.run(["curl", "-s", "-L", "-m", "600", "-o", str(out), url])
    sz = out.stat().st_size if out.exists() else 0
    print(f"{name}: rc={r.returncode} {sz} bytes", flush=True)
    log.write(f"{name}: rc={r.returncode} {sz}\n"); log.flush()
print("downloads done")
