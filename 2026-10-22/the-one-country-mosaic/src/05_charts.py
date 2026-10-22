#!/usr/bin/env python3
"""Charts for 'The One-Country Mosaic' -> charts/*.png"""
import csv
import json
import pathlib
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})

CA_C, US_C = "#d80621", "#1f4e79"  # Canada red, US navy


def load(path):
    by_year = defaultdict(dict)
    if not path.exists():
        return by_year
    for r in csv.DictReader(path.open()):
        if int(r["persons"]) > 0:
            by_year[int(r["year"])][r["country"]] = int(r["persons"])
    return by_year


def main():
    s = json.loads((ROOT / "data" / "summary.json").read_text())
    ca = {x["year"]: x for x in s["ca_pr"]}
    us = {x["year"]: x for x in s["us_pr"]}
    yrs = sorted(set(ca) & set(us))

    # 1. HHI race
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(yrs, [ca[y]["hhi"] for y in yrs], "o-", color=CA_C, lw=2.4,
            label="Canada — permanent residents (by citizenship)")
    ax.plot(yrs, [us[y]["hhi"] for y in yrs], "s-", color=US_C, lw=2.4,
            label="US — green cards (by country of birth)")
    ax.axhline(1500, color="grey", ls=":", lw=1.2)
    ax.text(2015.1, 1560, "DOJ 'moderately concentrated' begins (1,500)",
            color="grey", fontsize=9)
    ax.axhline(2500, color="grey", ls=":", lw=1.2)
    ax.text(2020.9, 2560, "DOJ 'highly concentrated' (2,500)",
            color="grey", fontsize=9)
    ax.set_ylabel("Herfindahl index (HHI, 0–10,000)")
    ax.set_title("The mosaic is the more concentrated market")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(yrs)
    fig.tight_layout(); fig.savefig(CH / "hhi_race.png"); plt.close(fig)

    # 2. Effective number of source countries
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.plot(yrs, [ca[y]["effective_n"] for y in yrs], "o-", color=CA_C,
            lw=2.4, label="Canada")
    ax.plot(yrs, [us[y]["effective_n"] for y in yrs], "s-", color=US_C,
            lw=2.4, label="US")
    ax.set_ylabel("Effective source countries (1/HHI)")
    ax.set_title("Effective source countries: Canada 9–11, the US about 20")
    ax.legend(frameon=False); ax.set_xticks(yrs)
    fig.tight_layout(); fig.savefig(CH / "effective_n.png"); plt.close(fig)

    # 3. Top-1 share
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.plot(yrs, [100 * ca[y]["top1_share"] for y in yrs], "o-",
            color=CA_C, lw=2.4, label="Canada top source (India)")
    ax.plot(yrs, [100 * us[y]["top1_share"] for y in yrs], "s-",
            color=US_C, lw=2.4, label="US top source (Mexico)")
    ax.set_ylabel("Share of all new permanent residents (%)")
    ax.set_title("One flag on the podium: top source country's share")
    ax.legend(frameon=False); ax.set_xticks(yrs)
    fig.tight_layout(); fig.savefig(CH / "top1_share.png"); plt.close(fig)

    # 4. Canada composition, stacked top sources
    ca_raw = load(ROOT / "data" / "ca_pr_by_citizenship.csv")
    focus = ["India", "China", "Philippines", "Nigeria", "France",
             "United States of America", "Pakistan"]
    yrs_ca = [y for y in sorted(ca_raw) if 2015 <= y <= 2024]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bottom = [0.0] * len(yrs_ca)
    cmap = plt.cm.tab10.colors
    for i, name in enumerate(focus):
        vals = []
        for y in yrs_ca:
            tot = sum(ca_raw[y].values())
            vals.append(100 * ca_raw[y].get(name, 0) / tot)
        ax.bar(yrs_ca, vals, bottom=bottom, label=name, color=cmap[i])
        bottom = [b + v for b, v in zip(bottom, vals)]
    rest = [100 - b for b in bottom]
    ax.bar(yrs_ca, rest, bottom=bottom, label="All other countries",
           color="#cccccc")
    ax.set_ylabel("Share of Canada's new PRs (%)")
    ax.set_title("What Canada's intake is made of, 2015–2024")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.set_xticks(yrs_ca)
    fig.tight_layout(); fig.savefig(CH / "ca_composition.png"); plt.close(fig)

    # 5. Study-permit pipeline concentration (if data present)
    if s.get("ca_study"):
        sp = {x["year"]: x for x in s["ca_study"]}
        ys = sorted(sp)
        fig, ax = plt.subplots(figsize=(8.5, 4.2))
        ax.plot(ys, [sp[y]["hhi"] for y in ys], "o-", color="#7d3c98",
                lw=2.4, label="Canada — study permit holders (stock)")
        ax.plot(ys, [ca[y]["hhi"] for y in ys if y in ca], "o--",
                color=CA_C, lw=1.6, label="Canada — new PRs (flow)")
        ax.axhline(2500, color="grey", ls=":", lw=1.2)
        ax.text(ys[0], 2620, "DOJ 'highly concentrated' (2,500)",
                color="grey", fontsize=9)
        ax.set_ylabel("Herfindahl index (HHI)")
        ax.set_title("The pipeline was more concentrated than the destination")
        ax.legend(frameon=False); ax.set_xticks(ys)
        fig.tight_layout(); fig.savefig(CH / "study_pipeline.png")
        plt.close(fig)
    # 6. The baton pass: India vs China share of the study-permit stock
    sp_raw = load(ROOT / "data" / "ca_study_by_citizenship.csv")
    ys = [y for y in sorted(sp_raw) if 2000 <= y <= 2024]
    if ys:
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        for name, color in [("India", "#e67e22"),
                            ("China, People's Republic of", "#c0392b")]:
            vals = [100 * sp_raw[y].get(name, 0) / sum(sp_raw[y].values())
                    for y in ys]
            ax.plot(ys, vals, "o-", color=color, lw=2.2, ms=3.5, label=name)
        ax.set_ylabel("Share of study permit holders in Canada (%)")
        ax.set_title("The baton pass: who supplies Canada's students")
        ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(CH / "baton_pass.png")
        plt.close(fig)
    print("charts done:", sorted(p.name for p in CH.glob("*.png")))


if __name__ == "__main__":
    main()
