# MCP and Agent Setup

This project supports two different working modes. Keep them separate so the team
does not confuse AI IDE tooling with the runtime QA framework.

## Mode 1: Framework Runtime

Use this mode for the actual QA pipeline.

Command example:

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --feature "HM-516 Profile Posts Tab Android" \
  --platform android \
  --ticket "HM-516" \
  --include-subtasks \
  --story "Generate Android UI test cases only. Exclude API contract tests."
```

Runtime source adapters live in:

| Source | Adapter |
| --- | --- |
| Jira | `mcp_tools/jira_client/jira_client.py` |
| Confluence | `mcp_tools/confluence_client/confluence_client.py` |
| Telegram | `mcp_tools/telegram_bot/run_bot.py` |
| Jira webhook | `mcp_tools/jira_webhook/webhook_server.py` |

This mode reads credentials from `.env`. It does not require starting an
external MCP server for normal Jira/Confluence pipeline runs.

Required environment variables:

```bash
JIRA_BASE_URL=https://thehono.atlassian.net
JIRA_EMAIL=<your-email>
JIRA_TOKEN=<your-atlassian-api-token>
JIRA_PROJECT_KEY=HM
```

Optional:

```bash
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_QA_OPS_CHAT_ID=<chat-id>
```

## Mode 2: Manual AI IDE Workflow

Use this mode when a QA/Dev wants to work manually inside an AI IDE such as
Copilot, Augment, Claude Code, or another agent-enabled editor.

Agent profiles live in:

| Agent | Purpose |
| --- | --- |
| `.github/agents/case-generation.agent.md` | Generate scoped test cases |
| `.github/agents/case-reviewer.agent.md` | Review test cases against source requirements |
| `.github/agents/tdd-automation.agent.md` | Convert approved cases into automation with TDD |

Recommended external MCP configuration:

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Use Atlassian MCP only with an account that has access to the Jira/Confluence
content being reviewed. Do not force-open documents owned by another user.

## Recommended Team Workflow

Use parent Jira tickets for context, but keep generation scoped by platform.

```text
Jira parent ticket + optional PRD
  -> source intake
  -> platform-aware subtask filtering
  -> requirements extraction
  -> test case generation
  -> AI case review
  -> QA Lead approval
  -> CSV/Excel export
  -> TDD automation
```

For parent tickets with BE, FE, and Mobile subtasks:

| Target | Command Platform | Included Subtasks |
| --- | --- | --- |
| API tests | `--platform api` | `[BE]`, API, endpoint, contract, payload, schema |
| Android tests | `--platform android` | `[Mobile]`, mobile, Android, Flutter, Appium |
| Web tests | `--platform web` | `[FE]`, frontend, web, CMS, browser, Playwright |

If no platform-specific subtask can be detected, the pipeline keeps all subtasks
as fallback context.

The case-review gate is also platform-aware. Missing cases and findings are
classified as:
- `in_scope_missing`: blocks the current platform plan
- `cross_platform_related_risk`: reported, but does not block this platform
- `clarification_needed`: reported for PO/Dev follow-up
- `security_blocker`: always blocks until redacted or removed

Automation code generation has a separate readiness gate. It requires executable
flow evidence before codegen:
- API: curl/endpoint/spec, method, expected status/schema
- Android/iOS: actual app steps, locator/app-source/accessibility evidence, test data
- Web: URL/route, actual web steps, selector/DOM/accessibility evidence

If evidence is missing, the framework reports what is missing and does not
generate code. This prevents fake steps, fake locators, fake payloads, weak
assertions, and automation that only passes because the AI changed the truth of
the test.

Debug triage also has an integrity policy:
- failed tests are quality signals, not problems to hide
- product/API/developer bugs must preserve the failing signal and produce a bug
  report or human triage item
- AI must not remove assertions, weaken expected results, skip tests, catch and
  ignore exceptions, or change steps to avoid the real failure
- auto-fix is allowed only for high-confidence test bugs, locator issues, or
  flaky sync issues where approved expected behavior remains intact

## When To Start External MCP

Start or configure external MCP when:
- working manually in an AI IDE
- asking an IDE agent to fetch Jira/Confluence directly
- asking an IDE agent to observe or inspect web behavior via Playwright

Do not start external MCP just to run:

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline ...
```

