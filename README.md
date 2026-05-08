# QA AI Framework — Phase 1 + 2

Stack: Python 3.11+ | OpenRouter | LangGraph | Playwright | Telegram | ChromaDB

---

## Setup

### 1. Clone & install

```bash
git clone <your-repo>
cd qa-ai-framework
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in your keys:
#   OPENROUTER_API_KEY   → from openrouter.ai
#   JIRA_BASE_URL        → your Atlassian URL
#   JIRA_EMAIL           → your Jira email
#   JIRA_TOKEN           → Jira API token
#   TELEGRAM_BOT_TOKEN   → from @BotFather
#   TELEGRAM_*_CHAT_ID   → group chat IDs (see below)
```

### 3. Get Telegram Chat IDs

```
1. Add your bot to each Telegram group
2. Send /start in each group
3. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Copy the chat.id values into .env
```

### 4. Smoke test — verify LLM connection

```bash
python cli.py smoke
# Expected: ✓ LLM connection OK — model: meta-llama/llama-3.1-8b-instruct:free
```

---

## Usage

### Generate test cases (approval required — bot must be running)

```bash
# Terminal 1 — start the bot
python cli.py bot start --mode polling

# Terminal 2 — generate test cases
python cli.py generate testcase \
  --feature "User Login" \
  --description "User authenticates with email and password" \
  --platform web \
  --ac "User can log in with valid credentials" "Login fails with wrong password"
```

The bot will send a Telegram message to #qa-leads with Approve/Edit/Reject buttons.

### Generate without approval (for testing)

```bash
# Set APPROVAL_REQUIRED=false in .env
python cli.py generate testcase --feature "Login" --platform web
```

### Webhook mode (with ngrok)

```bash
# Terminal 1 — start ngrok
ngrok http 8000

# Terminal 2 — start bot with webhook
python cli.py bot start --mode webhook --ngrok-url https://xxxx.ngrok.io
```

---

## Run Evals

```bash
# Create sample fixture first
python tests/evals/test_case_eval.py

# Run evals
pytest tests/evals/ -v
```

---

## Project Structure

```
qa-ai-framework/
├── agents/          test_case_agent.py
├── core/            llm_client | agent_contracts | circuit_breaker
│                    input_sanitizer | prompt_manager | telegram_bot
├── knowledge_base/  rag_engine (ChromaDB)
├── prompts/         prompt_registry.yaml | model_config.yaml | *.txt
├── approval_workflow/ feedback_schema (review queue)
├── config/          settings.py
├── tests/evals/     test_case_eval.py + golden fixtures
└── cli.py           entry point
```

---

## OpenRouter Free Models Used

| Tier     | Model                                    | Used For                  |
|----------|------------------------------------------|---------------------------|
| fast     | meta-llama/llama-3.1-8b-instruct:free   | Classification, triage    |
| standard | meta-llama/llama-3.3-70b-instruct:free  | Test generation, code gen |
| complex  | deepseek/deepseek-r1:free               | Debug, deep analysis      |

Upgrade path: remove `:free` suffix from `prompts/model_config.yaml` when ready.
