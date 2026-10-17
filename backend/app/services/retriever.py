"""
retriever.py – RAG retrieval service using ChromaDB + Sentence Transformers.
Indexes runbook Markdown files and retrieves the most relevant ones given
an incident description.
"""

from __future__ import annotations

import os
import glob
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from sentence_transformers import SentenceTransformer

from backend.app.config import get_settings

settings = get_settings()

_EMBED_MODEL = "all-MiniLM-L6-v2"   # ~90 MB, fast and accurate


class RunbookRetriever:
    """Embeds runbook documents and retrieves the top-k most relevant ones."""

    def __init__(self):
        self._client: chromadb.HttpClient | None = None
        self._collection = None
        self._embedder: SentenceTransformer | None = None

    def _ensure_init(self):
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
            self._embedder = SentenceTransformer(_EMBED_MODEL)
            logger.info(f"RunbookRetriever connected to ChromaDB at "
                        f"{settings.chroma_host}:{settings.chroma_port}")

    def index_runbooks(self, runbook_dir: str = "knowledge_base/sample_runbooks") -> int:
        """
        Scan *runbook_dir* for *.md files and upsert them into ChromaDB.
        Returns the number of documents indexed.
        """
        self._ensure_init()
        files = glob.glob(os.path.join(runbook_dir, "**", "*.md"), recursive=True)
        if not files:
            logger.warning(f"No runbook files found in {runbook_dir}")
            return 0

        documents, ids, metadatas = [], [], []
        for path in files:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            doc_id = os.path.relpath(path, runbook_dir).replace("\\", "/")
            documents.append(content)
            ids.append(doc_id)
            metadatas.append({"filename": os.path.basename(path), "path": path})

        embeddings = self._embedder.encode(documents, show_progress_bar=False).tolist()
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Indexed {len(documents)} runbooks into ChromaDB.")
        return len(documents)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the top-k most semantically similar runbooks for *query*.
        Returns list of dicts: { id, document, metadata, distance }
        """
        self._ensure_init()

        query_emb = self._embedder.encode([query], show_progress_bar=False).tolist()
        results = self._collection.query(
            query_embeddings=query_emb,
            n_results=min(top_k, self._collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "id":       doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return hits


# ── Module-level singleton ────────────────────────────────────────────────────
_retriever: RunbookRetriever | None = None


def get_retriever() -> RunbookRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RunbookRetriever()
    return _retriever
