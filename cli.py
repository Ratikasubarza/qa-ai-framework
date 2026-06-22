import asyncio
import argparse
import sys
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
logger  = structlog.get_logger(__name__)


async def cmd_smoke(args):
    from core.llm_client import llm_client, ModelTier
    console.print("[cyan]Running smoke test...[/]")
    try:
        response = llm_client.complete_text(
            system="You are a QA engineer. Reply with exactly: OK",
            user="Are you ready?",
            tier=ModelTier.FAST,
            agent_name="smoke_test",
        )
        if "OK" in response.content:
            console.print(f"[green]✓ LLM connection OK[/] — model: {response.model}")
        else:
            console.print(f"[yellow]⚠ Unexpected:[/] {response.content}")
    except Exception as e:
        console.print(f"[red]✗ LLM FAILED:[/] {e}")
        sys.exit(1)


async def cmd_run(args):
    from core.telegram_bot import telegram_bot
    from core.workflows.approval_workflow import review_queue
    from agents.test_case_agent import test_case_agent
    from core.agent_contracts import TestCaseAgentInput, Platform
    telegram_bot.set_review_queue(review_queue)
    await telegram_bot.start_polling()
    await asyncio.sleep(2)
    console.print("[green]✓ Bot running[/]")
    platforms  = [Platform(p.strip()) for p in args.platform.split(",")]
    input_data = TestCaseAgentInput(
        feature=args.feature,
        description=args.description or args.feature,
        platforms=platforms,
        acceptance_criteria=args.ac or [],
    )
    try:
        output = await test_case_agent.run(input_data)
        _print_testcase_output(output)
    except ValueError as e:
        console.print(f"[red]Agent error:[/] {e}")
    finally:
        await telegram_bot.stop_polling()


async def cmd_generate_testcase(args):
    from agents.test_case_agent import test_case_agent
    from core.agent_contracts import TestCaseAgentInput, Platform
    platforms  = [Platform(p.strip()) for p in args.platform.split(",")]
    input_data = TestCaseAgentInput(
        feature=args.feature,
        description=args.description or args.feature,
        platforms=platforms,
        acceptance_criteria=args.ac or [],
        jira_story_key=getattr(args, "jira_story", None),
    )
    console.print(Panel(
        f"[bold cyan]Generating:[/] {args.feature}",
        title="[bold]Test Case Agent", border_style="cyan",
    ))
    try:
        output = await test_case_agent.run(input_data)
        _print_testcase_output(output)
        if getattr(args, "export", False):
            from skills.reporting.excel_writer import excel_writer
            paths = excel_writer.write_both(output)
            console.print(f"\n[green]✓ CSV:[/] {paths['csv']}")
            console.print(f"[green]✓ Excel:[/] {paths['excel']}")
    except ValueError as e:
        console.print(f"[red]Agent error:[/] {e}")
        sys.exit(1)


def _print_testcase_output(output):
    table = Table(title=f"Test Cases — {output.feature}", border_style="cyan", show_lines=True)
    table.add_column("ID",       style="dim",    width=8)
    table.add_column("Scenario", style="white",  width=25)
    table.add_column("Steps (Gherkin)", style="cyan", width=50)
    table.add_column("Type",     style="yellow", width=10)
    table.add_column("Platform", style="green",  width=8)
    table.add_column("Priority", style="red",    width=8)
    for s in output.scenarios:
        # Format steps as Gherkin string
        steps_text = "\n".join(
            st.action for st in s.steps
        ) if s.steps else s.expected_result or ""
        table.add_row(s.scenario_id, s.name, steps_text, s.test_type.value,
                      ", ".join(p.value for p in s.platforms), s.priority.value)
    console.print(table)
    console.print(f"\n[green]✓[/] {output.total_scenarios} scenarios | Model: {output.model_used}")


def cmd_generate_code(args):
    from agents.test_case_agent import test_case_agent
    from agents.code_generator_agent import code_generator_agent
    from core.automation_readiness import load_automation_evidence
    from core.agent_contracts import TestCaseAgentInput, Platform
    try:
        automation_evidence = load_automation_evidence(args.automation_evidence)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Automation evidence error:[/] {e}")
        sys.exit(1)
    platforms  = [Platform(p.strip()) for p in args.platform.split(",")]
    input_data = TestCaseAgentInput(
        feature=args.feature,
        description=args.description or args.feature,
        platforms=platforms,
        acceptance_criteria=args.ac or [],
    )
    console.print(Panel(
        f"[bold cyan]Step 1:[/] Generate test cases\n[bold cyan]Step 2:[/] Generate Playwright code",
        title="[bold]Code Generator", border_style="cyan",
    ))
    tc_output   = asyncio.run(test_case_agent.run(input_data))
    saved_files = code_generator_agent.run(
        tc_output,
        platforms[0],
        automation_evidence=automation_evidence,
    )
    console.print(f"\n[green]✓ Playwright code generated:[/]")
    for f in saved_files:
        console.print(f"  [dim]→[/] {f}")
    feature_low = args.feature.lower().replace(" ", "_")
    console.print(f"\n[cyan]Run:[/]  pytest features/{feature_low}/steps/ -v")


