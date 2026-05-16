"""
RAG Quality Evaluator — measures retrieval precision and recall.

Runs against known query → expected_source pairs.
Use this to gate changes to embedding config, chunking strategy,
or vector store content (adding/removing documents).

Run: python -m knowledge_base.rag_quality_evaluator
CI command: pytest knowledge_base/rag_quality_evaluator.py -v
"""
import structlog
import pytest
from dataclasses import dataclass

from knowledge_base.rag_engine import rag_engine

logger = structlog.get_logger(__name__)

THRESHOLD_PRECISION = 0.70   # ≥70% returned docs must be relevant
THRESHOLD_RECALL    = 0.60   # ≥60% expected sources must be returned

# Known query → expected source fragment pairs.
# Add more as knowledge_base grows.
EVAL_QUERIES: list[dict] = [
    {
        "id":               "login_auth",
        "query":            "user login authentication credentials",
        "expected_sources": ["requirements/hono_app_requirements"],
        "collection":       "knowledge_base",
        "top_k":            5,
    },
    {
        "id":               "registration_flow",
        "query":            "user registration email verification phone",
        "expected_sources": ["requirements/hono_app_requirements"],
        "collection":       "knowledge_base",
        "top_k":            5,
    },
    {
        "id":               "password_security",
        "query":            "change password current new password security",
        "expected_sources": ["requirements/hono_app_requirements"],
        "collection":       "knowledge_base",
        "top_k":            5,
    },
    {
        "id":               "bug_login_401",
        "query":            "401 unauthorized login blocked regression",
        "expected_sources": ["bug_history/known_bugs"],
        "collection":       "knowledge_base",
        "top_k":            5,
    },
]


@dataclass
class RetrievalResult:
    query_id:  str
    query:     str
    returned:  list[str]   # source paths returned by retriever
    expected:  list[str]   # expected source fragments
    precision: float
    recall:    float
    passed:    bool
    notes:     str = ""


def _precision(returned: list[str], expected: list[str]) -> float:
    if not returned:
        return 0.0
    relevant = sum(1 for r in returned if any(e in r for e in expected))
    return relevant / len(returned)


def _recall(returned: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    found = sum(1 for e in expected if any(e in r for r in returned))
    return found / len(expected)


def evaluate_query(eval_case: dict) -> RetrievalResult:
    query      = eval_case["query"]
    expected   = eval_case["expected_sources"]
    collection = eval_case.get("collection", "knowledge_base")
    top_k      = eval_case.get("top_k", 5)

    col = rag_engine._get_collection(collection)
    if col.count() == 0:
        return RetrievalResult(
            query_id=eval_case.get("id", "?"),
            query=query,
            returned=[],
            expected=expected,
            precision=0.0,
            recall=0.0,
            passed=False,
            notes="Collection empty — run: python -m knowledge_base.indexer",
        )

    raw      = col.query(query_texts=[query], n_results=min(top_k, col.count()))
    metas    = raw.get("metadatas", [[]])[0]
    returned = [m.get("source", "") for m in metas]

    prec   = _precision(returned, expected)
    rec    = _recall(returned, expected)
    passed = prec >= THRESHOLD_PRECISION and rec >= THRESHOLD_RECALL

    result = RetrievalResult(
        query_id=eval_case.get("id", "?"),
        query=query,
        returned=returned,
        expected=expected,
        precision=round(prec, 2),
        recall=round(rec, 2),
        passed=passed,
        notes=(
            f"P={prec:.0%} R={rec:.0%} "
            f"(thresholds: P≥{THRESHOLD_PRECISION:.0%} R≥{THRESHOLD_RECALL:.0%})"
        ),
    )
    logger.info(
        "rag_eval_query",
        query_id=result.query_id,
        precision=result.precision,
        recall=result.recall,
        passed=result.passed,
    )
    return result


def evaluate_all() -> list[RetrievalResult]:
    results = []
    for case in EVAL_QUERIES:
        results.append(evaluate_query(case))
    passed  = sum(1 for r in results if r.passed)
    logger.info("rag_eval_complete", total=len(results), passed=passed)
    return results


# ── pytest entry point ───────────────────────────────────────────────────────

@pytest.mark.skip(reason="Requires indexed knowledge_base — run indexer first")
def test_rag_retrieval_quality():
    """
    Gate: RAG precision and recall must meet thresholds.
    Remove the skip mark once sources are indexed.
    """
    results = evaluate_all()
    failed  = [r for r in results if not r.passed]
    assert not failed, (
        f"{len(failed)}/{len(results)} RAG queries below threshold:\n"
        + "\n".join(f"  [{r.query_id}] {r.notes}" for r in failed)
    )


if __name__ == "__main__":
    results = evaluate_all()
    print("\nRAG Quality Evaluation:")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.query_id}: P={r.precision:.0%} R={r.recall:.0%}")
        if not r.passed:
            print(f"         returned: {r.returned}")
            print(f"         expected: {r.expected}")
    overall = sum(1 for r in results if r.passed)
    print(f"\n  Overall: {overall}/{len(results)} queries passing")
