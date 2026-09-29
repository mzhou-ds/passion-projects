"""Print top-k pairs per modern item for hand calibration."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
backend = sys.argv[1] if len(sys.argv) > 1 else "minilm"
d = json.load(open(os.path.join(PROJ, "data", "scores_%s.json" % backend)))
for m in d["modern"]:
    print("=" * 100)
    print(f"[{m['id']}] {m['label']}\n  MODERN: {m['text']}")
    for t in m["top3"]:
        print(f"  [{t['score']:.3f}] Bk{t['book']}.{t['chap']} ({t['theme']}): {t['text'][:300]}")