def cmd_export(args):
    from agents.test_case_agent import test_case_agent
    from skills.reporting.excel_writer import excel_writer
    from core.agent_contracts import TestCaseAgentInput, Platform
    platforms  = [Platform(p.strip()) for p in args.platform.split(",")]
    input_data = TestCaseAgentInput(
        feature=args.feature,
        description=args.description or args.feature,
        platforms=platforms,
        acceptance_criteria=args.ac or [],
    )
    console.print(Panel(
        f"[bold cyan]Generating + Exporting:[/] {args.feature}",
        title="[bold]Export", border_style="cyan",
    ))
    output = asyncio.run(test_case_agent.run(input_data))
    _print_testcase_output(output)
    paths = excel_writer.write_both(output)
    console.print(f"\n[green]✓ CSV:[/]   {paths['csv']}")
    console.print(f"[green]✓ Excel:[/] {paths['excel']}")


def cmd_review(args):
    from agents.reviewer_agent import reviewer_agent
    if args.prd_file:
        try:
            prd_content = open(args.prd_file, encoding="utf-8").read()
        except FileNotFoundError:
            console.print(f"[red]PRD file not found: {args.prd_file}[/]")
            return
    elif args.prd_text:
        prd_content = args.prd_text
    else:
        console.print("[red]Provide --prd-file or --prd-text[/]")
        return

    console.print(Panel(
        f"[bold cyan]Feature:[/] {args.feature}\n"
        f"[bold cyan]PRD:[/] {args.prd_file or 'text input'}\n"
        f"[bold cyan]Test Cases:[/] {args.tc_file or 'not provided'}",
        title="[bold]Reviewer Agent", border_style="cyan",
    ))
    report = reviewer_agent.review(
        prd_content=prd_content,
        test_cases_path=args.tc_file,
        feature=args.feature,
    )
    cov_color = "green" if report.coverage_percentage >= 80 else "yellow" if report.coverage_percentage >= 60 else "red"
    console.print(f"\n[bold]Review Summary[/]")
    console.print(f"  Requirements:    {report.total_requirements}")
    console.print(f"  Test cases:      {report.total_test_cases}")
    console.print(f"  Coverage:        [{cov_color}]{report.coverage_percentage:.0f}%[/]")
    console.print(f"  Quality score:   {report.overall_quality_score}/10")
    console.print(f"  Critical:        [red]{report.findings_critical}[/]")
    console.print(f"  Major:           [yellow]{report.findings_major}[/]")
    console.print(f"  Missing TCs:     [yellow]{len(report.missing_test_cases)}[/]")
    if report.findings_critical > 0:
        console.print(f"\n[red bold]Critical Findings:[/]")
        for f in report.detailed_findings:
            if f.get("severity") == "Critical":
                console.print(f"  [red]✗[/] {f.get('issue','')[:80]}")
                console.print(f"    [dim]→ {f.get('suggestion','')[:80]}[/]")
    if getattr(args, "export", True):
        paths = reviewer_agent.export_report(report, args.feature)
        console.print(f"\n[green]✓ Report exported:[/]")
        console.print(f"  [cyan]Excel:[/] {paths['excel']}")
        console.print(f"  [cyan]CSV:[/]   {paths['csv']}")


def cmd_debug(args):
    from agents.debug_agent import FailureContext, debug_agent
    from pathlib import Path

    test_file = args.test_file
    test_name = Path(test_file).stem if test_file else "unknown"

    console.print(Panel(
        f"[bold cyan]Test file:[/] {test_file or 'N/A'}\n"
        f"[bold cyan]Error:[/] {args.error[:120]}",
        title="[bold]Debug Agent", border_style="cyan",
    ))

    ctx = FailureContext(
        test_name=test_name,
        error_message=args.error,
        platform=getattr(args, "platform", "web"),
        location=test_file or "",
    )
    report = debug_agent.analyze(ctx)

    sev_color = {"P0": "red", "P1": "orange1", "P2": "yellow", "P3": "green"}.get(report.severity, "white")
    console.print(f"\n[bold]Debug Report[/]")
    console.print(f"  Severity:   [{sev_color}]{report.severity}[/]")
    console.print(f"  Title:      {report.title}")
    console.print(f"  Bug type:   {report.bug_type}")
    console.print(f"  Root cause: {report.root_cause}")
    console.print(f"  Component:  {report.affected_component}")
    console.print(f"  Action:     {report.recommended_action}")
    if report.steps_to_reproduce:
        console.print(f"\n  [bold]Steps to Reproduce:[/]")
        for i, step in enumerate(report.steps_to_reproduce, 1):
            console.print(f"    {i}. {step}")
    if report.suggested_fix:
        console.print(f"\n  [bold]Suggested Fix:[/] {report.suggested_fix}")
    if report.integrity_notes:
        console.print(f"\n  [bold yellow]Integrity Notes:[/]")
        for note in report.integrity_notes:
            console.print(f"    - {note}")


