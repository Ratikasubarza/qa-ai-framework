# GitHub Secrets Setup Guide

Add these secrets to your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

## Required Secrets

### LLM / OpenRouter
| Secret | Value |
|--------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |

### Staging API
| Secret | Value |
|--------|-------|
| `HONO_API_URL` | `https://api-dev.thehono.com` |
| `HONO_API_KEY` | Your x-api-key value |
| `STAGING_EMAIL` | `testingHonoA@mailinator.com` |
| `STAGING_PASSWORD` | Your staging password |

### Jira
| Secret | Value |
|--------|-------|
| `JIRA_BASE_URL` | `https://thehono.atlassian.net` |
| `JIRA_EMAIL` | Your Jira email |
| `JIRA_TOKEN` | Your Jira API token |
| `JIRA_PROJECT_KEY` | `HM` |

### Telegram
| Secret | Value |
|--------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `TELEGRAM_QA_LEADS_CHAT_ID` | QA leads chat ID |
| `TELEGRAM_QA_TEAM_CHAT_ID` | QA team chat ID |
| `TELEGRAM_QA_OPS_CHAT_ID` | QA ops chat ID |
| `TELEGRAM_QA_BUGS_CHAT_ID` | QA bugs chat ID |

### VPN (for web tests)
| Secret | Value |
|--------|-------|
| `VPN_CONFIG` | Full content of `Hono_Ratika_hono-vpn.ovpn` file |

## How to Add VPN Config

```bash
# Copy entire .ovpn file content
cat /Users/ratikasubarza/Documents/VPN/Hono_Ratika_hono-vpn.ovpn | pbcopy
```

Then paste as `VPN_CONFIG` secret value.

## Workflow Triggers

| Trigger | Jobs Run |
|---------|----------|
| Push to main/develop | All jobs |
| Pull Request | PR fast check only |
| Daily schedule (08:00 WIB) | All jobs |
| Manual dispatch | Choose suite |

## Manual Run

1. Go to GitHub → Actions tab
2. Select "QA AI Framework — Automated Test Pipeline"
3. Click "Run workflow"
4. Choose test suite: all / web / api / self-healing / debug-agent
