"""Validate PBF files by fully reading them (truncation raises)."""
import sys, osmium
from pathlib import Path

class Counter(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.n = 0
    def node(self, nd):
        self.n += 1

for name in sys.argv[1:]:
    p = Path(name)
    h = Counter()
    try:
        h.apply_file(str(p), locations=False)
        print(f"OK {p.name}: {h.n} nodes read cleanly", flush=True)
    except Exception as ex:  # noqa: BLE001
        print(f"TRUNCATED/ERROR {p.name}: {type(ex).__name__}: {ex}", flush=True)