def cmd_approve(args):
    """Manually resolve a pending async approval from the terminal."""
    from core.workflows.pending_approvals import PendingApprovalStore
    store   = PendingApprovalStore()
    payload = store.load(args.id)

    if payload is None:
        console.print(f"[red]✗ Approval not found or expired:[/] {args.id}")
        return

    feature    = payload.get("feature", "N/A")
    ticket     = payload.get("ticket_id", "N/A")
    confidence = payload.get("confidence", 0.0)
    created    = payload.get("created_at", "N/A")
    expires    = payload.get("expires_at", "N/A")

    console.print(Panel(
        f"[bold cyan]ID:[/]         {args.id}\n"
        f"[bold cyan]Ticket:[/]     {ticket}\n"
        f"[bold cyan]Feature:[/]    {feature}\n"
        f"[bold cyan]Confidence:[/] {confidence:.0%}\n"
        f"[bold cyan]Created:[/]    {created}\n"
        f"[bold cyan]Expires:[/]    {expires}",
        title="[bold]Pending Approval", border_style="cyan",
    ))

    decision = args.decision
    ok = store.resolve(args.id, decision, reason=args.reason or "")
    if ok:
        color = "green" if decision == "approve" else "red"
        symbol = "✅" if decision == "approve" else "❌"
        console.print(f"\n[{color}]{symbol} {decision.upper()}ED:[/] {args.id}")
        if args.reason:
            console.print(f"  Reason: {args.reason}")
    else:
        console.print(f"[red]✗ Failed to resolve[/] — may already be expired or resolved")


