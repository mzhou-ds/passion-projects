"""Inspect NHANES 2013-2014 XPT files: columns, shapes, key variables."""
import pyreadstat
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

for name in ["DR1IFF_H", "DR2IFF_H", "DR1TOT_H", "DXX_H", "MGX_H", "DEMO_H", "BMX_H", "PAQ_H"]:
    df, meta = pyreadstat.read_xport(os.path.join(DATA, name + ".xpt"))
    print(f"== {name}: {df.shape}")
    print("   cols:", list(df.columns)[:40])
    print()
