"""
resume_rag.py
=============
RAG system for resumes (Assignment 3, Part A).

Pipeline:
    load resumes (file-system tools)  ->  section-aware chunking
      ->  embeddings  ->  vector store (with metadata for filtering)

Everything runs **offline by default**: a pure-Python TF-IDF embedder and an
in-memory cosine vector store need no dependencies or API keys. If better
components are installed they are used automatically:

    embeddings : sentence-transformers  (HuggingFace)  ->  else TF-IDF
    vector DB  : chromadb                               ->  else in-memory + JSON

Public API:
    rag = ResumeRAG()
    rag.build_index("data/resumes")
    hits = rag.search("python backend django", k=10, where={"role": "backend"})
    cand = rag.candidates            # {cid: metadata}
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Skill vocabulary (shared by chunking metadata + the matcher)
# --------------------------------------------------------------------------
SKILL_VOCAB = [
    "Python", "Django", "Flask", "FastAPI", "PostgreSQL", "Redis", "REST APIs",
    "Docker", "Microservices", "RabbitMQ", "Kafka", "Spark", "Airflow", "dbt",
    "Snowflake", "ETL", "JavaScript", "TypeScript", "React", "Redux", "CSS",
    "HTML", "Next.js", "Jest", "Webpack", "Node.js", "pandas", "NumPy",
    "scikit-learn", "Statistics", "Matplotlib", "Jupyter", "A/B Testing",
    "PyTorch", "TensorFlow", "NLP", "MLflow", "Kubernetes", "Feature Engineering",
    "AWS", "Azure", "Terraform", "CI/CD", "Linux", "Ansible", "Prometheus",
    "Bash", "Kotlin", "Swift", "Android", "iOS", "Java", "Firebase",
    "Jetpack Compose", "Penetration Testing", "SIEM", "Networking",
    "Cryptography", "Incident Response", "OWASP", "Selenium", "Cypress",
    "Pytest", "API Testing", "TestRail", "Cost Optimization", "SQL",
]
_SKILL_LOWER = {s.lower(): s for s in SKILL_VOCAB}

SECTION_HEADERS = ["SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION", "CONTACT"]
_TOKEN_RE = re.compile(r"[a-z0-9\+\#\.]+")
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.I)


def _tokenize(text: str) -> List[str]:
    text = text.lower().replace("c++", "cpp").replace("c#", "csharp")
    return _TOKEN_RE.findall(text)


def find_skills(text: str) -> List[str]:
    """Return canonical skill names mentioned in text (order-preserving, unique)."""
    low = text.lower()
    found: List[str] = []
    for lower, canon in _SKILL_LOWER.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(lower)}(?![a-z0-9])", low):
            found.append(canon)
    return found


# ==========================================================================
# Embeddings (pluggable)
# ==========================================================================
class TfidfEmbedder:
    """Pure-Python TF-IDF embedder. Fit on the corpus, then embed any text."""

    name = "tfidf"

    def __init__(self) -> None:
        self.vocab: Dict[str, int] = {}
        self.idf: List[float] = []
        self.dim = 0
        self._fitted = False

    def fit(self, docs: List[str]) -> "TfidfEmbedder":
        df: Counter = Counter()
        tokd = [_tokenize(d) for d in docs]
        for toks in tokd:
            for term in set(toks):
                df[term] += 1
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n = len(docs)
        self.idf = [0.0] * len(self.vocab)
        for term, i in self.vocab.items():
            self.idf[i] = math.log((1 + n) / (1 + df[term])) + 1.0
        self.dim = len(self.vocab)
        self._fitted = True
        return self

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("TfidfEmbedder.fit() must be called first.")
        out = []
        for text in texts:
            toks = _tokenize(text)
            counts = Counter(toks)
            total = sum(counts.values()) or 1
            vec = [0.0] * self.dim
            for term, c in counts.items():
                i = self.vocab.get(term)
                if i is not None:
                    vec[i] = (c / total) * self.idf[i]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class SentenceTransformerEmbedder:
    """HuggingFace sentence-transformers embedder (used if installed)."""

    name = "sentence-transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def fit(self, docs: List[str]) -> "SentenceTransformerEmbedder":
        return self  # no corpus fitting needed

    def embed(self, texts: List[str]) -> List[List[float]]:
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]


def get_embedder(prefer: Optional[str] = None):
    """Return the best available embedder. ``prefer='tfidf'`` forces offline mode."""
    if prefer != "tfidf":
        try:
            return SentenceTransformerEmbedder()
        except Exception:
            pass
    return TfidfEmbedder()


# ==========================================================================
# Vector store (pluggable)
# ==========================================================================
def _cosine(a: List[float], b: List[float]) -> float:
    # vectors are L2-normalized upstream, so dot == cosine
    return sum(x * y for x, y in zip(a, b))


class InMemoryVectorStore:
    """Simple cosine-similarity store with JSON persistence."""

    name = "in-memory"

    def __init__(self) -> None:
        self.ids: List[str] = []
        self.embeddings: List[List[float]] = []
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

    def add(self, ids, embeddings, documents, metadatas) -> None:
        self.ids.extend(ids)
        self.embeddings.extend(embeddings)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)

    def query(self, embedding: List[float], k: int = 10,
              where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        scored = []
        for i, emb in enumerate(self.embeddings):
            meta = self.metadatas[i]
            if where and any(meta.get(kk) != vv for kk, vv in where.items()):
                continue
            scored.append((i, _cosine(embedding, emb)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"id": self.ids[i], "document": self.documents[i],
                 "metadata": self.metadatas[i], "score": float(s)}
                for i, s in scored[:k]]

    def count(self) -> int:
        return len(self.ids)

    def persist(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"ids": self.ids, "embeddings": self.embeddings,
                       "documents": self.documents, "metadatas": self.metadatas},
                      fh)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        self.ids, self.embeddings = d["ids"], d["embeddings"]
        self.documents, self.metadatas = d["documents"], d["metadatas"]


class ChromaVectorStore:
    """ChromaDB-backed store (used if the ``chromadb`` package is installed)."""

    name = "chromadb"

    def __init__(self, persist_dir: str, collection: str = "resumes") -> None:
        import chromadb  # type: ignore
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.col = self.client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"})

    def add(self, ids, embeddings, documents, metadatas) -> None:
        # chroma metadata values must be scalars — join lists.
        flat = [{k: (", ".join(v) if isinstance(v, list) else v)
                 for k, v in m.items()} for m in metadatas]
        self.col.add(ids=list(ids), embeddings=[list(e) for e in embeddings],
                     documents=list(documents), metadatas=flat)

    def query(self, embedding, k=10, where=None):
        res = self.col.query(query_embeddings=[list(embedding)], n_results=k,
                             where=where or None)
        out = []
        for i in range(len(res["ids"][0])):
            out.append({"id": res["ids"][0][i], "document": res["documents"][0][i],
                        "metadata": res["metadatas"][0][i],
                        "score": 1.0 - res["distances"][0][i]})
        return out

    def count(self) -> int:
        return self.col.count()

    def persist(self, path: str) -> None:
        pass  # chroma persists automatically

    def load(self, path: str) -> None:
        pass


def get_vector_store(persist_dir: str, backend: str = "auto"):
    if backend in ("auto", "chromadb"):
        try:
            return ChromaVectorStore(os.path.join(persist_dir, "chroma"))
        except Exception:
            if backend == "chromadb":
                raise
    return InMemoryVectorStore()


# ==========================================================================
# Document processing
# ==========================================================================
def load_resume(path: str) -> str:
    """Load a resume file (mirrors the Milestone-1 read_file tool)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if ext == ".pdf":
        from pypdf import PdfReader  # type: ignore
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    if ext == ".docx":
        import docx  # type: ignore
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    raise ValueError(f"Unsupported resume type: {ext}")


