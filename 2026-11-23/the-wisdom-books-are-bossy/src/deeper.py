"""Second-order analysis: what KIND of commands each text issues.

- top imperative verbs per text
- negated-imperative share (commands that forbid: contain not/never/no)
- 'let'-imperative share
- self-address: in Meditations, share of imperatives addressed to 'thou/thy/thyself'
- East vs West: means + permutation test on imperative share
- correlation: imperative share vs second-person rate across the 13 texts
"""
import json, re, random, statistics
from collections import Counter
import sys
sys.path.insert(0, "src")
import analyze as az

rows = json.load(open("data/processed/analysis_results.json"))
by_file = {r["file"]: r for r in rows}

def imp_sents(fname):
    txt = open(f"data/processed/clean/{fname}", encoding="utf-8").read()
    return [s for s in az.split_sentences(txt) if az.is_imperative(s)]

detail = {}
for r in rows:
    imps = imp_sents(r["file"])
    verbs = Counter()
    for s in imps:
        s2 = s
        m = re.match(r"^\s*[\"'\u201c\u2018]*O\s+[A-Za-z\u00c0-\u00ff]+,\s+", s2)
        if m:
            s2 = s2[m.end():]
        s2 = re.sub(r"^\[\s*\d+\s*\]\s*", "", s2.strip())
        w, _ = az.first_content_word(s2)
        verbs[w] += 1
    neg = sum(1 for s in imps if re.search(r"\b(not|never|no|nor)\b", s.lower()))
    let = sum(1 for s in imps if s.strip().lower().lstrip("\"'“‘([ ").startswith("let"))
    second = sum(1 for s in imps if re.search(r"\b(thou|thy|thyself|thee|you|your)\b", s.lower()))
    detail[r["title"]] = {
        "n_imperative": len(imps),
        "top_verbs": verbs.most_common(5),
        "negated_share": 100.0 * neg / max(1, len(imps)),
        "let_share": 100.0 * let / max(1, len(imps)),
        "second_person_share": 100.0 * second / max(1, len(imps)),
    }

for t, d in detail.items():
    print(f"{t:28s} n={d['n_imperative']:4d} neg={d['negated_share']:4.1f}% let={d['let_share']:4.1f}% 2nd={d['second_person_share']:4.1f}%  verbs={d['top_verbs']}")

# East vs West on imperative share
east = [r["imperative_share"] for r in rows if r["tradition"] == "East"]
west = [r["imperative_share"] for r in rows if r["tradition"] == "West"]
print(f"\nEast mean imperative share: {statistics.mean(east):.2f}% (n={len(east)})")
print(f"West mean imperative share: {statistics.mean(west):.2f}% (n={len(west)})")
print(f"East mean negation: {statistics.mean([r['negation_per_1000'] for r in rows if r['tradition']=='East']):.1f} per 1000")
print(f"West mean negation: {statistics.mean([r['negation_per_1000'] for r in rows if r['tradition']=='West']):.1f} per 1000")
print(f"East mean obligation: {statistics.mean([r['obligation_per_1000'] for r in rows if r['tradition']=='East']):.1f} per 1000")
print(f"West mean obligation: {statistics.mean([r['obligation_per_1000'] for r in rows if r['tradition']=='West']):.1f} per 1000")

# permutation test: is the East-West imperative gap bigger than chance?
obs = statistics.mean(west) - statistics.mean(east)
allv = east + west
random.seed(1)
count = 0
for _ in range(10000):
    random.shuffle(allv)
    if statistics.mean(allv[:len(west)]) - statistics.mean(allv[len(west):]) >= obs:
        count += 1
print(f"West-East imperative gap: {obs:.2f}pp; permutation p = {count/10000:.4f} (10,000 shuffles)")

# correlation imperative share vs second-person rate
xs = [r["imperative_share"] for r in rows]
ys = [r["second_person_per_1000"] for r in rows]
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
r = cov / (sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys)) ** 0.5
print(f"corr(imperative share, second-person rate) = {r:.2f} across {len(rows)} texts")
# correlation imperative vs negation
yn = [r["negation_per_1000"] for r in rows]
mn = statistics.mean(yn)
rn = sum((x-mx)*(y-mn) for x, y in zip(xs, yn)) / (sum((x-mx)**2 for x in xs) * sum((y-mn)**2 for y in yn)) ** 0.5
print(f"corr(imperative share, negation rate) = {rn:.2f}")

json.dump(detail, open("data/processed/detail.json", "w"), indent=2, default=str)
