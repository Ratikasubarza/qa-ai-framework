"""
RAG Engine — ChromaDB-backed retrieval for grounding agent context.
Sources: bug history, test history, requirements, codebase snippets.

Embedding model is pinned to sentence-transformers/all-MiniLM-L6-v2 v1.0.
Increment EMBEDDING_MODEL_VERSION when changing the model so existing
embeddings can be identified as semantically incompatible with new ones.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import structlog
from chromadb.utils import embedding_functions

import chromadb
from config.settings import settings
from core.source_intake.security import redact_internal_text

logger = structlog.get_logger(__name__)

# ── Pinned embedding model ────────────────────────────────────────────────────
# Change the version string here whenever the model is swapped. Existing
# collections built with a previous version must be re-indexed to avoid
# silent semantic drift between stored and query embeddings.
EMBEDDING_MODEL_NAME    = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_VERSION = "v1.0"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME,
)


class RAGEngine:
    def __init__(self) -> None:
        persist_dir = settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self._collections: dict[str, chromadb.Collection] = {}
        logger.info(
            "rag_engine_ready",
            persist_dir=persist_dir,
            embedding_model=EMBEDDING_MODEL_NAME,
            embedding_version=EMBEDDING_MODEL_VERSION,
        )

    def _get_collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=_embedding_fn,
                metadata={
                    "hnsw:space":             "cosine",
                    "embedding_model":        EMBEDDING_MODEL_NAME,
                    "embedding_model_version": EMBEDDING_MODEL_VERSION,
                },
            )
        return self._collections[name]

    def _enrich_metadata(self, metadata: dict, content: str) -> dict:
        """Attach embedding provenance + content fingerprint to every document."""
        return {
            **metadata,
            "embedding_model":         EMBEDDING_MODEL_NAME,
            "embedding_model_version": EMBEDDING_MODEL_VERSION,
            "chunk_id":                hashlib.sha256(content.encode()).hexdigest()[:16],
        }

    def index(
        self,
        documents:  list[str],
        ids:        list[str],
        metadatas:  list[dict],
        collection: str = "knowledge_base",
    ) -> None:
        """Redact then index documents into the vector store with enriched metadata."""
        col = self._get_collection(collection)
        safe_documents: list[str] = []
        safe_metadatas: list[dict] = []

        for document, metadata in zip(documents, metadatas):
            redaction = redact_internal_text(document)
            safe_doc  = redaction.text
            safe_meta = {
                key: (
                    redact_internal_text(value).text
                    if isinstance(value, str)
                    else value
                )
                for key, value in metadata.items()
            }
            if redaction.redactions:
                safe_meta["redactions_applied"] = ",".join(sorted(set(redaction.redactions)))

            enriched = self._enrich_metadata(safe_meta, safe_doc)
            safe_documents.append(safe_doc)
            safe_metadatas.append(enriched)

        col.upsert(
            documents=safe_documents,
            ids=ids,
            metadatas=safe_metadatas,
        )
        logger.info("rag_indexed", collection=collection, count=len(safe_documents))

    def retrieve(
        self,
        query:      str,
        collection: str           = "knowledge_base",
        top_k:      int           = 5,
        where:      Optional[dict] = None,
    ) -> str:
        """
        Retrieve top-k relevant documents for a query.
        Returns a formatted context string ready for LLM prompt injection.
        """
        col   = self._get_collection(collection)
        count = col.count()
        if count == 0:
            logger.debug("rag_empty_collection", collection=collection)
            return "No past context available."

        results = col.query(
            query_texts=[query],
            n_results=min(top_k, count),
            where=where,
        )

        docs  = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return "No relevant context found."

        formatted: list[str] = []
        for i, (doc, meta) in enumerate(zip(docs, metas), 1):
            source  = meta.get("source", "unknown")
            version = meta.get("embedding_model_version", "unknown")
            formatted.append(f"[{i}] Source: {source} (emb:{version})\n{doc}")

        context    = "\n\n---\n\n".join(formatted)
        safe_query = redact_internal_text(query[:50]).text
        logger.debug("rag_retrieved", query=safe_query, results=len(docs), collection=collection)
        return context

    def add_bug_history(self, bug_id: str, title: str, description: str, feature: str) -> None:
        self.index(
            documents=[f"Bug: {title}\n{description}"],
            ids=[f"bug_{bug_id}"],
            metadatas=[{"source": f"bug/{bug_id}", "feature": feature, "type": "bug"}],
            collection="knowledge_base",
        )

    def add_test_history(self, test_id: str, name: str, content: str, feature: str) -> None:
        self.index(
            documents=[f"Test Case: {name}\n{content}"],
            ids=[f"test_{test_id}"],
            metadatas=[{"source": f"test/{test_id}", "feature": feature, "type": "test"}],
            collection="knowledge_base",
        )


rag_engine = RAGEngine()