def split_sections(text: str) -> Dict[str, str]:
    """Split a resume into {section_name: body}, preserving section boundaries."""
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {"HEADER": []}
    current = "HEADER"
    for line in lines:
        stripped = line.strip()
        if stripped.upper() in SECTION_HEADERS:
            current = stripped.upper()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def extract_metadata(text: str, resume_path: str) -> Dict[str, Any]:
    """Extract Name, Title, Skills, Experience Years, Education."""
    sections = split_sections(text)
    header = sections.get("HEADER", "").splitlines()
    name = header[0].strip() if header else os.path.basename(resume_path)
    title = header[1].strip() if len(header) > 1 else ""

    skills = find_skills(sections.get("SKILLS", "") or text)
    ym = _YEARS_RE.search(sections.get("SUMMARY", "")) or _YEARS_RE.search(text)
    years = int(ym.group(1)) if ym else 0
    education = sections.get("EDUCATION", "").strip()

    # role guessed from the title (used for metadata filtering + eval labels)
    role = title.lower().replace(" ", "_") if title else ""
    return {"candidate_name": name, "title": title, "role_title": role,
            "skills": skills, "experience_years": years, "education": education,
            "resume_path": resume_path}


def chunk_resume(text: str) -> List[Dict[str, str]]:
    """Section-aware chunking: one chunk per resume section.

    Keeping each section intact (Summary / Skills / Experience / Education)
    means a query about 'education' retrieves the education chunk, and a
    skills query retrieves the skills chunk — cleaner than fixed-size windows.
    """
    sections = split_sections(text)
    chunks = []
    for name, body in sections.items():
        if name == "CONTACT":
            continue  # not useful for matching
        chunks.append({"section": name, "text": body})
    return chunks