def cmd_pending(args):
    """List all pending async approvals not yet expired."""
    from core.workflows.pending_approvals import PendingApprovalStore
    from rich.table import Table
    from rich import box

    store   = PendingApprovalStore()
    cleaned = store.cleanup_expired()
    items   = store.list_pending()

    if cleaned:
        console.print(f"[dim]Cleaned up {cleaned} expired record(s)[/]\n")

    if not items:
        console.print("[yellow]No pending approvals[/]")
        return

    table = Table(
        title=f"Pending Approvals ({len(items)})",
        border_style="cyan",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("ID",         style="dim",   width=28)
    table.add_column("Ticket",     style="cyan",  width=12)
    table.add_column("Feature",    style="white", width=30)
    table.add_column("Confidence", style="yellow",width=11)
    table.add_column("Created",    style="dim",   width=20)
    table.add_column("Expires",    style="red",   width=20)

    for item in items:
        conf = item.get("confidence", 0.0)
        conf_emoji = "🟢" if conf >= 0.85 else "🟡" if conf >= 0.60 else "🔴"
        table.add_row(
            item.get("approval_id", ""),
            item.get("ticket_id", "N/A"),
            item.get("feature", "N/A")[:30],
            f"{conf_emoji} {conf:.0%}",
            item.get("created_at", "")[:19],
            item.get("expires_at", "")[:19],
        )

    console.print(table)
    console.print(
        "\n[dim]Resolve:[/] "
        "PYTHONPATH=. ./venv/bin/python3.11 cli.py approve --id <ID> --decision approve|reject"
    )


def cmd_requirements(args):
    from agents.requirements_agent import requirements_agent
    # Auto-fetch dari Jira menggunakan jira_client
    if args.jira_story and not getattr(args, "description", None):
        try:
            from mcp_tools.jira_client.jira_client import jira_client
            issue = jira_client.get_issue(args.jira_story)

            if not getattr(args, "feature", None) or args.feature == args.jira_story:
                args.feature = f"{issue['key']}: {issue['summary']}"

            context = issue["description"][:800]
            if issue["subtasks"]:
                context += "\n\nSUBTASKS:"
                for st in issue["subtasks"]:
                    context += f"\n  - [{st['key']}] {st['summary']} ({st['status']})"
                    if st["description"]:
                        context += f"\n    {st['description'][:150]}"
            args.description = context[:1500]

            if not getattr(args, "ac", None):
                args.ac = issue["acceptance_criteria"][:15]

            console.print(f"[green]✓ Jira fetched:[/] {issue['summary'][:60]}")
            console.print(f"[green]✓ Subtasks:[/] {len(issue['subtasks'])} | AC: {len(issue['acceptance_criteria'])}")

            # Extract images if available
            import os
            if os.getenv("ANTHROPIC_API_KEY"):
                try:
                    import asyncio as _asyncio
                    img_desc = _asyncio.get_event_loop().run_until_complete(
                        jira_client.describe_images_with_llm(args.jira_story)
                    )
                    if img_desc:
                        args.description += f"\n\nUI SCREENSHOTS:\n{img_desc}"
                        console.print(f"[green]✓ Images:[/] extracted and described via vision LLM")
                except Exception as e:
                    console.print(f"[yellow]⚠ Image extraction failed:[/] {e}")
            else:
                # Check attachments without vision
                attachments = jira_client.get_attachments(args.jira_story)
                images = [a for a in attachments if a["mimeType"].startswith("image/")]
                if images:
                    img_names = ", ".join(a["filename"] for a in images[:3])
                    console.print(f"[yellow]⚠ {len(images)} images found:[/] {img_names} — set ANTHROPIC_API_KEY for vision extraction")
        except Exception as e:
            console.print(f"[yellow]⚠ Jira fetch failed:[/] {e}")

    if args.jira_story:
        console.print(Panel(
            f"[bold cyan]Story:[/] {args.jira_story}\n"
            f"Fetch → Extract AC → Generate tickets → Create in Jira",
            title="[bold]Requirements Agent", border_style="cyan",
        ))
        result = requirements_agent.run_from_jira(args.jira_story)
    elif args.feature and args.text:
        console.print(Panel(
            f"[bold cyan]Feature:[/] {args.feature}",
            title="[bold]Requirements Agent", border_style="cyan",
        ))
        result = requirements_agent.run_from_text(
            feature=args.feature,
            story_text=args.text,
            parent_key=args.parent_key or "",
        )
    else:
        console.print("[red]Provide --jira-story or --feature + --text[/]")
        return
    console.print(f"\n[green]✓ AC Extracted:[/] {result.get('ac_count', 0)} criteria")
    if result.get("ambiguities"):
        console.print(f"\n[yellow]⚠ Ambiguities ({len(result['ambiguities'])}):[/]")
        for a in result["ambiguities"][:3]:
            console.print(f"  [dim]→[/] {a.get('description','')[:80]}")
            console.print(f"    [dim]Q: {a.get('suggested_question','')[:80]}[/]")
    if result.get("tickets_created"):
        console.print(f"\n[green]✓ Tickets created ({len(result['tickets_created'])}):[/]")
        for t in result["tickets_created"]:
            console.print(f"  [cyan]{t['key']}[/] — {t['title'][:60]}")
    if result.get("ticket_drafts"):
        console.print(f"\n[cyan]Drafts ({len(result['ticket_drafts'])}) — run: python cli.py drafts --jira-story {args.jira_story or args.feature}[/]")
    if result.get("missing_data"):
        console.print(f"\n[red]Missing data:[/]")
        for m in result["missing_data"][:3]:
            console.print(f"  [dim]→[/] {m}")


def cmd_show_drafts(args):
    from agents.requirements_agent import requirements_agent
    from rich.table import Table
    from rich import box
    import csv
    from datetime import datetime
    from pathlib import Path

    console.print(Panel(
        f"[bold cyan]Story:[/] {args.jira_story}\n"
        f"Fetch → Extract AC → Preview drafts (no Jira create)",
        title="[bold]Draft Preview", border_style="cyan",
    ))
    result = requirements_agent.run_from_jira(args.jira_story)
    drafts = result.get("ticket_drafts", [])

    if not drafts:
        console.print("[yellow]No drafts generated[/]")
        return

    console.print(f"\n[green]✓ {len(drafts)} ticket drafts[/]\n")
    table = Table(title=f"Drafts — {result.get('story_key')}",
                  border_style="cyan", box=box.ROUNDED, show_lines=True)
    table.add_column("#",        style="dim",    width=4)
    table.add_column("Title",    style="white",  width=55)
    table.add_column("Type",     style="yellow", width=12)
    table.add_column("Platform", style="green",  width=10)
    table.add_column("Priority", style="red",    width=8)
    table.add_column("Auto?",    style="cyan",   width=6)
    for i, d in enumerate(drafts, 1):
        table.add_row(str(i), d.get("title","")[:55], d.get("test_type",""),
                      d.get("platform",""), d.get("priority",""),
                      "✓" if d.get("automation_candidate") else "✗")
    console.print(table)

    if args.detail and args.detail <= len(drafts):
        d     = drafts[args.detail - 1]
        steps = "\n".join(f"  {s}" for s in d.get("steps", []))
        edges = "\n".join(f"  • {e}" for e in d.get("edge_cases", []))
        console.print(f"\n[bold cyan]Detail — Draft #{args.detail}[/]")
        console.print(Panel(
            f"[bold]Title:[/] {d.get('title')}\n\n"
            f"[bold]Precondition:[/]\n{d.get('precondition','N/A')}\n\n"
            f"[bold]Steps:[/]\n{steps}\n\n"
            f"[bold]Expected:[/]\n{d.get('expected','N/A')}\n\n"
            f"[bold]Edge Cases:[/]\n{edges}",
            border_style="cyan",
        ))

    if args.export:
        path = Path(f"reports/excel/drafts_{args.jira_story.lower()}_{datetime.now().strftime('%Y%m%d')}.csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "title","test_type","platform","priority","precondition",
                "steps","expected","edge_cases","automation_candidate","source_ac_id",
            ])
            writer.writeheader()
            for d in drafts:
                writer.writerow({
                    "title":                d.get("title",""),
                    "test_type":            d.get("test_type",""),
                    "platform":             d.get("platform",""),
                    "priority":             d.get("priority",""),
                    "precondition":         d.get("precondition",""),
                    "steps":                " | ".join(d.get("steps",[])),
                    "expected":             d.get("expected",""),
                    "edge_cases":           " | ".join(d.get("edge_cases",[])),
                    "automation_candidate": d.get("automation_candidate",False),
                    "source_ac_id":         d.get("source_ac_id",""),
                })
        console.print(f"\n[green]✓ Exported:[/] {path}")

    if result.get("ambiguities"):
        console.print(f"\n[yellow]⚠ Ambiguities ({len(result['ambiguities'])}):[/]")
        for a in result["ambiguities"]:
            console.print(f"  [dim]→[/] {a.get('description','')[:80]}")
            console.print(f"    [dim]Q: {a.get('suggested_question','')[:80]}[/]")


