"""Build the genealogy: parse declared base-model relations, walk each
model up its family tree to a root, and classify the relation type.

Relation sources (union, typed tags win over untyped card declarations):
  tags:  base_model:<id>                      -> 'declared'
         base_model:finetune:<id>             -> 'finetune'
         base_model:quantized:<id>            -> 'quantized'
         base_model:adapter:<id>              -> 'adapter'
         base_model:merge:<id>                -> 'merge'
  cardData.base_model: [<id>, ...]            -> 'declared'

A model with any base relation is a DERIVATIVE; a model with none is an
ORIGINAL (as far as its own metadata declares). Under-declaration is
common, so every derivative share in this project is a lower bound.

Root resolution walks parent pointers while the parent is itself in the
sample and itself declares a base, with a cycle guard. The FAMILY key is
the root model's author org plus a normalized root name (variant
suffixes like -GGUF / -AWQ / -4bit stripped), so a base and its official
repacks land in one family while distinct bases stay distinct.
"""
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "data" / "models_raw.jsonl"
OUT = HERE / "data" / "models_genealogy.csv"
FAM = HERE / "data" / "families.csv"

REL_TYPES = ("finetune", "quantized", "adapter", "merge")


def parse_relations(row):
    """Return (parent_id, relation_type) or (None, None)."""
    typed = {}
    plain = None
    for t in row.get("tags") or []:
        if not t.startswith("base_model:"):
            continue
        rest = t[len("base_model:"):]
        parts = rest.split(":", 1)
        if len(parts) == 2 and parts[0] in REL_TYPES:
            typed[parts[1]] = parts[0]
        elif rest:
            plain = plain or rest
    if typed:
        # a model can declare several bases (merges do); take the first
        pid, rel = next(iter(typed.items()))
        return pid, rel
    if plain:
        return plain, "declared"
    card = row.get("card_base_model") or []
    if card:
        return card[0], "declared"
    return None, None


SUFFIX_RE = re.compile(
    r"(-gguf|-awq|-gptq|-mlx|-bnb|-4bit|-8bit|-int4|-int8|-fp16|-bf16|"
    r"-quantized|-exl2|-aqlm|-hqq)+$",
    re.IGNORECASE,
)


def family_key(root_id):
    if not isinstance(root_id, str):
        return "unknown"
    if "/" in root_id:
        org, name = root_id.split("/", 1)
    else:
        org, name = "", root_id
    prev = None
    n = name
    while prev != n:
        prev = n
        n = SUFFIX_RE.sub("", n)
    return f"{org.lower()}/{n.lower()}"


def main():
    rows = {}
    samples = {}
    # Merge pass 1 (expand: params, all-time downloads, cardData) and
    # pass 2 (plain: honest downloads/likes/pipeline_tag). The expand
    # endpoint zeroes the non-sorted counter and drops pipeline_tag, so
    # numerics merge by max and categoricals by first non-null.
    plain_path = RAW.parent / "models_plain.jsonl"
    for path in [RAW, plain_path]:
        if not path.exists():
            continue
        with open(path) as fh:
            for line in fh:
                r = json.loads(line)
                mid = r["id"]
                samples.setdefault(mid, set()).add(r["sample"])
                if mid not in rows:
                    rows[mid] = dict(r)
                    continue
                cur = rows[mid]
                for k in ("downloads", "downloadsAllTime", "likes"):
                    cur[k] = max(cur.get(k) or 0, r.get(k) or 0)
                for k in ("pipeline_tag", "library_name", "author",
                          "createdAt", "params", "gated"):
                    if not cur.get(k) and r.get(k):
                        cur[k] = r[k]
                cur["tags"] = sorted(set(cur.get("tags") or []) | set(r.get("tags") or []))
                if r.get("card_base_model"):
                    cur["card_base_model"] = r["card_base_model"]
    print(f"unique models: {len(rows)}")

    recs = []
    for mid, r in rows.items():
        parent, rel = parse_relations(r)
        recs.append(
            {
                "id": mid,
                # both API passes return author=null in list mode; the
                # author namespace is definitionally the id prefix
                "author": r.get("author") or mid.split("/")[0],
                "createdAt": r.get("createdAt"),
                "downloads": r.get("downloads") or 0,
                "downloadsAllTime": r.get("downloadsAllTime") or 0,
                "likes": r.get("likes") or 0,
                "pipeline_tag": r.get("pipeline_tag") or "unspecified",
                "library_name": r.get("library_name"),
                "params": r.get("params"),
                "gated": r.get("gated"),
                "samples": ",".join(sorted(samples[mid])),
                "parent": parent,
                "relation": rel,
            }
        )
    df = pd.DataFrame(recs)
    df["is_derivative"] = df["parent"].notna()

    parent_of = dict(zip(df["id"], df["parent"]))

    def resolve(mid):
        seen = set()
        cur, depth = mid, 0
        while True:
            p = parent_of.get(cur)
            if not isinstance(p, str):
                p = None
            if not p or p == cur or p in seen or p not in parent_of:
                # root is p if a parent outside/at the edge was declared,
                # else the model itself
                return (p if (p and p != cur and p not in seen) else cur), depth + (
                    1 if (p and p != cur and p not in seen) else 0
                )
            seen.add(cur)
            cur, depth = p, depth + 1

    roots, depths = [], []
    for mid in df["id"]:
        root, depth = resolve(mid)
        roots.append(root)
        depths.append(depth)
    df["root"] = roots
    df["depth"] = depths
    df.loc[~df["is_derivative"], "depth"] = 0
    df.loc[~df["is_derivative"], "root"] = df.loc[~df["is_derivative"], "id"]
    df["family"] = df["root"].map(family_key)
    df["root_org"] = df["root"].str.split("/").str[0].str.lower()
    df["created"] = pd.to_datetime(df["createdAt"], errors="coerce", utc=True)
    df["created_year"] = df["created"].dt.year

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(df)} rows)")
    print(f"derivatives (declared): {df['is_derivative'].mean():.1%} of models")

    fam = (
        df.groupby("family")
        .agg(
            root=("root", "first"),
            root_org=("root_org", "first"),
            n_models=("id", "count"),
            n_derivatives=("is_derivative", "sum"),
            downloads=("downloads", "sum"),
            downloadsAllTime=("downloadsAllTime", "sum"),
            likes=("likes", "sum"),
            max_depth=("depth", "max"),
        )
        .reset_index()
        .sort_values("downloads", ascending=False)
    )
    fam.to_csv(FAM, index=False)
    print(f"wrote {FAM} ({len(fam)} families)")
    print(fam.head(15).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
