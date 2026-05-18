# How to Use AI Agents

All agents run through the CLI. Never call agent Python files directly in production — use the CLI or the pipeline.

## Full pipeline (recommended)

Runs all agents end-to-end: requirements → testcase → review → approval → codegen → execute → report.

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --feature "User Login" \
  --platform api \
  --ticket HM-516
```

With Confluence PRD:
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --ticket HM-516 \
  --prd-url https://thehono.atlassian.net/wiki/spaces/... \
  --platform api,web \
  --include-subtasks
```

## Individual agents

### Requirements Agent — extract AC from Jira
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py requirements \
  --jira-story HM-516
```

Preview ticket drafts without creating in Jira:
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py drafts \
  --jira-story HM-516 --detail 1
```

### Test Case Agent — generate test cases
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py generate testcase \
  --feature "User Login" \
  --platform api \
  --ac "User can login with valid email and password" \
  --export
```

### Reviewer Agent — quality-check test cases
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py review \
  --feature "User Login" \
  --prd-file docs/prd_login.md \
  --tc-file reports/excel/user_login_testcases.csv
```

### Code Generator Agent — generate pytest code
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py generate code \
  --feature "User Login" \
  --platform api \
  --automation-evidence docs/examples/automation_evidence/users_me_account_api.json
```

### Debug Agent — analyze a failure
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py debug \
  --test-file features/login/steps/api/login_api_test.py \
  --error "AssertionError: expected 200 got 401" \
  --platform api
```

### Approval management

List pending approvals:
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pending
```

Approve / reject a pending run:
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py approve \
  --id HM-516_1716000000 \
  --decision approve \
  --reason "Coverage looks good, edge cases sufficient"
```

### LLM connection check
```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py smoke
```

## Approval tiers (APPROVAL_MODE=smart)

| Confidence | Behavior |
|-----------|---------|
| ≥ 85% AND regression | Auto-approved — pipeline continues |
| 60–84% OR any non-regression | Async Telegram to QA Leads — pipeline pauses |
| < 60% | Auto-rejected — test cases regenerated (max 3 retries) |

Override: set `APPROVAL_MODE=never` in `.env` to skip all approval gates (CI/CD use).

## RAG knowledge base

Index new source documents:
```bash
PYTHONPATH=. ./venv/bin/python3.11 -c "
from knowledge_base.indexer import Indexer
indexer = Indexer()
indexer.index_all()
print('Done')
"
```

Sources indexed automatically:
- `knowledge_base/sources/requirements/` — API specs, Gherkin
- `knowledge_base/sources/bug_history/` — past bugs
- `knowledge_base/sources/test_history/` — past test runs

## Model configuration

Edit `config/agent_config.yaml` to change tier or token budget per agent.

Switch to production (Claude) models:
```bash
MODEL_TIER=production  # in .env
```
