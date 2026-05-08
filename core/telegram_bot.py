"""
Telegram Bot — interactive approval interface + notifications.
Inline keyboards let QA Leads approve/reject AI output from their phone.
Channels:
  qa_leads → interactive approvals (test cases, tickets, AC review)
  qa_team  → informational results (test runs, coverage reports)
  qa_ops   → system alerts (self-heal, circuit breaker, CI failures)
  qa_bugs  → auto-created Jira bug notifications
"""
import asyncio
import structlog
from typing import Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config.settings import settings
from core.secret_manager import secret_manager
from core.agent_contracts import AgentFeedback, Decision, RejectionReason

logger = structlog.get_logger(__name__)


class QATelegramBot:
    def __init__(self):
        token = secret_manager.get("telegram_bot_token")
        self.bot      = Bot(token=token)
        self.channels = settings.telegram_channels
        self.app      = Application.builder().token(token).build()
        self._register_handlers()
        self._review_queue = None  # Injected after init to avoid circular import

    def set_review_queue(self, queue):
        self._review_queue = queue

    def _register_handlers(self):
        self.app.add_handler(
            CallbackQueryHandler(self._handle_callback)
        )

    async def _handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data  # Format: "action:output_id[:reason]"
        parts = data.split(":")

        if len(parts) < 2:
            return

        action, output_id = parts[0], parts[1]
        reason = parts[2] if len(parts) > 2 else None

        if not self._review_queue:
            return

        if action == "approve":
            feedback = AgentFeedback(
                output_id=output_id,
                decision=Decision.APPROVE,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(
                f"✅ Approved by {query.from_user.first_name}"
            )

        elif action == "reject":
            feedback = AgentFeedback(
                output_id=output_id,
                decision=Decision.REJECT,
                rejection_reason=RejectionReason(reason) if reason else None,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(
                f"❌ Rejected by {query.from_user.first_name}"
            )

        elif action == "edit":
            feedback = AgentFeedback(
                output_id=output_id,
                decision=Decision.EDIT,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(
                f"✏️ Edit requested by {query.from_user.first_name}\n"
                f"Reply with your corrections."
            )
        else:
            return

        self._review_queue.resolve(output_id, feedback)

    # ── Notification Methods ──────────────────────────────────────────

    async def send_test_cases_for_review(
        self,
        output_id: str,
        feature:   str,
        scenarios: list,
        model_used: str,
    ) -> None:
        """Send generated test cases to QA Leads for approval."""
        scenario_list = "\n".join(
            f"  {'🔥' if s.priority.value == 'high' else '🔹'} "
            f"[{s.test_type.value.upper()}] {s.name}"
            for s in scenarios[:10]  # Max 10 in preview
        )
        if len(scenarios) > 10:
            scenario_list += f"\n  ... and {len(scenarios) - 10} more"

        text = (
            f"📋 *TEST CASES READY FOR REVIEW*\n\n"
            f"Feature: `{feature}`\n"
            f"Scenarios: {len(scenarios)}\n"
            f"Model: `{model_used}`\n\n"
            f"*Scenarios:*\n{scenario_list}\n\n"
            f"Output ID: `{output_id}`"
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{output_id}"),
            InlineKeyboardButton("✏️ Edit",    callback_data=f"edit:{output_id}"),
            InlineKeyboardButton("❌ Reject",   callback_data=f"reject:{output_id}"),
        ]])

        await self._send(self.channels["qa_leads"], text, keyboard)

    async def send_test_result(
        self,
        feature:    str,
        passed:     int,
        failed:     int,
        skipped:    int,
        duration:   float,
    ) -> None:
        """Send test run result to QA Team channel."""
        total  = passed + failed + skipped
        emoji  = "✅" if failed == 0 else "❌"
        rate   = round(passed / total * 100) if total > 0 else 0

        text = (
            f"{emoji} *TEST RUN COMPLETE*\n\n"
            f"Feature: `{feature}`\n"
            f"Pass: {passed}/{total} ({rate}%)\n"
            f"Fail: {failed}  |  Skip: {skipped}\n"
            f"Duration: {duration:.1f}s"
        )
        await self._send(self.channels["qa_team"], text)

    async def send_self_heal_result(
        self,
        feature:    str,
        healed:     bool,
        locator:    str,
    ) -> None:
        """Send self-healing event to QA Ops channel."""
        emoji = "🔧" if healed else "🚨"
        status = "healed automatically" if healed else "FAILED — manual fix required"
        text = (
            f"{emoji} *SELF-HEAL EVENT*\n\n"
            f"Feature: `{feature}`\n"
            f"Locator: `{locator[:60]}...`\n"
            f"Status: {status}"
        )
        await self._send(self.channels["qa_ops"], text)

    async def send_bug_created(
        self,
        jira_key:  str,
        summary:   str,
        severity:  str,
        jira_url:  str,
    ) -> None:
        """Notify QA Bugs channel when Debug Agent creates a Jira ticket."""
        emoji = "🔴" if severity.lower() == "high" else "🟡"
        text = (
            f"{emoji} *BUG CREATED*\n\n"
            f"Ticket: `{jira_key}`\n"
            f"Summary: {summary}\n"
            f"Severity: {severity}\n"
            f"[View in Jira]({jira_url})"
        )
        await self._send(self.channels["qa_bugs"], text)

    async def send_circuit_breaker_alert(self, agent_name: str, error: str) -> None:
        """Alert QA Ops when a circuit breaker opens."""
        text = (
            f"⚡ *CIRCUIT BREAKER OPEN*\n\n"
            f"Agent: `{agent_name}`\n"
            f"Error: {error[:200]}\n\n"
            f"Agent calls are blocked until recovery."
        )
        await self._send(self.channels["qa_ops"], text)

    async def _send(
        self,
        chat_id:  str,
        text:     str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error("telegram_send_failed", chat_id=chat_id, error=str(e))

    async def start_webhook(self, webhook_url: str, port: int = 8000):
        """Start webhook server — use with ngrok in development."""
        await self.app.initialize()
        await self.app.bot.set_webhook(
            url=f"{webhook_url}/telegram/webhook"
        )
        logger.info("telegram_webhook_set", url=webhook_url)
        await self.app.start()
        await self.app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/telegram/webhook",
        )

    async def start_polling(self):
        """Polling mode — simpler for local dev without ngrok."""
        logger.info("telegram_polling_started")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()


telegram_bot = QATelegramBot()
