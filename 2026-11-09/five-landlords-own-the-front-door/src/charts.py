"""Charts for 'Five Landlords Own the Internet's Front Door'."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.labelcolor": "#222222"})
C_MAIN = "#1f4e79"
C_ACCENT = "#c0392b"
C_MID = "#5b9bd5"
C_GREY = "#9e9e9e"

s = json.load(open("data/summary.json"))
n = s["n_ns_resolved"]

# --- 1. Operator share, top 1000 ---
ops = [("AWS Route 53", 233), ("Self-hosted", 172), ("Cloudflare", 110),
       ("Akamai", 98), ("Google", 72), ("NS1", 58), ("Azure DNS", 36),
       ("Alibaba Cloud", 20), ("UltraDNS", 10), ("Long tail (97 zones)", 181)]
labels = [o for o, _ in ops][::-1]
vals = [v / n * 100 for _, v in ops][::-1]
colors = [C_ACCENT if l == "AWS Route 53" else (C_MID if l in ("Cloudflare", "Akamai", "Google", "NS1") else C_GREY) for l in labels]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.barh(labels, vals, color=colors, height=0.62)
for i, v in enumerate(vals):
    ax.text(v + 0.4, i, f"{v:.1f}%", va="center", fontsize=10)
ax.set_xlim(0, 28)
ax.set_xlabel("Share of the Tranco top 1,000 domains (n=990 resolved)")
ax.set_title("Who answers DNS for the top 1,000 sites?\nAWS Route 53 alone is nearly 1 in 4", fontsize=13, loc="left", pad=12)
plt.tight_layout()
plt.savefig("charts/operator-share.png", dpi=150)
plt.close()

# --- 2. Tier inversion ---
tiers = ["Top 100", "101-500", "501-1000"]
data = {
    "Cloudflare": [2.0, 10.6, 13.3],
    "AWS Route 53": [14.1, 20.5, 27.9],
    "Self-hosted": [21.2, 19.7, 14.7],
    "Google": [15.2, 7.3, 5.7],
    "Azure DNS": [12.1, 4.5, 1.2],
}
import numpy as np
x = np.arange(len(tiers))
w = 0.16
fig, ax = plt.subplots(figsize=(9.5, 5.0))
for i, (k, v) in enumerate(data.items()):
    color = C_ACCENT if k == "Cloudflare" else (C_MAIN if k == "AWS Route 53" else C_MID if k in ("Google", "Azure DNS") else C_GREY)
    ax.bar(x + (i - 2) * w, v, w, label=k, color=color)
ax.set_xticks(x)
ax.set_xticklabels(tiers)
ax.set_ylabel("Share of tier (%)")
ax.set_title("Cloudflare is the landlord of the middle, not the top\nOnly 2 of the top 100 sites use Cloudflare DNS", fontsize=13, loc="left", pad=12)
ax.legend(frameon=False, ncol=3, loc="upper right")
ax.set_ylim(0, 32)
plt.tight_layout()
plt.savefig("charts/tier-inversion.png", dpi=150)
plt.close()

# --- 3. Blast radius: cumulative share of top operators ---
cum_labels = ["Route 53", "+ Cloudflare", "+ Akamai", "+ Google", "+ NS1"]
cum = [23.5, 34.6, 44.5, 51.8, 57.7]
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(cum_labels, cum, color=[C_ACCENT, C_ACCENT, C_ACCENT, C_MAIN, C_MAIN], width=0.6)
for i, v in enumerate(cum):
    ax.text(i, v + 1.2, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
ax.set_ylim(0, 66)
ax.set_ylabel("% of top-1,000 sites whose DNS dies with them")
ax.set_title("Blast radius: if the top 5 DNS operators went dark at once,\n58% of the top 1,000 sites would not resolve", fontsize=13, loc="left", pad=12)
plt.tight_layout()
plt.savefig("charts/blast-radius.png", dpi=150)
plt.close()

# --- 4. CDN layer ---
cdn = [("No CDN detected", 60.1), ("Cloudflare", 18.6), ("CloudFront (AWS)", 8.0),
       ("Akamai", 8.0), ("Vercel", 2.1), ("Google", 1.6), ("Other", 1.6)]
labels = [c for c, _ in cdn][::-1]
vals = [v for _, v in cdn][::-1]
colors = [C_ACCENT if l == "Cloudflare" else (C_MID if l in ("CloudFront (AWS)", "Akamai") else C_GREY) for l in labels]
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.barh(labels, vals, color=colors, height=0.62)
for i, v in enumerate(vals):
    ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=10)
ax.set_xlim(0, 70)
ax.set_xlabel("Share of reachable top-300 sites (n=188, by response headers)")
ax.set_title("The CDN layer: Cloudflare's reach is bigger than its DNS share\n60% of top sites show no CDN at all", fontsize=13, loc="left", pad=12)
plt.tight_layout()
plt.savefig("charts/cdn-share.png", dpi=150)
plt.close()
print("charts written")
