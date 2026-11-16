"""Print value labels / column labels for key variables."""
import pyreadstat
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

df, meta = pyreadstat.read_xport(os.path.join(DATA, "DR1IFF_H.xpt"), metadataonly=False)
print("DR1_030Z labels:", meta.value_labels.get("DR1_030Z"))
print("DR1_020 sample:", df["DR1_020"].dropna().head(10).tolist())
print("DR1DRSTZ labels:", meta.value_labels.get("DR1DRSTZ"))
print("DR1DRSTZ counts:", df["DR1DRSTZ"].value_counts(dropna=False).to_dict())

df, meta = pyreadstat.read_xport(os.path.join(DATA, "DXX_H.xpt"))
labels = dict(zip(meta.column_names, meta.column_labels))
print("\nDXX_H columns:")
for c in df.columns:
    print("  ", c, "-", labels.get(c, ""))
print("DXAEXSTS labels:", meta.value_labels.get("DXAEXSTS"))

df, meta = pyreadstat.read_xport(os.path.join(DATA, "MGX_H.xpt"))
labels = dict(zip(meta.column_names, meta.column_labels))
print("\nMGX_H columns:")
for c in df.columns:
    print("  ", c, "-", labels.get(c, ""))
print("MGDEXSTS labels:", meta.value_labels.get("MGDEXSTS"))

df, meta = pyreadstat.read_xport(os.path.join(DATA, "PAQ_H.xpt"))
labels = dict(zip(meta.column_names, meta.column_labels))
for c in ["PAQ650", "PAQ665", "PAD680", "PAQ605", "PAQ620"]:
    print(c, "-", labels.get(c, ""), meta.value_labels.get(c))

# Empirical check: meal code vs time of day
import pandas as pd
df, meta = pyreadstat.read_xport(os.path.join(DATA, "DR1IFF_H.xpt"))
df["hour"] = df["DR1_020"].apply(lambda t: t.hour if pd.notna(t) else None)
print("\nMeal code x median hour / protein:")
print(df.groupby("DR1_030Z").agg(n=("SEQN", "size"), med_hour=("hour", "median"),
                                  mean_prot=("DR1IPROT", "mean")).to_string())