The CLI pipeline already uses the Python adapters in `mcp_tools/`.

## Safety Rules

- Never commit `.env`.
- Never paste personal Atlassian tokens into agent instructions.
- Keep credentials local to `.env` or the IDE MCP credential store.
- Do not use another person's Confluence/Jira credentials.
- Keep generated official exports separate from drafts:
  - drafts: `reports/drafts/`
  - approved exports: generated after case review and approval pass

## Internal Data Security Criteria

AI agents may read internal Jira, Confluence, PRD, API, and subtask context only
to produce QA artifacts for this repository. Treat all credentialed source data
as internal by default.

### Data Classification

| Class | Examples | Allowed In Outputs |
| --- | --- | --- |
| Public | public docs, public package names, public API standards | yes |
| Internal | Jira summaries, PRD behavior, acceptance criteria, non-secret API contracts | yes, summarized and scoped |
| Confidential | unreleased roadmap, partner/customer names, internal URLs, private architecture notes | only if required, minimized |
| Secret | tokens, passwords, cookies, API keys, auth headers, private certs, DB credentials | never |
| Personal Data | emails, phone numbers, names tied to users, screenshots with identifiable data | avoid; redact unless explicitly required for a test |

### Do

- Use the current user's authorized Jira/Confluence access only.
- Fetch only the ticket, PRD, subtask, or URL required for the current task.
- Prefer summaries over copying full internal documents into prompts or outputs.
- Keep test cases focused on behavior, not secret implementation detail.
- Redact tokens, cookies, auth headers, passwords, personal emails, private IDs,
  and raw customer/user data.
- Use synthetic test data in generated cases and automation.
- Store credentials only in `.env`, local keychains, or the IDE MCP credential
  store.
- Mention internal API contracts at the level needed for QA, such as endpoint,
  method, expected schema shape, status code, and validation behavior.
- Record source references by key or title, for example `HM-516` or PRD title,
  instead of pasting entire confidential source text into reports.

### Don't

- Do not paste Atlassian API tokens, cookies, bearer tokens, session IDs, DB
  passwords, or `.env` contents into prompts, agent files, reports, screenshots,
  CSV, Excel, logs, or commits.
- Do not fetch or summarize unrelated tickets, PRDs, users, customer records, or
  private pages outside the requested scope.
- Do not bypass permissions, use another person's credentials, or force-open
  credentialed resources the current user cannot access.
- Do not include raw internal implementation notes in public-facing artifacts.
- Do not generate test data using real users, real customer names, real phone
  numbers, real emails, or production identifiers.
- Do not expose full request/response bodies when they contain secrets or
  personal data. Keep only the fields needed for QA validation.
- Do not commit generated reports if they contain confidential source text,
  screenshots, tokens, or personal data.
- Do not ask an external model or external MCP to process data that violates the
  team's access or retention policy.

### API/Subtask Handling

When fetching API subtasks:
- include endpoint names, methods, schema expectations, validation rules, and
  status codes when they are needed for tests
- omit credentials, auth token values, private headers, database credentials,
  raw production payloads, and internal-only operational notes
- convert examples into synthetic payloads before writing test cases
- separate API-only risks from Android/Web UI test plans

Example safe output:

```text
Validate POST /posts rejects an empty content field with 400 and a structured
validation error.
```

Unsafe output:

```text
Use Bearer eyJ... from the Jira comment and call the staging endpoint with the
real user email shown in the screenshot.
```

### Agent Stop Conditions

An agent must stop and ask for human review when:
- a source contains tokens, cookies, private keys, DB credentials, or production
  personal data
- the requested artifact requires data outside the current user's permission
- the output would need to include confidential implementation details not
  required for QA validation
- a screenshot or attachment contains visible personal or customer data

### Review Checklist Before Commit or Share

- [ ] No `.env` content
- [ ] No access tokens, cookies, passwords, or API keys
- [ ] No real customer/user personal data
- [ ] No unrelated Jira/Confluence content
- [ ] No full confidential PRD pasted into generated artifacts
- [ ] Synthetic test data only
- [ ] Source references are traceable but minimal
- [ ] Draft artifacts with sensitive content stay local
