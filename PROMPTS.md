# PROMPTS.md — QA AI Framework Prompt Templates

All LLM prompts are versioned files in `prompts/` and registered in `prompts/prompt_registry.yaml`.
Loaded at runtime via `core/prompt_manager.py`.

---

## Prompt Inventory

| Prompt Key | Version | File | Agent | Model Tier |
|------------|---------|------|-------|------------|
| `test_case_gen` | 2.0.0 | `test_case_gen_v2.0.0.txt` | TestCaseAgent | standard |
| `test_case_gen_v1` | 1.0.0 | `test_case_gen_v1.0.0.txt` | TestCaseAgent (legacy) | standard |
| `ac_extraction` | 1.0.0 | `ac_extraction_v1.0.0.txt` | RequirementsAgent | standard |
| `code_gen` | 1.0.0 | `code_gen_v1.0.0.txt` | CodeGeneratorAgent | standard |
| `reviewer` | 1.0.0 | `reviewer_v1.0.0.txt` | ReviewerAgent | complex |

---

## `test_case_gen` v2.0.0

**Used by:** `agents/test_case_agent.py`
**Purpose:** Generate 20+ comprehensive test scenarios from feature description + AC

### Input variables
| Variable | Source | Description |
|----------|--------|-------------|
| `{feature}` | `TestCaseAgentInput.feature` | Feature name |
| `{description}` | `TestCaseAgentInput.description` | User story or feature description |
| `{platforms}` | `TestCaseAgentInput.platforms` | Target platforms (api, web, android) |
| `{acceptance_criteria}` | AC from Jira / requirements_agent | Bullet list of AC items |
| `{past_context}` | RAG + Jira subtask history + Confluence PRD | Existing tests + bug history |

### Output format (JSON)
```json
{
  "feature": "...",
  "scenarios": [
    {
      "scenario_id": "TC-001",
      "name": "...",
      "precondition": "...",
      "steps": "...",
      "expected_result": "...",
      "test_type": "smoke|functional|regression|e2e|negative|boundary",
      "priority": "high|medium|low",
      "platforms": ["api"],
      "tags": ["smoke", "P0"],
      "regression_candidate": true,
      "regression_risk_area": ["auth", "posts"]
    }
  ],
  "coverage_summary": "...",
  "total_scenarios": 20
}
```

### Versioning rules
- Bump minor for wording changes that don't affect output shape
- Bump major for structural changes (new JSON fields, different output format)
- Update `prompt_registry.yaml` + set `version` field in the file header comment
- Add changelog entry to `prompt_registry.yaml`

---

## `ac_extraction` v1.0.0

**Used by:** `agents/requirements_agent.py`
**Purpose:** Extract structured acceptance criteria from raw user story / Jira description

### Input variables
| Variable | Source |
|----------|--------|
| `{story_text}` | Jira description (ADF→plain) or manual input |
| `{feature}` | Feature name |

### Output format (JSON)
```json
{
  "acceptance_criteria": ["AC item 1", "AC item 2"],
  "criteria": [
    {"summary": "...", "description": "...", "category": "functional|security|performance"}
  ]
}
```

---

## `code_gen` v1.0.0

**Used by:** `agents/code_generator_agent.py`
**Purpose:** Generate pytest async test file from test case scenarios

### Input variables
| Variable | Source |
|----------|--------|
| `{feature}` | Feature name |
| `{scenarios_json}` | JSON array of `ScenarioSchema` from TestCaseAgent |
| `{platform}` | `api` | `web` | `android` |
| `{endpoint}` | API endpoint (api platform only) |

### Output
Executable pytest file following the patterns in `features/*/steps/api/`.

### Conventions enforced in prompt
- `pytestmark = allure.feature("...")`
- Single-line docstring: `"""TC-XXX | Category | Description"""`
- `@pytest.mark.asyncio` only (no per-test allure decorators)
- Uses `HonoAPIClient` / `APIAssertions` for API tests
- Uses `BasePage` / `WebAssertions` for web tests

---

## `reviewer` v1.0.0

**Used by:** `agents/reviewer_agent.py`
**Purpose:** Review generated test cases against PRD for coverage completeness

### Input variables
| Variable | Source |
|----------|--------|
| `{prd_content}` | Confluence PRD or Jira story text |
| `{test_cases_json}` | Generated test cases from TestCaseAgent |
| `{feature}` | Feature name |
| `{target_platforms}` | Platforms being tested |

### Output (JSON)
```json
{
  "quality_score": 8.5,
  "coverage_percentage": 85,
  "status": "approved|needs_revision",
  "findings": {"critical": 0, "major": 1, "minor": 2},
  "missing_test_cases": ["..."],
  "prd_clarifications": ["..."]
}
```

---

## How to add a new prompt

1. Create `prompts/<key>_v<N.M.P>.txt` with `{variable}` placeholders
2. Add entry to `prompts/prompt_registry.yaml`:
   ```yaml
   my_new_prompt:
     version: "1.0.0"
     model_tier: standard
     changelog: "Initial version — ..."
     template_ref: "prompts/my_new_prompt_v1.0.0.txt"
     eval_threshold: 0.85
   ```
3. Load via `core/prompt_manager.py`:
   ```python
   from core.prompt_manager import prompt_manager
   text = prompt_manager.render("my_new_prompt", feature="...", description="...")
   ```
4. Write an eval in `tests/evals/` to validate quality gate

---

## Model tiers

Configured in `prompts/model_config.yaml` and `core/llm_client.py`.

| Tier | Dev model | Prod model | Use for |
|------|-----------|-----------|---------|
| `fast` | free/small | claude-haiku | smoke, quick checks |
| `standard` | free/mid | claude-sonnet | test case gen, code gen |
| `complex` | free/large | claude-opus | reviewer, deep analysis |

Switch tiers: set `MODEL_TIER=production` in `.env` + `ANTHROPIC_API_KEY`.
