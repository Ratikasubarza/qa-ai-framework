---
name: Test Code Generation Agent
description: Converts a TestCaseAgentOutput into runnable Playwright Python pytest files. Use when you need to generate automation code from approved test cases. Requires explicit automation evidence (actual locators, API payloads, endpoints) — refuses to invent locators when none are provided.
---

## What this agent does

Takes a typed `TestCaseAgentOutput` and generates Playwright Python pytest files saved to `features/{feature}/steps/`.

**Flow:**
1. Format test cases as human-readable text (`_format_test_cases`)
2. Format automation evidence as JSON for the prompt (`_format_automation_evidence`)
3. Load `code_gen` prompt template
4. Call LLM (`ModelTier.STANDARD`) with full test case context + evidence
5. Parse response using `# === FILE: filename ===` markers
6. If no markers found → save as single `{feature}_steps.py` file
7. Always ensure `conftest.py` is present (generated if missing)
8. Save all files to disk and return `{filename: absolute_path}` dict

**Python module:** `agents/code_generator_agent.py`  
**Singleton:** `code_generator_agent = CodeGeneratorAgent()`  
**Prompt name:** `code_gen`  
**Prompt version:** `1.0.0`  
**LLM tier:** `ModelTier.STANDARD`

## Input

Method: `code_generator_agent.run(test_output, platform=Platform.WEB, automation_evidence=None)`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `test_output` | `TestCaseAgentOutput` | ✅ | From `test_case_agent` or loaded from pipeline state |
| `platform` | `Platform` | ❌ | Default `Platform.WEB`; determines `base_url` |
| `automation_evidence` | `dict \| None` | ❌ | Keyed by `platform.value`; contains real locators, API payloads, endpoints |

`automation_evidence` structure (per platform):
```json
{
  "web": { "locators": {...}, "endpoints": [...], "selectors": {...} },
  "api": { "base_url": "...", "payloads": {...}, "headers": {...} },
  "mobile": { "content_descs": [...], "activities": [...] }
}
```

Mobile platforms (`android`, `ios`) also check `automation_evidence["mobile"]` as fallback.

## Output

Returns `dict[str, str]` — `{relative_filename: absolute_path}` for each file saved.

Typical output files:
- `features/{feature_lower}/steps/{feature_lower}_steps.py` — main test file
- `conftest.py` — pytest fixtures (auto-generated if absent from LLM output)

Generated `conftest.py` includes:
- `base_url` session fixture from `TestConfig.WEB_APP_URL`
- `navigate_to_base` autouse fixture that calls `page.goto(base_url)` before each test

## Base URL selection

| `Platform` | `base_url` |
|---|---|
| `Platform.WEB` | `TestConfig.WEB_APP_URL` |
| `Platform.API` | `TestConfig.API_URL` |
| Other | Falls back to `TestConfig.WEB_APP_URL` |

## Automation evidence rule

If `automation_evidence` is empty or has no entry for the platform, the prompt explicitly includes:

> "NO EXECUTION EVIDENCE PROVIDED. Do not invent locators, selectors, API payloads, assertions, or navigation steps."

**The agent will generate structurally correct but non-functional placeholder code** — it will not hallucinate locators. This is intentional and enforced by the prompt.

## Rules

- **Never hardcode credentials or URLs** — use `TestConfig.API_URL`, `TestConfig.WEB_APP_URL`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Do not invent locators** — without evidence the agent writes TODO stubs, not invented selectors
- **Automation readiness gate** (`node_automation_readiness` in pipeline) must pass before this agent is called in the orchestrated pipeline
- **Output directory:** `features/{feature_lower}/steps/` — `feature_lower` is `feature.lower().replace(" ", "_")`
- **File markers:** LLM output uses `# === FILE: path/to/file.py ===` delimiters; agent falls back to single file if absent
- **Integrity:** generated code must call real API endpoints and assert real response fields — never mock the product under test
