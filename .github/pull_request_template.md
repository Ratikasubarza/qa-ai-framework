## Summary

Brief description of what this PR changes and why.

## Type of change

- [ ] New test suite (new feature under `features/`)
- [ ] Bug fix in existing test
- [ ] Agent improvement (`agents/`)
- [ ] Pipeline / orchestration change (`orchestrator/`)
- [ ] Config / infrastructure change (`config/`, `.github/`)
- [ ] Documentation update

## Checklist

### Code quality
- [ ] `PYTHONPATH=. ./venv/bin/python3.11 -m py_compile [changed files]` — syntax OK
- [ ] `./venv/bin/python3.11 -m ruff check . --select E,W,F --ignore E501,E402` — no lint errors
- [ ] No hardcoded URLs — use `TestConfig.API_URL` or `APIEndpoints`
- [ ] No hardcoded credentials — use `os.getenv()` via `TestConfig` or `KnownAccounts`
- [ ] `.env` not committed (check `git status`)

### Test integrity
- [ ] All existing tests still pass locally
- [ ] New tests follow `test_TC_[SUITE]_[NUM]_[description]` naming
- [ ] `@pytest.mark` applied to all new test functions
- [ ] Gherkin `.feature` file updated if test logic changed
- [ ] TDD flow followed: spec written first, red → green confirmed

### AI agent changes (if applicable)
- [ ] `.claude/agents/` md file updated to match Python agent changes
- [ ] `.github/agents/` md file synced (must match `.claude/agents/`)
- [ ] Input sanitizer called before LLM boundary
- [ ] Output uses typed Pydantic contract from `core/agent_contracts.py`

### Documentation
- [ ] `AGENTS.md` updated if new conventions or folder structure added
- [ ] `config/agent_config.yaml` updated if new agent added
- [ ] `.env.example` updated if new env var added

## Testing evidence

```
# Paste output of running the affected tests:
PYTHONPATH=. ./venv/bin/python3.11 -m pytest [affected_test] -v --tb=short
```

## Related Jira ticket

<!-- e.g. HM-516 -->