async def cmd_bot_start(args):
    from core.telegram_bot import telegram_bot
    from core.workflows.approval_workflow import review_queue
    telegram_bot.set_review_queue(review_queue)
    if args.mode == "polling":
        console.print("[cyan]Starting bot in polling mode...[/]")
        await telegram_bot.start_polling()
        await asyncio.Event().wait()
    elif args.mode == "webhook":
        if not args.ngrok_url:
            console.print("[red]--ngrok-url required[/]")
            sys.exit(1)
        await telegram_bot.start_webhook(webhook_url=args.ngrok_url, port=8000)



async def cmd_pipeline_batch(args):
    """Run pipeline for each ticket in --tickets and print a combined summary."""
    tickets = [t.strip() for t in args.tickets.split(",") if t.strip()]
    console.print(f"\n[bold cyan]Batch Pipeline — {len(tickets)} stories[/]")
    console.print(f"  PRD: {args.prd_url or 'N/A'}\n")

    results = []
    for i, ticket in enumerate(tickets, 1):
        console.rule(f"[bold cyan][{i}/{len(tickets)}] {ticket}[/]")
        # Reuse cmd_pipeline by temporarily setting args.ticket
        args.ticket  = ticket
        args.feature = None   # force re-derive from Jira each iteration
        try:
            await cmd_pipeline(args)
            results.append({"ticket": ticket, "status": "ok"})
        except SystemExit:
            results.append({"ticket": ticket, "status": "error"})
        except Exception as exc:
            console.print(f"[red]✗ {ticket} failed:[/] {exc}")
            results.append({"ticket": ticket, "status": "error", "error": str(exc)})

    console.rule("[bold]Batch Summary[/]")
    ok  = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] != "ok"]
    console.print(f"  [green]✓ Success:[/] {len(ok)}/{len(tickets)}")
    if err:
        console.print(f"  [red]✗ Failed:[/]  {len(err)}/{len(tickets)}")
        for r in err:
            console.print(f"    • {r['ticket']}: {r.get('error','')[:80]}")


async def cmd_pipeline(args):
    from core.automation_readiness import load_automation_evidence
    from orchestrator.pipeline import run_pipeline

    # Auto-derive feature from Jira ticket when --feature not given
    if not args.feature and args.ticket:
        try:
            from mcp_tools.jira_client.jira_client import jira_client
            issue = jira_client.get_issue(args.ticket)
            args.feature = f"{issue['key']}: {issue['summary']}"
            console.print(f"[green]✓ Jira:[/] {args.feature}")
        except Exception as e:
            args.feature = args.ticket
            console.print(f"[yellow]⚠ Jira fetch failed, using ticket as feature:[/] {e}")
    elif not args.feature:
        console.print("[red]Provide --feature or --ticket[/]")
        sys.exit(1)

    try:
        automation_evidence = load_automation_evidence(args.automation_evidence)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Automation evidence error:[/] {e}")
        sys.exit(1)

    console.print(Panel(
        f"[bold cyan]Feature:[/] {args.feature}\n"
        f"[bold cyan]Platforms:[/] {args.platform}\n"
        f"[bold cyan]Ticket:[/] {args.ticket or 'N/A'}\n"
        f"[bold cyan]PRD:[/] {args.prd_url or 'N/A'}\n"
        f"[bold cyan]Subtasks:[/] {'included' if args.include_subtasks else 'not included'}\n"
        f"[bold cyan]Evidence:[/] {args.automation_evidence or 'N/A'}\n"
        f"[bold cyan]URL:[/] {args.url or 'N/A'}",
        title="[bold]QA Pipeline — Phase 9", border_style="cyan",
    ))

    platforms = [p.strip() for p in args.platform.split(",")]
    final = await run_pipeline(
        feature=args.feature,
        platforms=platforms,
        ticket_id=args.ticket or None,
        story_text=args.story or args.feature,
        feature_url=args.url or None,
        prd_url=args.prd_url or None,
        include_subtasks=args.include_subtasks,
        automation_evidence=automation_evidence,
        github_pr_number=getattr(args, "github_pr", None),
    )

    console.print(f"\n[bold]Pipeline Complete[/]")
    case_review = final.get("case_review") or {}
    try:
        coverage = float(
            final.get("coverage_percentage")
            if final.get("coverage_percentage") is not None
            else case_review.get("coverage_percentage") or 0.0
        )
    except (TypeError, ValueError):
        coverage = 0.0
    console.print(f"  Coverage:   [cyan]{coverage:.0f}%[/]")
    console.print(f"  Test cases: {len(final.get('test_cases') or [])}")
    console.print(f"  Case review: {case_review.get('status', 'N/A')}")
    readiness = final.get("automation_readiness") or {}
    console.print(f"  Automation readiness: {readiness.get('status', 'N/A')}")
    if case_review:
        findings = case_review.get("findings") or {}
        raw_score = case_review.get("quality_score_raw")
        score_text = str(case_review.get("quality_score", "N/A"))
        if raw_score not in (None, case_review.get("quality_score")):
            score_text = f"{score_text} (raw: {raw_score})"
        console.print(f"  Review score: [cyan]{score_text}[/]")
        console.print(
            "  Findings:    "
            f"critical={findings.get('critical', 'N/A')}, "
            f"major={findings.get('major', 'N/A')}, "
            f"minor={findings.get('minor', 'N/A')}"
        )
        missing_cases = case_review.get("missing_test_cases") or []
        if missing_cases:
            console.print("  Missing cases:")
            for item in missing_cases[:5]:
                console.print(f"    - {str(item)[:120]}")
        clarifications = case_review.get("prd_clarifications") or []
        if clarifications:
            console.print("  PRD clarifications:")
            for item in clarifications[:3]:
                console.print(f"    - {str(item)[:120]}")
    console.print(f"  Bugs found: {len(final.get('bug_reports') or [])}")
    console.print(f"  Gaps:       {len(final.get('coverage_gaps') or [])}")
    missing_evidence = readiness.get("missing_evidence") or []
    if missing_evidence:
        console.print("  Missing automation evidence:")
        for item in missing_evidence[:5]:
            console.print(
                f"    - {item.get('platform')}/{item.get('type')}: "
                f"{item.get('message')}"
            )
    if final.get('testcase_exports'):
        for name, path in final['testcase_exports'].items():
            console.print(f"  {name.upper()}:      [dim]{path}[/]")
    if final.get('draft_exports'):
        for name, path in final['draft_exports'].items():
            console.print(f"  DRAFT {name.upper()}: [dim]{path}[/]")
    if final.get('gap_report_path'):
        console.print(f"  Gap report: [dim]{final['gap_report_path']}[/]")

