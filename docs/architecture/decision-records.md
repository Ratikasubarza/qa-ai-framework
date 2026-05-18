# Architecture Decision Records

Lightweight ADR log for key decisions made during development.
Format: date | decision | context | alternatives considered | trade-offs

---

## ADR-001 — LangGraph for pipeline orchestration
**Date:** 2026-01
**Decision:** Use LangGraph StateGraph for multi-agent coordination.
**Context:** Need a reliable way to chain 10+ AI agents with conditional routing, retries, and state propagation between nodes.
**Alternatives:** Custom async task queue (asyncio); Celery; simple sequential functions.
**Trade-offs:** LangGraph adds a dependency but provides conditional edges, state typing, and easy graph visualization. Custom queue would be lighter but lacks typed state and conditional routing out of the box.

---

## ADR-002 — OpenRouter for LLM access (dev) → Claude (prod)
**Date:** 2026-01
**Decision:** Use OpenRouter free models during development. Switch to Claude production models via `MODEL_TIER=production` when framework is mature.
**Context:** Development phase requires fast iteration without API cost. Production needs reliability and quality.
**Alternatives:** Direct Anthropic API from day 1; Azure OpenAI; local models (Ollama).
**Trade-offs:** Free models have lower quality and more variability. Production Claude costs money but gives reliable structured output. The dual-tier design in `core/llm_client.py` allows zero-code switch.

---

## ADR-003 — File-backed pending approvals (not in-memory)
**Date:** 2026-02
**Decision:** Store pending Telegram approvals as JSON files at `reports/pending_approvals/{id}.json`.
**Context:** If the server restarts between a Telegram notification and the QA Lead's response, an in-memory store would lose the pending state.
**Alternatives:** Redis; SQLite; in-memory dict.
**Trade-offs:** File-backed is simple, survives restarts, and requires no extra infrastructure. Not suitable for multi-instance deployments (but this is a single-runner setup).

---

## ADR-004 — Confidence-based 3-tier approval gate
**Date:** 2026-02
**Decision:** Auto-approve at ≥85% confidence for regressions; async Telegram for 60–84%; auto-reject below 60%.
**Context:** Human approval on every pipeline run is a bottleneck. High-confidence regression runs need no human review.
**Alternatives:** Always require human approval; approve all automatically.
**Trade-offs:** Auto-approve misses edge cases if confidence score is incorrectly calculated. The safety lock: confidence = coverage_percentage / 100.0 from the reviewer agent. Reviewer uses scope-aware missing case classification to avoid inflating coverage.

---

## ADR-005 — skills/auth and skills/data as shared helpers
**Date:** 2026-05
**Decision:** Create `skills/auth/auth_helper.py` and `skills/data/data_generator.py` as the single source of truth for auth tokens and test data generation.
**Context:** Every feature test_data file was duplicating the same email/phone/timestamp generation logic and token retrieval patterns.
**Alternatives:** Keep generation inline in each test_data file; use fixtures.
**Trade-offs:** Centralizing creates a single failure point but eliminates 200+ lines of duplication. All boundary values reference `BoundaryValues` and `ReferenceIDs` from config — no hardcoded numbers.

---

## ADR-006 — Structured logging with structlog
**Date:** 2026-01
**Decision:** Use `structlog` throughout (not Python's built-in logging).
**Context:** Need machine-parseable logs for CI/CD monitoring and agent audit trail.
**Trade-offs:** Adds a dependency but provides JSON-structured events with consistent key names. Easier to grep in CI logs.

---

## ADR-007 — TDD as mandatory flow (not optional)
**Date:** 2026-01
**Decision:** Every new test must go through red → green → refactor. Gherkin written before test code.
**Context:** Without TDD discipline, tests were added that passed immediately without actually testing the feature (false positives).
**How enforced:** AGENTS.md mandates it. Pre-commit hooks catch syntax errors. CI gate validates markers are applied.

---

## ADR-008 — .env tracked in git (known issue)
**Date:** 2026-05
**Status:** OPEN — requires human action
**Issue:** `.env` was committed before `.gitignore` was properly configured. It remains tracked by git.
**Required fix:** `git rm --cached .env && git commit -m "chore: untrack .env from git history"`
**Risk:** If `.env` contains real secrets, those secrets are in git history. Rotate all credentials in `.env` after untracking.
**Mitigation in place:** pre-commit `detect-secrets` hook and `detect-private-key` hook prevent future accidental commits.
