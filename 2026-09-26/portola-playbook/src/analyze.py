"""Portola Playbook analysis: attention economics, schedule optimizer, resale market."""
import csv, json, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

# Effective draw: the duo/project page understates the live draw for these bills.
# DOG BLOOD = Skrillex + Boys Noize (first joint set in 7 years); use Skrillex's
# monthly listeners as the conservative effective draw, noted in the README.
EFFECTIVE_DRAW = {norm("DOG BLOOD"): 21117443}

# ---------- load ----------
lineup = {}   # norm -> dict
with open("data/lineup.csv") as f:
    for r in csv.DictReader(f):
        lineup[norm(r["artist"])] = {"artist": r["artist"], "tier": int(r["billing_tier"]),
                                     "day": r["day"], "poster_rank": r["poster_rank"]}
listeners = {}
with open("data/spotify_listeners.json") as f:
    for r in json.load(f):
        listeners[norm(r["artist"])] = r["monthly_listeners"] or 0
for k, v in EFFECTIVE_DRAW.items():
    listeners[k] = v
sched = []
with open("data/schedule.csv") as f:
    for r in csv.DictReader(f):
        sched.append(r)

def to_min(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m  # all PM

# ---------- 1. attention concentration ----------
vals = [(v["artist"], listeners[norm(v["artist"])], v["tier"], v["day"])
        for v in lineup.values()]
vals.sort(key=lambda x: -x[1])
total = sum(v[1] for v in vals)
top5_share = sum(v[1] for v in vals[:5]) / total
top10_share = sum(v[1] for v in vals[:10]) / total
print(f"total lineup attention: {total/1e6:.0f}M monthly listeners")
print(f"top 5 share: {top5_share:.1%}, top 10 share: {top10_share:.1%}")
print("top 10:", [(v[0], f"{v[1]/1e6:.1f}M") for v in vals[:10]])

# ---------- 2. billing vs attention mispricing ----------
# attention rank (1 = most listeners) vs billing tier (1 = headliner)
att_rank = {v[0]: i + 1 for i, v in enumerate(vals)}
rows = []
for artist, ml, tier, day in vals:
    rows.append({"artist": artist, "listeners": ml, "tier": tier, "day": day,
                 "att_rank": att_rank[artist]})
# mispriced = low tier number (small bill) but high attention rank (big number) -> over-billed
# or high tier number (big bill... tier 5 = small) with small attention rank -> under-billed
# define: expected tier from attention rank via quintiles; gap = tier - expected_tier
n = len(rows)
for r in rows:
    r["expected_tier"] = min(5, max(1, int((r["att_rank"] - 1) / n * 5) + 1))
    r["gap"] = r["tier"] - r["expected_tier"]  # positive = billed below their attention (value)
under = sorted([r for r in rows if r["listeners"] > 0], key=lambda r: -r["gap"])[:8]
over = sorted([r for r in rows if r["listeners"] > 0], key=lambda r: r["gap"])[:8]
print("\nmost UNDER-billed (attention >> billing):")
for r in under:
    print(f"  {r['artist']:28s} tier {r['tier']} | {r['listeners']/1e6:6.1f}M listeners | att rank #{r['att_rank']}")
print("most OVER-billed (billing >> attention):")
for r in over:
    print(f"  {r['artist']:28s} tier {r['tier']} | {r['listeners']/1e6:6.1f}M listeners | att rank #{r['att_rank']}")

# fig1: billing tier vs listeners
fig, ax = plt.subplots(figsize=(9, 5.5))
tiers = [r["tier"] for r in rows if r["listeners"] > 0]
mls = [r["listeners"] for r in rows if r["listeners"] > 0]
ax.scatter(tiers, mls, alpha=0.55, s=42, color="#7b2ff7")
ax.set_yscale("log")
ax.set_xlabel("Billing tier (1 = headliner, 5 = small print)")
ax.set_ylabel("Spotify monthly listeners (log)")
ax.set_title("Portola 2026: billing vs. actual attention")
ax.set_xticks([1, 2, 3, 4, 5])
for r in rows:
    if r["artist"] in ("Zara Larsson", "ADÉLA", "Tove Lo", "Robyn", "DOG BLOOD",
                       "Swedish House Mafia", "Soulwax", "Prospa", "oskar med k",
                       "Marlon Hoffstadt", "Tiësto"):
        ax.annotate(r["artist"], (r["tier"], r["listeners"]), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")
fig.tight_layout(); fig.savefig("figures/fig1_billing_vs_attention.png"); plt.close(fig)

# fig2: concentration bars
fig, ax = plt.subplots(figsize=(9, 4.5))
top12 = vals[:12]
ax.barh([v[0] for v in top12][::-1], [v[1] / 1e6 for v in top12][::-1], color="#ff5e3a")
ax.set_xlabel("Spotify monthly listeners (millions)")
ax.set_title("Portola 2026: the 12 biggest draws own the weekend's attention")
for i, v in enumerate(top12):
    ax.text(v[1] / 1e6 + 0.4, 11 - i, f"{v[1]/1e6:.1f}M", va="center", fontsize=8)
fig.tight_layout(); fig.savefig("figures/fig2_attention_concentration.png"); plt.close(fig)

# ---------- 3. Beatport heat cross ----------
chart_hits = {}
with open("data/beatport_tracks.csv") as f:
    rd = csv.DictReader(f)
    cols = rd.fieldnames
    for row in rd:
        credit = f"{row['artists']} {row.get('remixers','')}"
        for key, v in lineup.items():
            na = norm(credit)
            if key and len(key) > 3 and key in na:
                chart_hits.setdefault(v["artist"], set()).add(row["chart"])
                break
print(f"\n{len(chart_hits)} lineup artists on Beatport Top 100s right now:")
for a, charts in sorted(chart_hits.items(), key=lambda x: -len(x[1])):
    print(f"  {a}: {sorted(charts)}")
json.dump({k: sorted(v) for k, v in chart_hits.items()},
          open("data/beatport_hits.json", "w"), indent=1)

# ---------- 4. schedule optimizer (weighted interval scheduling) ----------
def optimize(day):
    slots = []
    for s in sched:
        if s["day"] != day or s["artist"] == "DESPACIO":
            continue
        ml = listeners.get(norm(s["artist"]), 0)
        dur = to_min(s["end"]) - to_min(s["start"])
        if dur <= 0:
            dur += 720
        slots.append({"artist": s["artist"], "stage": s["stage"],
                      "start": to_min(s["start"]), "end": to_min(s["end"]),
                      "s": s["start"], "e": s["end"],
                      "weight": ml * dur, "ml": ml, "dur": dur})
    slots.sort(key=lambda x: x["end"])
    ends = [x["end"] for x in slots]
    # p[i] = last slot ending <= slots[i].start
    import bisect
    p = [bisect.bisect_right(ends, slots[i]["start"]) - 1 for i in range(len(slots))]
    dp = [0] * len(slots)
    for i in range(len(slots)):
        incl = slots[i]["weight"] + (dp[p[i]] if p[i] >= 0 else 0)
        excl = dp[i - 1] if i > 0 else 0
        dp[i] = max(incl, excl)
    # reconstruct
    chosen, i = [], len(slots) - 1
    while i >= 0:
        incl = slots[i]["weight"] + (dp[p[i]] if p[i] >= 0 else 0)
        excl = dp[i - 1] if i > 0 else 0
        if incl >= excl:
            chosen.append(slots[i]); i = p[i]
        else:
            i -= 1
    chosen.sort(key=lambda x: x["start"])
    total_w = sum(s["weight"] for s in slots)
    got_w = sum(s["weight"] for s in chosen)
    return chosen, got_w / total_w if total_w else 0

itineraries = {}
for day in ("Sat", "Sun"):
    chosen, frac = optimize(day)
    itineraries[day] = chosen
    print(f"\n=== optimal {day} itinerary ({frac:.0%} of day's attention) ===")
    for c in chosen:
        print(f"  {c['s']:>5s}-{c['e']:<5s} {c['stage']:<12s} {c['artist']:28s} {c['ml']/1e6:5.1f}M")

# biggest conflicts: overlapping pairs, cost = min(ml_a, ml_b) lost
def conflicts(day):
    slots = [{"artist": s["artist"], "start": to_min(s["start"]), "end": to_min(s["end"]),
              "ml": listeners.get(norm(s["artist"]), 0)}
             for s in sched if s["day"] == day and s["artist"] != "DESPACIO"]
    out = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            a, b = slots[i], slots[j]
            if a["start"] < b["end"] and b["start"] < a["end"]:
                ov = min(a["end"], b["end"]) - max(a["start"], b["start"])
                if ov >= 20:
                    out.append((min(a["ml"], b["ml"]) * ov, a["artist"], b["artist"], ov))
    return sorted(out, reverse=True)[:6]

print("\ncostliest conflicts (listener-minutes you must leave on the table):")
conf = {}
for day in ("Sat", "Sun"):
    conf[day] = conflicts(day)
    print(f" {day}:")
    for cost, a, b, ov in conf[day]:
        print(f"   {a} vs {b} ({ov} min overlap)")

# ---------- 5. resale market ----------
resale = list(csv.DictReader(open("data/resale_prices.csv")))
face = {"2-Day GA": 379.95, "Saturday GA": 249.95, "Sunday GA": 249.95}
primary_now = {"2-Day GA": 399.95, "Saturday GA": 269.95, "Sunday GA": 269.95}
print("\n=== resale vs face (game day) ===")
for tt in ("2-Day GA", "Saturday GA", "Sunday GA"):
    asks = [(r["platform"], float(r["from_price_usd"])) for r in resale
            if r["ticket_type"] == tt and not r["platform"].startswith("PRIMARY")]
    asks.sort(key=lambda x: x[1])
    lo, hi = asks[0][1], asks[-1][1]
    print(f"{tt}: face ${face[tt]:.2f} | primary now ${primary_now[tt]:.2f} | "
          f"resale asks ${lo:.0f}–${hi:.0f} (spread {hi/lo-1:.0%})")
    for p, pr in asks:
        prem = pr / face[tt] - 1
        print(f"    {p:34s} ${pr:>7.0f}  {prem:+.0%} vs face")

# fig3: resale by platform
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
for ax, tt in zip(axes, ("2-Day GA", "Saturday GA", "Sunday GA")):
    asks = [(r["platform"].replace(" (portolamusicfestival.com)", ""), float(r["from_price_usd"]))
            for r in resale if r["ticket_type"] == tt]
    asks.sort(key=lambda x: x[1])
    labels = [a[0].replace("SF.events aggregator", "SF.events").replace("PRIMARY", "Primary") for a in asks]
    colors = ["#2ca02c" if "PRIMARY" in a[0] else "#1f77b4" for a in asks]
    ax.barh(labels, [a[1] for a in asks], color=colors)
    ax.axvline(face[tt], color="red", linestyle="--", linewidth=1)
    ax.set_title(tt)
    ax.set_xlabel("cheapest ask (USD)")
axes[0].set_ylabel("")
fig.suptitle("Portola game-day resale: cheapest ask by platform (red dashed = original face value)")
fig.tight_layout(); fig.savefig("figures/fig3_resale_by_platform.png"); plt.close(fig)

# save summary for README
summary = {
    "total_attention_m": round(total / 1e6),
    "top5_share": round(top5_share, 3),
    "top10_share": round(top10_share, 3),
    "under_billed": [{"artist": r["artist"], "tier": r["tier"],
                      "listeners_m": round(r["listeners"] / 1e6, 1),
                      "att_rank": r["att_rank"]} for r in under],
    "over_billed": [{"artist": r["artist"], "tier": r["tier"],
                     "listeners_m": round(r["listeners"] / 1e6, 1),
                     "att_rank": r["att_rank"]} for r in over],
    "beatport_charting": sorted(chart_hits.keys()),
    "itineraries": {d: [{"start": c["s"], "end": c["e"], "stage": c["stage"],
                         "artist": c["artist"], "listeners_m": round(c["ml"] / 1e6, 1)}
                        for c in itineraries[d]] for d in itineraries},
    "attention_captured": {d: round(sum(c["weight"] for c in itineraries[d]) /
                                   sum((listeners.get(norm(s["artist"]), 0)) *
                                       (to_min(s["end"]) - to_min(s["start"]))
                                       for s in sched if s["day"] == d and s["artist"] != "DESPACIO"), 3)
                           for d in ("Sat", "Sun")},
}
json.dump(summary, open("data/summary.json", "w"), indent=1)
print("\nwrote data/summary.json")
