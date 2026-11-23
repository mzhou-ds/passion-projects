"""Reproduce the imperative classifier's held-out validation.

Reads data/processed/validation_labeled.csv (120 sentences, stratified
60 predicted-imperative / 60 predicted-not, seed 2026, hand-labelled) and
reports precision and recall. Run: python3 src/validate_classifier.py
"""
import csv

rows = list(csv.DictReader(open("data/processed/validation_labeled.csv")))
tp = sum(1 for r in rows if r["predicted"] == "imperative" and r["label"] == "1")
fp = sum(1 for r in rows if r["predicted"] == "imperative" and r["label"] == "0")
fn = sum(1 for r in rows if r["predicted"] == "not" and r["label"] == "1")
tn = sum(1 for r in rows if r["predicted"] == "not" and r["label"] == "0")
print(f"n={len(rows)}  TP={tp} FP={fp} FN={fn} TN={tn}")
print(f"precision = {tp/(tp+fp):.1%}   recall = {tp/(tp+fn):.1%}")
print("False positives:")
for r in rows:
    if r["predicted"] == "imperative" and r["label"] == "0":
        print("  -", r["source"], "|", r["sentence"][:100], "|", r["notes"])
print("False negatives:")
for r in rows:
    if r["predicted"] == "not" and r["label"] == "1":
        print("  -", r["source"], "|", r["sentence"][:100], "|", r["notes"])
