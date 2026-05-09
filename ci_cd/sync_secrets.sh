#!/bin/bash
# Sync .env values to GitHub Actions secrets
# Run: bash ci_cd/sync_secrets.sh

set -e
source .env

echo "Syncing secrets to GitHub..."
gh secret set OPENROUTER_API_KEY     --body "$OPENROUTER_API_KEY"
gh secret set HONO_API_KEY           --body "$HONO_API_KEY"
gh secret set HONO_API_URL           --body "$HONO_API_URL"
gh secret set STAGING_EMAIL          --body "$STAGING_EMAIL"
gh secret set STAGING_PASSWORD       --body "$STAGING_PASSWORD"
gh secret set JIRA_BASE_URL          --body "$JIRA_BASE_URL"
gh secret set JIRA_EMAIL             --body "$JIRA_EMAIL"
gh secret set JIRA_TOKEN             --body "$JIRA_TOKEN"
gh secret set JIRA_PROJECT_KEY       --body "$JIRA_PROJECT_KEY"
gh secret set TELEGRAM_BOT_TOKEN     --body "$TELEGRAM_BOT_TOKEN"
gh secret set TELEGRAM_QA_LEADS_CHAT_ID  --body "$TELEGRAM_QA_LEADS_CHAT_ID"
gh secret set TELEGRAM_QA_TEAM_CHAT_ID   --body "$TELEGRAM_QA_TEAM_CHAT_ID"
gh secret set TELEGRAM_QA_OPS_CHAT_ID    --body "$TELEGRAM_QA_OPS_CHAT_ID"
gh secret set TELEGRAM_QA_BUGS_CHAT_ID   --body "$TELEGRAM_QA_BUGS_CHAT_ID"
gh secret set VPN_CONFIG --body "$(cat /Users/ratikasubarza/Documents/VPN/Hono_Ratika_hono-vpn.ovpn)"

echo "✓ All secrets synced"