def build_parser():
    parser  = argparse.ArgumentParser(prog="cli.py", description="QA AI Framework CLI")
    sub     = parser.add_subparsers(dest="command")

    run = sub.add_parser("run")
    run.add_argument("--feature",     required=True)
    run.add_argument("--description", default="")
    run.add_argument("--platform",    default="web")
    run.add_argument("--ac",          nargs="*")

    gen     = sub.add_parser("generate")
    gen_sub = gen.add_subparsers(dest="artifact")

    tc = gen_sub.add_parser("testcase")
    tc.add_argument("--feature",     required=True)
    tc.add_argument("--description", default="")
    tc.add_argument("--platform",    default="web")
    tc.add_argument("--ac",          nargs="*")
    tc.add_argument("--jira-story",  default=None)
    tc.add_argument("--export",      action="store_true")

    code = gen_sub.add_parser("code")

    batch = gen_sub.add_parser("batch")
    batch.add_argument("--jira-story", required=True)
    batch.add_argument("--platform", action="append", default=["web"])
    batch.add_argument("--export", action="store_true")
    code.add_argument("--feature",     required=True)
    code.add_argument("--description", default="")
    code.add_argument("--platform",    default="web")
    code.add_argument("--ac",          nargs="*")
    code.add_argument("--automation-evidence", default=None, help="Path to JSON file with actual execution evidence for code generation")

    exp = sub.add_parser("export")
    exp.add_argument("--feature",     required=True)
    exp.add_argument("--description", default="")
    exp.add_argument("--platform",    default="web")
    exp.add_argument("--ac",          nargs="*")

    rev = sub.add_parser("review")
    rev.add_argument("--feature",   required=True)
    rev.add_argument("--prd-file",  default=None, dest="prd_file")
    rev.add_argument("--prd-text",  default=None, dest="prd_text")
    rev.add_argument("--tc-file",   default=None, dest="tc_file")
    rev.add_argument("--no-export", action="store_false", dest="export")

    dbg = sub.add_parser("debug", help="Analyze a test failure with the debug agent")
    dbg.add_argument("--test-file", default=None, dest="test_file", help="Path to the failing test file")
    dbg.add_argument("--error",     required=True, help="Error message from the test failure")
    dbg.add_argument("--platform",  default="web", help="Platform (web/android/api)")

    app = sub.add_parser("approve", help="Manually resolve a pending async approval")
    app.add_argument("--id",       required=True, help="Approval ID (e.g. HM-516_1234567890)")
    app.add_argument("--decision", choices=["approve", "reject"], default="approve",
                     help="Decision to apply (default: approve)")
    app.add_argument("--reason",   default="", help="Optional reason/notes")

    sub.add_parser("pending", help="List all pending async approvals")

    req = sub.add_parser("requirements")
    req.add_argument("--jira-story",  default=None, dest="jira_story")
    req.add_argument("--feature",     default=None)
    req.add_argument("--text",        default=None)
    req.add_argument("--parent-key",  default=None, dest="parent_key")

    drafts_p = sub.add_parser("drafts", help="Preview ticket drafts without creating in Jira")
    drafts_p.add_argument("--jira-story", required=True, dest="jira_story")
    drafts_p.add_argument("--detail",     type=int, default=None)
    drafts_p.add_argument("--export",     action="store_true")

    bot     = sub.add_parser("bot")
    bot_sub = bot.add_subparsers(dest="bot_action")
    bs      = bot_sub.add_parser("start")
    bs.add_argument("--mode",      choices=["polling","webhook"], default="polling")
    bs.add_argument("--ngrok-url", default=None)

    sub.add_parser("smoke", help="Verify LLM connection")

    pip = sub.add_parser("pipeline", help="Run full Phase 9 orchestrated pipeline")
    pip.add_argument("--feature",  default=None, help="Feature name (auto-derived from --ticket if omitted)")
    pip.add_argument("--platform", default="web")
    pip.add_argument("--ticket",   default=None, help="Single Jira story ID")
    pip.add_argument("--tickets",  default=None, help="Comma-separated Jira story IDs — runs pipeline per story")
    pip.add_argument("--story",    default=None, help="Raw story text")
    pip.add_argument("--prd-url",  default=None, help="Confluence PRD URL")
    pip.add_argument("--include-subtasks", action="store_true", help="Include Jira subtasks/developer details in source intake")
    pip.add_argument("--automation-evidence", default=None, help="Path to JSON file with actual API/web/mobile execution evidence for codegen")
    pip.add_argument("--url",      default=None, help="Implemented feature URL")
    pip.add_argument("--github-pr", default=None, type=int, help="GitHub PR number — post QA summary as PR comment")

    return parser



