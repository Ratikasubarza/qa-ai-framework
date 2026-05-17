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
        self.bot             = Bot(token=token)
        self.channels        = settings.telegram_channels
        self.app             = Application.builder().token(token).build()
        self._register_handlers()
        self._review_queue   = None   # Injected via set_review_queue()
        self._polling_active = False  # Guard against double-start

    def set_review_queue(self, queue):
        self._review_queue = queue

    def _register_handlers(self):
        self.app.add_handler(
            CallbackQueryHandler(self._handle_callback)
        )

    async def _handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data  # Format: "action:id[:reason]"
        parts = data.split(":")

        if len(parts) < 2:
            return

        action     = parts[0]
        target_id  = parts[1]
        reason_arg = parts[2] if len(parts) > 2 else None
        reviewer   = query.from_user.first_name

        # ── Async pending-approval callbacks ──────────────────────────
        # approval_ids look like "HM-516_1234567890"; review-queue ids are 8-char UUIDs
        if action in ("approve", "reject", "approve_notes") and (
            "_" in target_id and len(target_id) > 10
        ):
            from core.workflows.pending_approvals import PendingApprovalStore
            store = PendingApprovalStore()
            decision = "approve" if action in ("approve", "approve_notes") else "reject"
            ok = store.resolve(target_id, decision, reason=reason_arg or "")
            status_text = (
                f"✅ Approved by {reviewer}"
                if decision == "approve"
                else f"❌ Rejected by {reviewer}"
            )
            await query.edit_message_text(status_text)
            logger.info(
                "async_approval_resolved",
                approval_id=target_id,
                decision=decision,
                reviewer=reviewer,
                store_ok=ok,
            )
            return

        # ── Legacy review-queue callbacks ─────────────────────────────
        if not self._review_queue:
            return

        if action == "approve":
            feedback = AgentFeedback(
                output_id=target_id,
                decision=Decision.APPROVE,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(f"✅ Approved by {reviewer}")

        elif action == "reject":
            feedback = AgentFeedback(
                output_id=target_id,
                decision=Decision.REJECT,
                rejection_reason=RejectionReason(reason_arg) if reason_arg else None,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(f"❌ Rejected by {reviewer}")

        elif action == "edit":
            feedback = AgentFeedback(
                output_id=target_id,
                decision=Decision.EDIT,
                reviewer_id=str(query.from_user.id),
            )
            await query.edit_message_text(
                f"✏️ Edit requested by {reviewer}\nReply with your corrections."
            )
        else:
            return

        self._review_queue.resolve(target_id, feedback)

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

    async def send_alert(self, message: str) -> None:
        """Send a plain alert to the QA Ops channel."""
        await self._send(self.channels["qa_ops"], message)

    async def request_approval_async(
        self,
        approval_id:    str,
        feature:        str,
        ticket:         str,
        confidence:     float,
        scenarios_count: int,
        coverage:       str,
        timeout_hours:  int = 24,
    ) -> None:
        """
        Send async approval request to QA Leads — pipeline does NOT wait for reply.
        Approve/Reject buttons write to PendingApprovalStore; resolve() resumes the run.
        """
        confidence_emoji = (
            "🟢" if confidence >= 0.85
            else "🟡" if confidence >= 0.60
            else "🔴"
        )
        message = (
            f"🧪 *Test Cases Ready for Review*\n\n"
            f"*Ticket:* {ticket or 'N/A'}\n"
            f"*Feature:* {feature}\n"
            f"*Scenarios:* {scenarios_count}\n"
            f"*Confidence:* {confidence_emoji} {confidence:.0%}\n"
            f"*Coverage:* {coverage or 'N/A'}\n\n"
            f"_You have {timeout_hours}h to review. "
            f"No response → auto-escalated._"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Approve", callback_data=f"approve:{approval_id}"
                ),
                InlineKeyboardButton(
                    "❌ Reject", callback_data=f"reject:{approval_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "✏️ Approve with notes",
                    callback_data=f"approve_notes:{approval_id}",
                ),
            ],
        ])
        await self._send(self.channels["qa_leads"], message, keyboard)
        logger.info(
            "async_approval_requested",
            approval_id=approval_id,
            feature=feature,
            confidence=confidence,
        )

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

    async def start_polling(self) -> None:
        """Start the callback handler — non-blocking; polling runs as background asyncio tasks.

        Must be called in the same event loop as the agent that awaits ReviewItem.wait(),
        because review_queue uses asyncio.Event which is event-loop-bound.
        Call stop_polling() when done.
        """
        if self._polling_active:
            logger.debug("telegram_already_polling")
            return
        await self.app.initialize()
        await self.app.start()
        # drop_pending_updates avoids stale callbacks from a previous run firing immediately
        await self.app.updater.start_polling(drop_pending_updates=True)
        self._polling_active = True
        logger.info("telegram_polling_started")

    async def stop_polling(self) -> None:
        """Gracefully stop polling and release the httpx session."""
        if not self._polling_active:
            return
        try:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        except Exception as e:
            logger.error("telegram_stop_failed", error=str(e))
        finally:
            self._polling_active = False
        logger.info("telegram_polling_stopped")


telegram_bot = QATelegramBot()
