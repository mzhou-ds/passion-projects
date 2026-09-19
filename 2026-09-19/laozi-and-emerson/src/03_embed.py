"""Embed every sentence with LSA (TF-IDF 1-2 grams -> TruncatedSVD).

Why LSA here: on this single-domain corpus (philosophy/spirituality), the
shared vocabulary IS the signal — parallel passages ("desire", "content",
"stillness", "the sage") share terms, and LSA's topic directions capture
that crisply. Diagnostics showed averaged word vectors suffer severe
anisotropy here (mean cross-tradition cosine 0.50 — everything looks
alike), while LSA cosines are well-spread (mean 0.01, p99 0.34).

Fully offline and deterministic: no model downloads, random_state fixed.
Output: data/embeddings.npz (float32, one row per unit in units.csv order).
"""
from pathlib import Path

import json
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

DATA = Path(__file__).resolve().parent.parent / "data"


def main():
    df = pd.read_csv(DATA / "units.csv")
    texts = df["text"].tolist()
    print(f"{len(df)} sentences to embed")
    vec = TfidfVectorizer(max_features=12000, ngram_range=(1, 2),
                          stop_words="english", min_df=2)
    X = vec.fit_transform(texts)
    print(f"tfidf: {X.shape}")
    emb = normalize(TruncatedSVD(n_components=256, random_state=42
                                 ).fit_transform(X)).astype(np.float32)
    np.savez_compressed(DATA / "embeddings.npz", embeddings=emb,
                        unit_ids=df["unit_id"].to_numpy())
    print(f"wrote data/embeddings.npz: {emb.shape}")
    # save per-term idf so 04 can require lexically substantive overlaps
    # (shared rare words, not shared function-ish words) when mining pairs
    idf = {t: float(v) for t, v in zip(vec.get_feature_names_out(), vec.idf_)}
    (DATA / "tfidf_idf.json").write_text(json.dumps(idf))
    print(f"wrote data/tfidf_idf.json: {len(idf)} terms")


if __name__ == "__main__":
    main()
