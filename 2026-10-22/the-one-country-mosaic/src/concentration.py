#!/usr/bin/env python3
"""Concentration metrics shared by the analysis.

HHI here is the antitrust Herfindahl-Hirschman Index applied to
immigration source countries: sum of squared percentage shares
(0-10,000 scale). DOJ bands: <1,500 competitive, 1,500-2,500 moderately
concentrated, >2,500 highly concentrated. 'Effective countries' is the
inverse-HHI numbers equivalent: the number of equal-sized sources that
would produce the same concentration.
"""
import math


def shares(counts: dict) -> dict:
    tot = sum(counts.values())
    return {k: v / tot for k, v in counts.items()} if tot else {}


def hhi(counts: dict) -> float:
    return sum((100 * s) ** 2 for s in shares(counts).values())


def effective_n(counts: dict) -> float:
    sh = shares(counts)
    h = sum(s * s for s in sh.values())
    return 1 / h if h else float("nan")


def top_share(counts: dict, k: int) -> float:
    sh = sorted(shares(counts).values(), reverse=True)
    return sum(sh[:k])


def entropy(counts: dict) -> float:
    return -sum(s * math.log(s) for s in shares(counts).values() if s > 0)


def top_country(counts: dict) -> tuple:
    sh = shares(counts)
    if not sh:
        return (None, 0.0)
    k = max(sh, key=sh.get)
    return (k, sh[k])
