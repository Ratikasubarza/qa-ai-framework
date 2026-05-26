"""
RAG Indexer — reads source files and indexes them into the vector store.

Source directories (add documents here to enrich agent context):
  knowledge_base/sources/requirements/  — product requirements (.md, .txt)
  knowledge_base/sources/bug_history/   — past bug reports (.md, .json)
  knowledge_base/sources/test_history/  — past test execution results (.md, .json)

Run manually:
  python -m knowledge_base.indexer

Run in CI to refresh after adding new source documents.
"""
import json
import hashlib
import structlog
from pathlib import Path
from knowledge_base.rag_engine import rag_engine

logger = structlog.get_logger(__name__)

SOURCES_DIR = Path(__file__).parent / "sources"

# Each source maps to a collection name and document type tag
SOURCE_CONFIGS: dict[str, dict] = {
    "requirements": {
        "collection": "knowledge_base",
        "doc_type":   "requirement",
        "extensions": {".md", ".txt"},
    },
    "bug_history": {
        "collection": "knowledge_base",
        "doc_type":   "bug",
        "extensions": {".md", ".json"},
    },
    "test_history": {
        "collection": "knowledge_base",
        "doc_type":   "test",
        "extensions": {".md", ".json"},
    },
}


_CHUNK_SIZE    = 1500   # chars per chunk
_CHUNK_OVERLAP = 200    # overlap between adjacent chunks


def _stable_id(path: Path, content: str) -> str:
    """Deterministic doc ID: filename stem + first 8 chars of content MD5."""
    slug = path.stem.replace(" ", "_").lower()
    digest = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"{slug}_{digest}"


def _chunk_text(text: str) -> list[str]:
    """
    Sliding-window chunker for large documents.
    Returns a single-element list when text fits within _CHUNK_SIZE.
    Splits on paragraph boundaries when possible to avoid mid-sentence cuts.
    """
    if len(text) <= _CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to break at the last paragraph boundary (\n\n) within the window
        boundary = text.rfind("\n\n", start, end)
        if boundary == -1 or boundary <= start:
            # Fall back to last newline, then last space
            boundary = text.rfind("\n", start, end)
        if boundary == -1 or boundary <= start:
            boundary = text.rfind(" ", start, end)
        if boundary == -1 or boundary <= start:
            boundary = end  # hard split as last resort

        chunks.append(text[start:boundary].strip())
        start = boundary - _CHUNK_OVERLAP if boundary - _CHUNK_OVERLAP > start else boundary
    return [c for c in chunks if c]


def _read_file(path: Path) -> str:
    """Read a file, converting JSON to a readable string."""
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return "\n\n".join(json.dumps(item, indent=2) for item in data)
        return json.dumps(data, indent=2)
    return path.read_text(encoding="utf-8")


def index_source(source_name: str) -> int:
    """
    Index all supported files in one source directory.
    Returns the number of documents indexed (0 if dir missing or empty).
    """
    cfg = SOURCE_CONFIGS.get(source_name)
    if not cfg:
        logger.warning("indexer_unknown_source", source=source_name)
        return 0

    source_dir = SOURCES_DIR / source_name
    if not source_dir.exists():
        logger.warning("indexer_source_dir_missing", path=str(source_dir))
        return 0

    documents: list[str] = []
    ids:       list[str] = []
    metadatas: list[dict] = []

    for path in sorted(source_dir.iterdir()):
        if path.suffix not in cfg["extensions"]:
            continue
        try:
            content = _read_file(path).strip()
            if not content:
                continue
            chunks = _chunk_text(content)
            base_id = _stable_id(path, content)
            for i, chunk in enumerate(chunks):
                chunk_id = base_id if len(chunks) == 1 else f"{base_id}_c{i}"
                documents.append(chunk)
                ids.append(chunk_id)
                meta: dict = {
                    "source":  f"{source_name}/{path.name}",
                    "feature": path.stem,
                    "type":    cfg["doc_type"],
                }
                if len(chunks) > 1:
                    meta["chunk_index"] = i
                    meta["total_chunks"] = len(chunks)
                    meta["parent_id"]    = base_id
                metadatas.append(meta)
        except Exception as e:
            logger.error("indexer_file_error", path=str(path), error=str(e))

    if documents:
        rag_engine.index(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
            collection=cfg["collection"],
        )

    logger.info("source_indexed", source=source_name, count=len(documents))
    return len(documents)


def index_all() -> dict[str, int]:
    """
    Index every configured source directory.
    Returns {source_name: doc_count} report.
    """
    report: dict[str, int] = {}
    for source_name in SOURCE_CONFIGS:
        report[source_name] = index_source(source_name)
    total = sum(report.values())
    logger.info("index_all_complete", total=total, by_source=report)
    return report


if __name__ == "__main__":
    report = index_all()
    print("\nRAG Indexing complete:")
    for source, count in report.items():
        status = "✅" if count > 0 else "⚠️  (0 files — add documents to knowledge_base/sources/)"
        print(f"  {status} {source}: {count} document(s)")
    print(f"\n  Total indexed: {sum(report.values())} document(s)")