async def cmd_generate_testcase_batch_by_scenario(args):
    """Generate 150+ test cases per scenario from Jira — no duplication."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env")
    from core.llm_client import llm_client, ModelTier
    from core.prompt_manager import prompt_manager
    from datetime import datetime
    from mcp_tools.jira_client.jira_client import jira_client as jc
    import json, os

    # Fetch Jira issue
    console.print(f"[cyan]Fetching {args.jira_story} from Jira...[/]")
    issue = jc.get_issue(args.jira_story)
    desc = issue["description"]

    # Split description into scenarios
    import re
    scenario_blocks = re.split(r"(?=Scenario \d+:)", desc)
    scenario_blocks = [s.strip() for s in scenario_blocks if s.strip() and "Scenario" in s]

    if not scenario_blocks:
        scenario_blocks = [desc]  # fallback — treat as one block

    console.print(f"[green]✓ Found {len(scenario_blocks)} scenarios to process[/]")

    all_scenarios = []
    existing_ids = []
    template = prompt_manager.get("test_case_gen")

    for idx, scenario_block in enumerate(scenario_blocks, 1):
        scenario_title = scenario_block.split("\n")[0][:60]
        console.print(f"  [yellow]→[/] [{idx}/{len(scenario_blocks)}] {scenario_title}")

        start_id = len(all_scenarios) + 1
        prompt = template.format(
            feature=f"{args.jira_story}: {issue['summary']}",
            description=scenario_block[:1000],
            platforms=", ".join(getattr(args, "platform", ["web"])),
            acceptance_criteria="\n".join(f"- {ac}" for ac in issue["acceptance_criteria"][:8]) or "Not provided",
            past_context=f"Already generated IDs: {', '.join(existing_ids[-10:]) if existing_ids else 'None'}",
            date=datetime.now().strftime("%Y-%m-%d")
        )

        try:
            response = llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                agent_name="batch_scenario",
                tier=ModelTier.STANDARD
            )

            if not response.content:
                console.print(f"  [red]✗[/] Empty response")
                continue

            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            scenarios = data.get("scenarios", [])

            added = 0
            for s in scenarios:
                case_id = s.get("case_id", f"TC-{len(all_scenarios)+1:03d}")
                if case_id not in existing_ids:
                    # Prefix with scenario number for clarity
                    s["case_id"] = f"S{idx}-{case_id}"
                    all_scenarios.append(s)
                    existing_ids.append(s["case_id"])
                    added += 1

            console.print(f"  [green]✓[/] +{added} cases (total: {len(all_scenarios)})")

        except Exception as e:
            console.print(f"  [red]✗[/] Error: {e}")
            continue

    # Display summary
    console.print(f"\n[bold green]✓ Total: {len(all_scenarios)} unique test cases across {len(scenario_blocks)} scenarios[/]")

    # Auto-create Jira QA subtask
    try:
        subtask_key = jc.create_qa_subtask(
            parent_key=args.jira_story,
            test_cases=all_scenarios,
            feature=issue["summary"]
        )
        if subtask_key:
            console.print(f"[green]✓ Jira QA subtask created:[/] {subtask_key} → linked to {args.jira_story}")
            console.print(f"  [dim]https://thehono.atlassian.net/browse/{subtask_key}[/]")
        else:
            console.print(f"[yellow]⚠ Jira subtask creation failed[/]")
    except Exception as e:
        console.print(f"[yellow]⚠ Jira subtask error:[/] {e}")

    # Show table
    table = Table(title=f"Batch Test Cases — {args.jira_story}", border_style="cyan", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Scenario", style="white", width=30)
    table.add_column("Steps", style="cyan", width=45)
    table.add_column("Priority", style="red", width=8)

    for s in all_scenarios[:50]:  # show first 50 in table
        table.add_row(
            s.get("case_id", ""),
            s.get("title", "")[:30],
            s.get("steps", "")[:80],
            s.get("priority", ""),
        )

    console.print(table)
    if len(all_scenarios) > 50:
        console.print(f"[dim]... and {len(all_scenarios)-50} more (see export)[/]")

    # Export
    os.makedirs("reports/test_cases", exist_ok=True)
    output_file = f"reports/test_cases/{args.jira_story}_full_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "jira_story": args.jira_story,
            "summary": issue["summary"],
            "total": len(all_scenarios),
            "scenarios_processed": len(scenario_blocks),
            "generated_at": datetime.now().isoformat(),
            "test_cases": all_scenarios
        }, f, indent=2)
    console.print(f"\n[green]✓ JSON exported:[/] {output_file}")

    # Also export CSV/Excel via excel_writer
    if getattr(args, "export", False):
        try:
            from skills.reporting.excel_writer import excel_writer
            from core.agent_contracts import (
                TestCaseAgentOutput, ScenarioSchema, TestStep,
                TestType, Platform, Priority
            )
            priority_map = {"P0": "high", "P1": "medium", "P2": "low"}
            platform_map = {"WEB": "web", "API": "api", "MOBILE": "android", "ANDROID": "android"}

            schemas = []
            for s in all_scenarios:
                try:
                    steps_raw = s.get("steps", "")
                    steps = [TestStep(step_number=i+1, action=line, expected="")
                             for i, line in enumerate(steps_raw.split("\n")) if line.strip()]
                    if not steps:
                        steps = [TestStep(step_number=1, action=steps_raw, expected="")]

                    p_raw = s.get("priority", "P1").upper()
                    p_val = priority_map.get(p_raw, "medium")
                    pl_raw = s.get("platform", "WEB").upper()
                    pl_val = platform_map.get(pl_raw, "web")
                    tt = s.get("test_type", "functional").lower()
                    valid_types = ["smoke", "functional", "regression", "e2e", "negative", "boundary"]
                    if tt not in valid_types:
                        tt = "functional"

                    regression_risk_area = s.get("regression_risk_area", [])
                    if isinstance(regression_risk_area, str):
                        regression_risk_area = [regression_risk_area]

                    schemas.append(ScenarioSchema(
                        scenario_id=s.get("case_id", "TC-001"),
                        name=s.get("title", ""),
                        precondition=s.get("preconditions", ""),
                        steps=steps,
                        expected_result=s.get("expected_result", ""),
                        test_data={},
                        tags=s.get("tags", []),
                        test_type=TestType(tt),
                        platforms=[Platform(pl_val)],
                        priority=Priority(p_val),
                        regression_candidate=bool(s.get("regression_candidate", tt == "regression")),
                        regression_risk_area=regression_risk_area,
                    ))
                except Exception:
                    continue

            output = TestCaseAgentOutput(
                feature=f"{args.jira_story}: {issue['summary']}",
                model_used="batch-generation",
                scenarios=schemas,
                coverage_summary=f"{len(schemas)} cases across {len(scenario_blocks)} Jira scenarios",
                total_scenarios=len(schemas),
                prompt_version="2.0.0",
            )
            paths = excel_writer.write_both(output)
            console.print(f"[green]✓ CSV:[/] {paths['csv']}")
            console.print(f"[green]✓ Excel:[/] {paths['excel']}")
        except Exception as e:
            console.print(f"[yellow]⚠ Excel export failed:[/] {e}")



def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command == "run":
        asyncio.run(cmd_run(args))
    elif args.command == "generate":
        if args.artifact == "code":
            cmd_generate_code(args)
        elif args.artifact == "testcase":
            asyncio.run(cmd_generate_testcase(args))
        elif args.artifact == "batch":
            asyncio.run(cmd_generate_testcase_batch_by_scenario(args))
        else:
            parser.print_help()
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "review":
        cmd_review(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "approve":
        cmd_approve(args)
    elif args.command == "pending":
        cmd_pending(args)
    elif args.command == "requirements":
        cmd_requirements(args)
    elif args.command == "drafts":
        cmd_show_drafts(args)
    elif args.command == "bot":
        if args.bot_action == "start":
            asyncio.run(cmd_bot_start(args))
        else:
            parser.print_help()
    elif args.command == "pipeline":
        if getattr(args, "tickets", None):
            asyncio.run(cmd_pipeline_batch(args))
        else:
            asyncio.run(cmd_pipeline(args))
    elif args.command == "smoke":
        asyncio.run(cmd_smoke(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


def _extract_adf_text(node) -> str:
    """Extract plain text from Atlassian Document Format (ADF) recursively."""
    text = ""
    if isinstance(node, dict):
        if node.get("type") == "text":
            text += node.get("text", "")
        for child in node.get("content", []):
            text += _extract_adf_text(child)
        if node.get("type") in ["paragraph", "listItem", "bulletList", "heading"]:
            text += "\n"
    return text
