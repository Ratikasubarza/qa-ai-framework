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
