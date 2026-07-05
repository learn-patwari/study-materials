"""
rag.py
======
Lightweight semantic search over the resume corpus (the "RAG search tool"
referenced in Milestone 2 of the assignment).

We use TF-IDF + cosine similarity. If scikit-learn is available we use it;
otherwise we fall back to a small pure-Python TF-IDF implementation so the
system runs with **zero** extra dependencies. Either way the public API is:

    index = ResumeIndex(candidates)
    hits = index.search("react typescript 3 years", k=10)
    # -> [{"id": "C003", "score": 0.71, "candidate": {...}}, ...]
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List

from data_store import render_resume

_TOKEN_RE = re.compile(r"[a-z0-9\+\#\.]+")


def _tokenize(text: str) -> List[str]:
    text = text.lower().replace("c++", "cpp").replace("c#", "csharp")
    return _TOKEN_RE.findall(text)


try:  # Prefer scikit-learn if installed.
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    _HAVE_SKLEARN = True
except Exception:  # pragma: no cover - exercised only without sklearn
    _HAVE_SKLEARN = False


class ResumeIndex:
    """A searchable index over candidate resumes."""

    def __init__(self, candidates: List[Dict[str, Any]]):
        self.candidates = candidates
        self.by_id = {c["id"]: c for c in candidates}
        self._docs = [self._doc_text(c) for c in candidates]
        if _HAVE_SKLEARN:
            self._vectorizer = TfidfVectorizer(
                tokenizer=_tokenize, preprocessor=lambda x: x, token_pattern=None
            )
            self._matrix = self._vectorizer.fit_transform(self._docs)
        else:
            self._build_pure_python()

    # -- document text ----------------------------------------------------
    @staticmethod
    def _doc_text(candidate: Dict[str, Any]) -> str:
        # Weight skills by repeating them so exact-skill matches rank strongly.
        skills = " ".join(candidate["skills"])
        return f"{render_resume(candidate)} {skills} {skills}"

    # -- pure-python TF-IDF fallback -------------------------------------
    def _build_pure_python(self) -> None:
        self._tf: List[Counter] = []
        df: Counter = Counter()
        for doc in self._docs:
            toks = _tokenize(doc)
            counts = Counter(toks)
            self._tf.append(counts)
            for term in counts:
                df[term] += 1
        n = len(self._docs)
        self._idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        self._vecs = [self._to_vec(tf) for tf in self._tf]
        self._norms = [math.sqrt(sum(v * v for v in vec.values())) or 1.0
                       for vec in self._vecs]

    def _to_vec(self, tf: Counter) -> Dict[str, float]:
        total = sum(tf.values()) or 1
        return {t: (c / total) * self._idf.get(t, 0.0) for t, c in tf.items()}

    # -- search -----------------------------------------------------------
    def search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        if _HAVE_SKLEARN:
            qv = self._vectorizer.transform([query])
            sims = cosine_similarity(qv, self._matrix)[0]
            scored = list(zip(range(len(self.candidates)), sims))
        else:
            qvec = self._to_vec(Counter(_tokenize(query)))
            qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
            scored = []
            for i, vec in enumerate(self._vecs):
                dot = sum(qvec.get(t, 0.0) * w for t, w in vec.items())
                scored.append((i, dot / (qnorm * self._norms[i])))
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for i, score in scored[:k]:
            c = self.candidates[i]
            results.append({"id": c["id"], "score": float(round(score, 4)),
                            "candidate": c})
        return results
