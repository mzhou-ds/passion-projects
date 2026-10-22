#!/usr/bin/env python3
"""Concentration analysis: Canada (IRCC, by citizenship) vs US (OHSS,
by country of birth), permanent-resident flows 2014/2015-2024, plus
Canada's study-permit pipeline (IRCC temporary residents) if present.

Outputs data/summary.json with every number the README cites.
"""
import csv
import json
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from concentration import hhi, effective_n, top_share, top_country, shares

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    by_year = defaultdict(dict)
    if not path.exists():
        return by_year
    for r in csv.DictReader(path.open()):
        if int(r["persons"]) > 0:
            by_year[int(r["year"])][r["country"]] = int(r["persons"])
    return by_year


def series(by_year, years):
    out = []
    for y in years:
        c = by_year.get(y, {})
        if not c:
            continue
        tc, ts = top_country(c)
        out.append({
            "year": y, "total": sum(c.values()), "n_countries": len(c),
            "hhi": round(hhi(c), 1), "effective_n": round(effective_n(c), 2),
            "top1_country": tc, "top1_share": round(ts, 4),
            "top3_share": round(top_share(c, 3), 4),
            "top5_share": round(top_share(c, 5), 4),
            "top10_share": round(top_share(c, 10), 4),
        })
    return out


def country_path(by_year, name, years):
    return {y: by_year.get(y, {}).get(name, 0) for y in years}


def main():
    us = load(ROOT / "data" / "us_lpr_by_birth_country.csv")
    ca = load(ROOT / "data" / "ca_pr_by_citizenship.csv")
    sp = load(ROOT / "data" / "ca_study_by_citizenship.csv")

    years = list(range(2015, 2025))
    summary = {
        "us_pr": series(us, [2014] + years),
        # 2025 in the IRCC file is Q1 only (Jan-Mar, Aug 2025 snapshot)
        "ca_pr": series(ca, years),
        "ca_pr_2025_q1": series(ca, [2025]),
        "ca_study": series(sp, years),
    }

    # HHI contribution decomposition for the most recent complete year
    # both countries share (2024), and for Canada's peak year.
    def decomp(by_year, y):
        c = by_year.get(y, {})
        sh = shares(c)
        total_hhi = hhi(c)
        top = sorted(sh.items(), key=lambda kv: -kv[1])[:8]
        return {
            "year": y,
            "hhi": round(total_hhi, 1),
            "contributors": [
                {"country": k, "share": round(v, 4),
                 "hhi_points": round((100 * v) ** 2, 1),
                 "pct_of_hhi": round((100 * v) ** 2 / total_hhi * 100, 1)}
                for k, v in top
            ],
        }

    if ca:
        ca_years = sorted(ca)
        peak = max((s for s in summary["ca_pr"] if s["year"] in ca_years),
                   key=lambda s: s["hhi"])
        summary["ca_peak"] = peak
        summary["ca_decomp_2024"] = decomp(ca, 2024)
        summary["ca_decomp_peak"] = decomp(ca, peak["year"])
    summary["us_decomp_2024"] = decomp(us, 2024)

    # The diaspora lens: China + India paths in both systems
    lens = {}
    for label, by_year, names in [
        ("ca", ca, ["India", "China, People's Republic of", "Philippines",
                    "Nigeria", "France"]),
        ("us", us, ["India", "China, People's Republic", "Mexico",
                    "Philippines", "Cuba"]),
    ]:
        if not by_year:
            continue
        lens[label] = {}
        for n in names:
            p = country_path(by_year, n, years)
            tot = {y: sum(by_year.get(y, {}).values()) for y in years}
            lens[label][n] = {
                y: {"persons": p[y],
                    "share": round(p[y] / tot[y], 4) if tot[y] else None}
                for y in years
            }
    summary["diaspora_lens"] = lens

    # Counterfactual: give Canada's 2024 total the US 2024 distribution
    # shape (rescaled) -> what effective N would Canada have had?
    if ca and us:
        ca24, us24 = ca.get(2024, {}), us.get(2024, {})
        if ca24 and us24:
            summary["counterfactual_2024"] = {
                "ca_actual_effective_n": round(effective_n(ca24), 2),
                "ca_with_us_shape_effective_n": round(effective_n(us24), 2),
                "ca_actual_hhi": round(hhi(ca24), 1),
                "ca_with_us_shape_hhi": round(hhi(us24), 1),
            }

    # Per-capita intensity, 2024 (population: StatCan QDE Jan 1 2025 for
    # Canada, 41,528,680; US Census Bureau Jan 1 2025 estimate for the
    # US, 340,110,988). Concentration only matters scaled by flow size.
    if ca and us:
        ca_tot = sum(ca.get(2024, {}).values())
        us_tot = 1364090  # OHSS published FY2024 total
        summary["per_capita_2024"] = {
            "ca_pr_per_100k_residents": round(ca_tot / 41528680 * 100000, 1),
            "us_pr_per_100k_residents": round(us_tot / 340110988 * 100000, 1),
        }
        # Supplier-shock sensitivity: a 25% drop in the top source's flow
        india24 = ca[2024].get("India", 0)
        summary["supplier_shock_2024"] = {
            "india_persons": india24,
            "india_share": round(india24 / ca_tot, 4),
            "total_loss_if_india_minus_25pct": int(india24 * 0.25),
            "pct_of_total_intake": round(india24 * 0.25 / ca_tot * 100, 2),
        }

    out = ROOT / "data" / "summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out}")
    for k in ("ca_pr", "us_pr", "ca_study"):
        for s in summary[k]:
            print(f"{k} {s['year']}: HHI={s['hhi']:7.1f} effN={s['effective_n']:5.2f} "
                  f"top1={s['top1_country']} {s['top1_share']:.1%} total={s['total']:,}")


if __name__ == "__main__":
    main()
