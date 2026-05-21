# QA AI Framework Maturity Plan

Last updated: 2026-05-20

This document captures the Phase 1 audit and the first incremental governance changes. It is intentionally migration-friendly: existing tests should keep running while new tests and generated code move toward the blessed patterns.

## Architecture Summary

The framework already has the right major building blocks: feature-based tests, typed agent contracts, a LangGraph-style pipeline, automation readiness checks, source intake redaction, API/web/mobile platform layers, and RAG storage.

The first maturity slice tightens boundaries without adding or removing agents:

- Automation runtime code uses `config.test_config.TestConfig`, `APIEndpoints`, and `Timeouts`.
- Service/orchestrator code continues to use `config.settings.settings` for LLM, Jira, Confluence, Telegram, GitHub, approval, and RAG settings.
- `HonoAPIClient` is the blessed API-test client surface for auth, request-level headers, no-api-key negative tests, consistent timeouts, and safe status assertions.
- RAG indexing redacts documents and string metadata before storage.
- Jira webhooks now fail closed when unsigned unless local unsigned mode is explicitly enabled.
- Orchestrator code generation now iterates every requested platform instead of silently using only the first platform.

## Audit Findings

Config structure:

- `TestConfig` owns automation runtime values, but `config.settings` also contained Hono URLs and credentials.
- Some tests and helpers still call `os.getenv` directly.
- `platforms/web/playwright_driver.py` had hardcoded staging URLs.

API client usage:

- API tests mostly use `HonoAPIClient`, but many mutate `client._client.headers`.
- Some helpers and explicit negative tests use raw `httpx.AsyncClient`.
- The client previously used service settings instead of automation runtime config.

Test data structure:

- There is a reusable `PayloadBuilder`, but feature tests still mix static classes, direct dictionaries, random suffixes, and DB helpers.
- Reference IDs currently live in `TestConfig.ReferenceIDs`; new code should move toward reference modules.

Locator/POM structure:

- Login has page/screen objects and feature locators.
- Several mobile tests still contain raw Appium locators, sleeps, coordinate taps, and ADB commands.
- Existing self-healing storage is history-based, but locator changes should remain recommendation-first.

Agent responsibility boundaries:

- Agent contracts exist in `core/agent_contracts.py`.
- Source intake already normalizes Jira/Confluence/manual context and redacts text.
- Some integration surfaces can still create comments or notifications directly; these should remain orchestrator-owned side effects.

Orchestrator workflow:

- The pipeline has source intake, requirements, test plan, test case generation, case review, approval, export, automation readiness, codegen, execution, debug, skill gap, report, and Jira update.
- Before this change, multi-platform codegen only used the first platform.
- `run_id` exists; future work should add `artifact_id`, `source_hash`, `trace_id`, and consistent `approval_status`.

Pipeline/CI readiness:

- PR and scheduled workflows exist.
- The PR gate should expand toward import checks, collection, contract tests, secret scanning, and affected smoke tests.
- Nightly and release-candidate tiers should be documented and separated from fast PR feedback.

Security/logging risks:

- Source intake redaction exists and is tested.
- RAG indexing previously accepted raw documents.
- Webhooks previously allowed unsigned requests when the secret was absent.
- Some tests print raw response bodies and some helpers log emails.

Generated artifact structure:

- Draft exports and reports exist, but orchestrated runs do not yet consistently write all artifacts under `reports/runs/<run_id>/`.
- Future artifact writers should redact by default and link every file by `run_id`.

Test execution strategy:

- API, web, mobile, DB, and agent tests are marked, but marker governance should be made stricter.
- DB-writing and mobile tests should run in controlled lanes, not in general PR gates.

## Blessed Patterns

API tests:

```python
async with HonoAPIClient() as client:
    token = await client.login(email, password)
    response = await client.put(
        APIEndpoints.ONBOARDING,
        json=payload,
        expected_status=200,
    )
```

Request-level auth for fixtures or CMS flows:

```python
async with HonoAPIClient() as client:
    response = await client.get(
        APIEndpoints.USERS_LIST,
        auth_token=cms_token,
        expected_status=200,
    )
```

No-api-key security test:

```python
async with HonoAPIClient.no_api_key() as client:
    response = await client.get(APIEndpoints.ME, expected_status=401)
```

Generated automation code must:

- Use `HonoAPIClient` for API tests.
- Use page/screen objects for web and mobile tests.
- Use payload builders and factories for valid payloads.
- Use explicit negative builders such as `.without(...)` and `.with_field(...)`.
- Avoid raw sleeps, coordinate taps, and direct mutation of `client._client.headers`.

## Migration Notes

1. Keep existing imports working while migrating:
   - `from config.test_config import TestConfig, APIEndpoints, Timeouts, ReferenceIDs`
   - `from platforms.api.httpx_client import HonoAPIClient`

2. Replace private header mutation:
   - Old: `client._client.headers["Authorization"] = f"Bearer {token}"`
   - New: `client.set_auth_token(token)` or pass `auth_token=token` on the request.

3. Replace raw `httpx.AsyncClient` in normal tests:
   - Use `HonoAPIClient.no_api_key()` for missing API-key cases.
   - Keep raw `httpx` only when a test must bypass framework behavior by design.

4. Move new test data toward:
   - `test_data/builders/`
   - `test_data/factories/`
   - `test_data/references/`
   - `test_data/expected/`

5. Move new locators toward feature/platform registries:
   - `locators/registry/login.web.yaml`
   - `locators/registry/login.android.yaml`
   - `locators/registry/onboarding.android.yaml`

6. Keep self-healing recommendation-first:
   - A healing agent may propose candidates with confidence and evidence.
   - The orchestrator or a human approval gate decides whether files change.

## Remaining Risks

- Many existing API tests still mutate `client._client.headers`; migrate feature by feature.
- Several mobile tests still use sleeps, coordinate taps, ADB commands, and raw Appium internals.
- RAG retrieval filters need to be expanded for feature, platform, endpoint, screen, test type, bug type, confidence, and last updated.
- Reports under `reports/runs/<run_id>/` are not yet fully standardized.
- Some notification paths still build Telegram/Jira messages directly and need shared redaction helpers.
- CI still needs a dedicated secret scan and a stricter marker/tier policy.
