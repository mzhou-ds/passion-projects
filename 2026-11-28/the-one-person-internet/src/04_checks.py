"""Independent verification for The One-Person Internet.

Recomputes the headline numbers straight from data/packages.csv and
data/deps_top200.json with plain pandas (no shared code with 02_analysis.py)
and asserts they match output/findings.json. Also checks every deliverable
file exists and is non-empty, and that the dependency graph is fully
resolved except for the two phantom packages that 404 on the registry.
Exit 0 = all checks pass.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "output"

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        fails.append(name)


def main():
    F = json.load(open(OUT / "findings.json"))
    df = pd.read_csv(DATA / "packages.csv").dropna(subset=["name"])
    df["last_publish"] = pd.to_datetime(df["last_publish"], utc=True, errors="coerce")
    df["age_days"] = (datetime.now(timezone.utc) - df["last_publish"]).dt.days
    df["abandoned"] = df["age_days"] > 730
    df = df.sort_values("weekly_downloads", ascending=False).reset_index(drop=True)
    top = df.head(1000)
    total = top["weekly_downloads"].sum()

    # 1. Headline: solo download share
    solo_dl = top.loc[top["n_maintainers"] <= 1, "weekly_downloads"].sum() / total
    check("solo download share ~53%",
          abs(solo_dl - F["solo_top1000"]["dl_share"]) < 0.001, f"{solo_dl:.4f}")

    # 2. Abandoned download share
    ab_dl = top.loc[top["abandoned"], "weekly_downloads"].sum() / total
    check("abandoned download share ~26%",
          abs(ab_dl - F["abandoned_top1000"]["dl_share"]) < 0.001, f"{ab_dl:.4f}")

    # 3. Solo + abandoned
    sab = top.loc[(top["n_maintainers"] <= 1) & top["abandoned"],
                  "weekly_downloads"].sum() / total
    check("solo+abandoned download share ~16%",
          abs(sab - F["solo_and_abandoned"]["dl_share"]) < 0.001, f"{sab:.4f}")

    # 4. Concentration: top 250 ~ 50%
    cum250 = top["weekly_downloads"].iloc[:250].sum() / total
    check("top 250 carry ~half of top-1000 downloads",
          abs(cum250 - F["concentration"]["top_250"]) < 0.001, f"{cum250:.4f}")

    # 5. Pool sanity: known giants present, top is semver
    for g in ("semver", "react", "lodash", "typescript", "chalk", "express",
              "@babel/parser", "acorn"):
        check(f"pool contains {g}", g in set(df["name"]))
    check("top package is semver", df.iloc[0]["name"] == "semver")

    # 6. Blast radius: dep graph coverage
    deps = json.load(open(DATA / "deps_top200.json"))
    top200 = set(df.head(200)["name"])
    check("deps cover all top 200", all(n in deps for n in top200))
    pool = set(df["name"])
    edges = [(k, c) for k, v in deps.items() if k in top200 for c in v]
    unres = sorted({c for _, c in edges if c not in pool})
    check("only phantom deps unresolved", unres == ["@jest/react-is-18", "@jest/react-is-19"],
          str(unres))
    known = [(k, c) for k, c in edges if c in pool]
    solo_edges = sum(1 for _, c in known
                     if int(df.loc[df["name"] == c, "n_maintainers"].iloc[0]) <= 1)
    solo_frac = solo_edges / len(known)
    check("solo share of dep edges ~57%",
          abs(solo_frac - F["blast_radius"]["solo_share_of_known_dep_edges"]) < 0.001,
          f"{solo_frac:.4f}")

    # 7. Abandonment gradient is monotone in maintainer count
    rates = (top.assign(b=top["n_maintainers"].apply(
        lambda n: "1" if n <= 1 else "2" if n == 2 else "3-5" if n <= 5
        else "6-10" if n <= 10 else "11+"))
        .groupby("b")["abandoned"].mean())
    check("abandonment rate falls with maintainer count",
          rates["1"] > rates["2"] > rates["3-5"] > rates["6-10"] > rates["11+"],
          " ".join(f"{k}:{v:.2f}" for k, v in rates.items()))

    # 8. Deliverables exist and are non-empty
    for p in [BASE / "README.md", BASE / "THREADS_DRAFT.md",
              BASE / "requirements.txt", OUT / "findings.json",
              OUT / "findings.txt"] + sorted((BASE / "charts").glob("*.png")):
        check(f"exists non-empty: {p.name}", p.exists() and p.stat().st_size > 0)
    for p in [BASE / "src" / f"0{i}_" for i in (1, 2, 3)]:
        pass
    for name in ("01_fetch.py", "01b_repair.py", "01c_resolve_deps.py",
                 "02_analysis.py", "03_charts.py", "04_checks.py"):
        p = BASE / "src" / name
        check(f"exists non-empty: {name}", p.exists() and p.stat().st_size > 0)

    print(f"\n{len(fails)} failures" if fails else "\nALL CHECKS PASSED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
