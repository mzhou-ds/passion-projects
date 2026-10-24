#!/usr/bin/env python3
"""
03_audio.py — Measure the DJ intro from 30-second preview audio (v2).

Lesson from v1 (kept in git history): RMS peak-crossing cannot see a
dance intro. A bare kick is already loud, and a chord pad is sustained,
so "time to 50% of peak volume" fires instantly in every era. What a
DJ intro actually is, acoustically, is *dark and sparse*: kick, bass,
maybe hats — very little energy above ~1.2 kHz — while the full
arrangement (vocals, synths, cymbals) is bright. So v2 measures the
preview's spectral shape per second (one ffmpeg decode per track):

- cent_first3 / cent_mean / cent_last5: spectral centroid (Hz)
- dark_share_10 / dark_share_30: share of seconds whose centroid is
  below 1200 Hz — "seconds where the record has not really started"
- lf_share_mean: mean share of spectral energy below 150 Hz, computed
  on 3s windows (1s windows alias against the kick period)
- rms_cv_10: coefficient of variation of 100ms RMS over the first 10s
  (a sparse beat pattern breathes; a filled arrangement does not)
- rms_slope_15: normalised slope of per-second RMS over 15s (builds)

Sampling is stratified by panel x coarse era x length bucket, because
the hypothesis is specific: the intro lived in LONG cuts. If long cuts
lost their dark openings while short cuts never had them, that is the
intro dying with the extended mix, not a general loudness trend.

Outputs: data/preview_features.csv, data/audio_stats.json
Per-track features cached as JSON under data/previews2/.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PREV = ROOT / "data" / "previews2"
PREV.mkdir(parents=True, exist_ok=True)

COARSE = {"1990s": "pre2010", "2000-04": "pre2010", "2005-09": "pre2010",
          "2010-14": "2010s", "2015-19": "2010s", "2020-26": "2020s"}
# (panel, coarse, bucket) -> target n ; bucket: long >=330s, short <=225s
TARGET = {
    ("dance", "pre2010", "long"): 110, ("dance", "pre2010", "short"): 110,
    ("dance", "2010s", "long"): 90, ("dance", "2010s", "short"): 90,
    ("dance", "2020s", "long"): 110, ("dance", "2020s", "short"): 110,
    ("pop", "pre2010", "mid"): 80, ("pop", "2020s", "mid"): 80,
}
SEED = 48
SR = 22050
DARK_HZ = 1200.0


def decode(url: str) -> np.ndarray | None:
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", url, "-ac", "1", "-ar", str(SR),
             "-f", "f32le", "-"],
            capture_output=True, timeout=60,
        ).stdout
        if len(raw) < SR * 4 * 25:
            return None
        return np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    except Exception:
        return None


def track_features(x: np.ndarray) -> dict:
    nsec = min(30, len(x) // SR)
    cents, secs_rms, lf3 = [], [], []
    for s in range(nsec):
        seg = x[s * SR:(s + 1) * SR]
        secs_rms.append(float(np.sqrt((seg ** 2).mean())))
        mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        freqs = np.fft.rfftfreq(len(seg), 1 / SR)
        cents.append(float((freqs * mag).sum() / max(mag.sum(), 1e-9)))
    for s in range(0, nsec - 2, 3):  # 3s windows for LF share (kick aliasing)
        seg = x[s * SR:(s + 3) * SR]
        mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        freqs = np.fft.rfftfreq(len(seg), 1 / SR)
        lf3.append(float(mag[freqs < 150].sum() / max(mag.sum(), 1e-9)))
    cents = np.array(cents)
    secs_rms = np.array(secs_rms)
    win = SR // 10
    n = (10 * SR) // win
    frames = x[: n * win].reshape(n, win)
    rms100 = np.sqrt((frames ** 2).mean(axis=1))
    slope = float(np.polyfit(np.arange(min(15, nsec)), secs_rms[:15], 1)[0]
                  / max(secs_rms.mean(), 1e-9)) if nsec >= 15 else np.nan
    return {
        "cent_first3": float(cents[:3].mean()),
        "cent_mean": float(cents.mean()),
        "cent_last5": float(cents[-5:].mean()),
        "cent_rise": float(cents[-5:].mean() - cents[:3].mean()),
        "dark_share_10": float((cents[:10] < DARK_HZ).mean()),
        "dark_share_30": float((cents < DARK_HZ).mean()),
        "lf_share_mean": float(np.mean(lf3)) if lf3 else np.nan,
        "rms_cv_10": float(rms100.std() / max(rms100.mean(), 1e-9)),
        "rms_slope_15": slope,
        "rms_first3_share": float(secs_rms[:3].mean() / max(secs_rms.max(), 1e-9)),
    }


def bucket_of(panel: str, seconds: float) -> str | None:
    if panel == "pop":
        return "mid"
    if seconds >= 330:
        return "long"
    if seconds <= 225:
        return "short"
    return None


def main() -> None:
    df = pd.read_csv(ROOT / "data" / "tracks_clean.csv")
    df["coarse"] = df["era"].map(COARSE)
    df = df[df["preview"].notna() & (df["preview"] != "") & (df["seconds"] >= 120)]
    df["bucket"] = [bucket_of(p, s) for p, s in zip(df["panel_query"], df["seconds"])]
    df = df[df["bucket"].notna()]
    picks = []
    for (panel, coarse, bucket), target in TARGET.items():
        sub = df[(df["panel_query"] == panel) & (df["coarse"] == coarse)
                 & (df["bucket"] == bucket)]
        take = sub.sample(n=min(target, len(sub)), random_state=SEED)
        picks.append(take)
        print(f"{panel}/{coarse}/{bucket}: sampled {len(take)} of {len(sub)}", flush=True)
    sample = pd.concat(picks).reset_index(drop=True)

    rows = []
    for _, r in sample.iterrows():
        tid = int(r["track_id"])
        cache = PREV / f"feat_{tid}.json"
        if cache.exists():
            f = json.loads(cache.read_text())
        else:
            x = decode(str(r["preview"]))
            if x is None:
                continue
            f = track_features(x)
            cache.write_text(json.dumps(f))
        rows.append({**r[["track_id", "track_name", "artist", "panel_query", "era",
                           "coarse", "bucket", "year", "seconds", "version"]].to_dict(),
                     **f})
        if len(rows) % 50 == 0:
            print(f"  decoded {len(rows)}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "data" / "preview_features.csv", index=False)
    print(f"features for {len(out)} previews")

    agg = (
        out.groupby(["panel_query", "coarse", "bucket"])
        .agg(n=("track_id", "count"),
             cent_first3=("cent_first3", "median"),
             dark10=("dark_share_10", "median"),
             share_dark_majority=("dark_share_10", lambda s: (s >= 0.5).mean()),
             lf=("lf_share_mean", "median"),
             cv10=("rms_cv_10", "median"),
             rise=("cent_rise", "median"))
        .reset_index()
    )
    print(agg.to_string(index=False))
    (ROOT / "data" / "audio_stats.json").write_text(
        json.dumps({"by_group": agg.to_dict("records")}, indent=2, default=str)
    )


if __name__ == "__main__":
    main()
