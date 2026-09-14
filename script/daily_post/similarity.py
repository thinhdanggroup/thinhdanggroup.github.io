#!/usr/bin/env python3
"""TF-IDF cosine similarity, standard library only.

scikit-learn and numpy are installed but broken on the target machine
(`ImportError: numpy.core.multiarray failed to import`), so this is hand-rolled.
The corpus is ~150 short documents, which is far too small for the dependency to
have earned its place anyway.
"""
from __future__ import annotations

import math
import re
from collections import Counter

WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens of two characters or more.

    Single characters carry no topical signal and inflate the vocabulary.
    """
    return [t for t in WORD_RE.findall(text.lower()) if len(t) > 1]


def tfidf_vectors(docs: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """Vectorise a corpus, returning the vectors and the IDF map that built them.

    The IDF map is returned so a later candidate can be projected into the same
    space with `vector_for` instead of re-vectorising the whole corpus.
    """
    tokenized = [tokenize(d) for d in docs]
    n = len(tokenized) or 1

    df: Counter[str] = Counter()
    for tokens in tokenized:
        df.update(set(tokens))

    # Smoothed IDF: +1 inside the log keeps a term present in every document at a
    # small positive weight rather than exactly zero, so a candidate made entirely
    # of common terms still scores above the floor.
    idf = {term: math.log((1 + n) / (1 + count)) + 1.0 for term, count in df.items()}

    return [_vector(tokens, idf) for tokens in tokenized], idf


def vector_for(text: str, idf: dict[str, float]) -> dict[str, float]:
    """Project one document into an existing IDF space. Unknown terms are dropped."""
    return _vector(tokenize(text), idf)


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {
        term: (count / total) * idf[term]
        for term, count in counts.items()
        if term in idf
    }


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity of two sparse vectors. Empty vectors score 0.0."""
    if not a or not b:
        return 0.0
    shared = a.keys() & b.keys()
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
