# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Branching & Release Strategy

- `main` — always deployable; CI runs on every push and PR
- `feature/*` — short-lived feature branches; merge via PR to main
- `feature/ai-gen-{ticket_id}` — AI-generated test code branches; require human review before merge
- `hotfix/*` — emergency fixes branched from main; merge back to main immediately
- Tags use semver: `v{major}.{minor}.{patch}` — cut on significant milestones

---

## [Unreleased]

### Fixed
- Sprint 1 audit fixes: CI triggers, fixture scoping, type annotations, HMAC digestmod, telegram settings
- Sprint 2 audit fixes: folder structure, env templates, pip-audit CI step

---

## [0.9.0] — 2026-05-21

### Added
- Phase 9 pipeline: test plan agent, skill gap agent, test case export (Excel/CSV)
- Telegram approval workflow with confidence-based auto-approve/reject
- RAG knowledge base (ChromaDB) for context injection
- GitHub MCP bridge + Figma MCP bridge
- POMRegistry `validate_step()` and `export_schema()` methods
- Production safety validator: blocks `playwright_ignore_https_errors=True` in production

### Changed
- Gherkin .feature files: removed all hardcoded `/v1/` URLs — behavior-driven language only
- CI pipeline: added `push:` and `pull_request:` triggers (previously schedule + manual only)
- Auth fixture scope: `module` → `function` in posts/auth/privacy/network conftest files
- `approval_workflow/` moved to `integrations/approval_workflow/`
- `ci_cd/` moved to `scripts/ci_cd/`
- Staging URL defaults removed from `config/settings.py` (now required env vars)

### Security
- HMAC `digestmod` set as keyword argument (defensive coding)
- Webhook server startup guards: fails fast on missing required env vars
- AST pre-flight validation for all LLM-generated code before writing to disk
- Path traversal guard in pipeline execute node

### Deprecated
- `skills/assertions/api_assertions.py` — use `skills/api/schema_validator.py`
- `skills/base/` — use POM/Screen Object methods directly

---

## [0.8.0] — 2026-04-15

### Added
- LangGraph Phase 8 pipeline with LangGraph 0.2.x StateGraph
- Jira webhook server with HMAC-SHA256, replay protection, deduplication
- `core/code_security.py` — AST validation for LLM-generated code
- `core/input_sanitizer.py` — prompt injection prevention
- CircuitBreaker for LLM calls

### Fixed
- Prompt injection vulnerability (C1)
- Webhook HMAC validation fail-closed (C2)
- Credential guards in all agent entry points (C3)
- Path traversal in code generator (C4)
