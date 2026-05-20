#!/bin/bash
# Sync .env values to GitHub Actions secrets
# Run: bash ci_cd/sync_secrets.sh

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Create it locally before syncing secrets." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

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
if [[ -n "${VPN_CONFIG_PATH:-}" ]]; then
  if [[ ! -f "$VPN_CONFIG_PATH" ]]; then
    echo "VPN_CONFIG_PATH is set but file does not exist: $VPN_CONFIG_PATH" >&2
    exit 1
  fi
  gh secret set VPN_CONFIG --body-file "$VPN_CONFIG_PATH"
else
  echo "Skipping VPN_CONFIG. Set VPN_CONFIG_PATH to sync it."
fi

echo "All configured secrets synced"
