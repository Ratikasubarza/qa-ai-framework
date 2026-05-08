"""
RAG Engine — ChromaDB-backed retrieval for grounding agent context.
Sources: bug history, test history, requirements, codebase snippets.
"""
import chromadb
import structlog
from pathlib import Path
from typing import Optional
from config.settings import settings

logger = structlog.get_logger(__name__)


class RAGEngine:
    def __init__(self):
        persist_dir = settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self._collections = {}
        logger.info("rag_engine_ready", persist_dir=persist_dir)

    def _get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def index(
        self,
        documents:   list[str],
        ids:         list[str],
        metadatas:   list[dict],
        collection:  str = "knowledge_base",
    ):
        """Index documents into the vector store."""
        col = self._get_collection(collection)
        col.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
        logger.info(
            "rag_indexed",
            collection=collection,
            count=len(documents),
        )

    def retrieve(
        self,
        query:      str,
        collection: str  = "knowledge_base",
        top_k:      int  = 5,
        where:      Optional[dict] = None,
    ) -> str:
        """
        Retrieve top-k relevant documents for a query.
        Returns formatted context string ready for LLM injection.
        """
        col = self._get_collection(collection)
        count = col.count()
        if count == 0:
            logger.debug("rag_empty_collection", collection=collection)
            return "No past context available."

        results = col.query(
            query_texts=[query],
            n_results=min(top_k, count),
            where=where,
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return "No relevant context found."

        formatted = []
        for i, (doc, meta) in enumerate(zip(docs, metas), 1):
            source = meta.get("source", "unknown")
            formatted.append(f"[{i}] Source: {source}\n{doc}")

        context = "\n\n---\n\n".join(formatted)
        logger.debug("rag_retrieved", query=query[:50], results=len(docs))
        return context

    def add_bug_history(self, bug_id: str, title: str, description: str, feature: str):
        """Convenience method for indexing bug reports."""
        self.index(
            documents=[f"Bug: {title}\n{description}"],
            ids=[f"bug_{bug_id}"],
            metadatas=[{"source": f"bug/{bug_id}", "feature": feature, "type": "bug"}],
            collection="knowledge_base",
        )

    def add_test_history(self, test_id: str, name: str, content: str, feature: str):
        """Convenience method for indexing past test cases."""
        self.index(
            documents=[f"Test Case: {name}\n{content}"],
            ids=[f"test_{test_id}"],
            metadatas=[{"source": f"test/{test_id}", "feature": feature, "type": "test"}],
            collection="knowledge_base",
        )


rag_engine = RAGEngine()