# ==========================================================================
# ResumeRAG
# ==========================================================================
class ResumeRAG:
    def __init__(self, embedder=None, persist_dir: Optional[str] = None,
                 backend: str = "auto", prefer_embedder: Optional[str] = None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.persist_dir = persist_dir or os.path.join(here, ".rag_store")
        os.makedirs(self.persist_dir, exist_ok=True)
        self.embedder = embedder or get_embedder(prefer_embedder)
        self.backend = backend
        self.store = None
        self.candidates: Dict[str, Dict[str, Any]] = {}

    # -- build ------------------------------------------------------------
    def build_index(self, resume_dir: str) -> Dict[str, Any]:
        """Load, chunk, embed, and index every resume in a directory."""
        paths = [os.path.join(resume_dir, f) for f in sorted(os.listdir(resume_dir))
                 if os.path.splitext(f)[1].lower() in (".txt", ".md", ".pdf", ".docx")]

        chunk_ids, chunk_texts, chunk_metas = [], [], []
        for path in paths:
            text = load_resume(path)
            cid = os.path.splitext(os.path.basename(path))[0]
            meta = extract_metadata(text, path)
            self.candidates[cid] = {**meta, "candidate_id": cid}
            for ch in chunk_resume(text):
                chunk_ids.append(f"{cid}::{ch['section']}")
                chunk_texts.append(ch["text"])
                chunk_metas.append({
                    "candidate_id": cid,
                    "candidate_name": meta["candidate_name"],
                    "resume_path": path,
                    "section": ch["section"],
                    "role": meta["role_title"],
                    "experience_years": meta["experience_years"],
                    "skills": meta["skills"],
                })

        # Fit embedder on all chunk texts (TF-IDF needs the corpus; ST ignores it).
        self.embedder.fit(chunk_texts)
        embeddings = self.embedder.embed(chunk_texts)

        self.store = get_vector_store(self.persist_dir, self.backend)
        self.store.add(chunk_ids, embeddings, chunk_texts, chunk_metas)
        self._save_candidates()
        return {"resumes": len(paths), "chunks": len(chunk_ids),
                "embedder": self.embedder.name, "vector_store": self.store.name,
                "embedding_dim": getattr(self.embedder, "dim", None)}

    # -- search -----------------------------------------------------------
    def search(self, query: str, k: int = 10,
               where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.store is None:
            raise RuntimeError("Call build_index() first.")
        qvec = self.embedder.embed([query])[0]
        return self.store.query(qvec, k=k, where=where)

    # -- persistence ------------------------------------------------------
    def _save_candidates(self) -> None:
        with open(os.path.join(self.persist_dir, "candidates.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(self.candidates, fh, indent=2)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    rag = ResumeRAG()
    stats = rag.build_index(os.path.join(here, "data", "resumes"))
    print("Index built:", json.dumps(stats, indent=2))
    print("\nTop 5 for 'python django backend api':")
    for h in rag.search("python django backend api", k=5):
        print(f"  {h['score']:.3f}  {h['id']:35}  [{h['metadata']['section']}]")
