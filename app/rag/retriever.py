"""
Session-scoped hybrid RAG store.

Features:
- FAISS cosine similarity (vector search)
- BM25 keyword search
- Hybrid score fusion with min-score threshold
- Full RetrievalScore preservation per chunk
- OCR extraction method tracking
- Session TTL cleanup
"""

import time
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

from app.utils.config import logger, MIN_HYBRID_SCORE, SESSION_TTL_SECONDS
from app.models.schemas import RetrievalScore, RetrievedChunk, ChunkMetadata

# ── Embedding model (singleton) ───────────────────────────────────────────────
_embedding_model: Optional[SentenceTransformer] = None

def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading SentenceTransformer 'all-MiniLM-L6-v2'...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer loaded.")
    return _embedding_model


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping character-level chunks."""
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size - overlap
    return chunks


class SessionRAGStore:
    """Per-session transient vector + keyword store with full score tracking."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at: float = time.time()
        self.last_accessed: float = time.time()

        self.chunks: List[Dict[str, Any]] = []          # raw chunk dicts
        self.embeddings: List[np.ndarray] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self.bm25: Optional[BM25Okapi] = None

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def add_document(
        self,
        source_name: str,
        content: str,
        source_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        extraction_method: str = "DIRECT",
    ) -> None:
        raw_chunks = chunk_text(content)
        if not raw_chunks:
            logger.warning(f"No text for '{source_name}'. Skipping ingestion.")
            return

        model = get_embedding_model()
        logger.info(f"Chunking '{source_name}' → {len(raw_chunks)} chunks. Embedding...")
        embeddings_batch = model.encode(raw_chunks, show_progress_bar=False)

        base_meta = metadata.copy() if metadata else {}
        base_meta.update({
            "source_name": source_name,
            "source_type": source_type,
            "extraction_method": extraction_method,
        })

        for i, (text, emb) in enumerate(zip(raw_chunks, embeddings_batch)):
            chunk_id = f"{self.session_id}_{source_name}_{len(self.chunks) + i}"
            meta = {**base_meta, "chunk_index": i}
            self.chunks.append({"chunk_id": chunk_id, "content": text, "metadata": meta})
            self.embeddings.append(emb)

        self._rebuild_indices()
        logger.info(f"Store '{self.session_id}': {len(self.chunks)} total chunks.")

    def _rebuild_indices(self) -> None:
        embs_np = np.vstack(self.embeddings).astype("float32")
        faiss.normalize_L2(embs_np)
        self.index = faiss.IndexFlatIP(embs_np.shape[1])
        self.index.add(embs_np)
        tokenized = [c["content"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = MIN_HYBRID_SCORE,
    ) -> List[RetrievedChunk]:
        """
        Hybrid FAISS + BM25 search.
        Returns RetrievedChunk objects with full score breakdown.
        Filters out chunks below min_score.
        """
        self.last_accessed = time.time()

        if not self.chunks or self.index is None or self.bm25 is None:
            logger.warning(f"Search on empty store for session '{self.session_id}'.")
            return []

        search_k = min(len(self.chunks), top_k * 4)

        # ── Vector search ─────────────────────────────────────────────────────
        model = get_embedding_model()
        q_emb = model.encode([query]).astype("float32")
        faiss.normalize_L2(q_emb)
        distances, indices = self.index.search(q_emb, search_k)

        vector_raw: Dict[int, float] = {}
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                vector_raw[int(idx)] = float(dist)

        # ── BM25 search ───────────────────────────────────────────────────────
        bm25_scores_arr = self.bm25.get_scores(query.lower().split())
        top_bm25 = np.argsort(bm25_scores_arr)[-search_k:][::-1]
        bm25_raw: Dict[int, float] = {int(i): float(bm25_scores_arr[i]) for i in top_bm25}

        # ── Normalize ─────────────────────────────────────────────────────────
        def _norm(d: Dict[int, float]) -> Dict[int, float]:
            if not d:
                return d
            lo, hi = min(d.values()), max(d.values())
            if hi == lo:
                return {k: 0.5 for k in d}
            return {k: (v - lo) / (hi - lo) for k, v in d.items()}

        v_norm = _norm(vector_raw)
        b_norm = _norm(bm25_raw)

        all_idx = set(v_norm) | set(b_norm)
        results: List[RetrievedChunk] = []

        for idx in all_idx:
            v = v_norm.get(idx, 0.0)
            b = b_norm.get(idx, 0.0)
            hybrid = 0.5 * v + 0.5 * b

            if hybrid < min_score:
                continue

            chunk = self.chunks[idx]
            meta_raw = chunk["metadata"]

            scores = RetrievalScore(
                vector_score=round(v, 4),
                bm25_score=round(b, 4),
                hybrid_score=round(hybrid, 4),
            )
            chunk_meta = ChunkMetadata(
                source_name=meta_raw.get("source_name", "Unknown"),
                source_type=meta_raw.get("source_type", "document"),
                chunk_index=meta_raw.get("chunk_index", 0),
                page=meta_raw.get("page"),
                url=meta_raw.get("url"),
                file_path=meta_raw.get("file_path"),
                extraction_method=meta_raw.get("extraction_method", "DIRECT"),
            )
            results.append(
                RetrievedChunk(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["content"],
                    retrieval_rank=0,  # assigned after sort
                    metadata=chunk_meta,
                    scores=scores,
                )
            )

        results.sort(key=lambda c: c.scores.hybrid_score, reverse=True)
        for rank, chunk in enumerate(results[:top_k], start=1):
            chunk.retrieval_rank = rank

        return results[:top_k]

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        return (time.time() - self.last_accessed) > SESSION_TTL_SECONDS

    def clear(self) -> None:
        self.chunks.clear()
        self.embeddings.clear()
        self.index = None
        self.bm25 = None
        logger.info(f"SessionRAGStore '{self.session_id}' cleared.")


# ── Global session registry ───────────────────────────────────────────────────
session_stores: Dict[str, SessionRAGStore] = {}


def get_session_store(session_id: str) -> SessionRAGStore:
    if session_id not in session_stores:
        logger.info(f"Creating SessionRAGStore for '{session_id}'.")
        session_stores[session_id] = SessionRAGStore(session_id)
    return session_stores[session_id]


def delete_session_store(session_id: str) -> None:
    if session_id in session_stores:
        session_stores[session_id].clear()
        del session_stores[session_id]
        logger.info(f"SessionRAGStore '{session_id}' deleted.")


def cleanup_expired_sessions() -> int:
    """Remove all sessions that have exceeded SESSION_TTL_SECONDS. Returns count removed."""
    expired = [sid for sid, store in session_stores.items() if store.is_expired()]
    for sid in expired:
        delete_session_store(sid)
    if expired:
        logger.info(f"Session cleanup: removed {len(expired)} expired stores.")
    return len(expired)
