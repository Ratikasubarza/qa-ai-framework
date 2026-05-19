"""
Demo runner for TestPlanAgent — no Jira, no live API key, no OpenRouter needed.

Root cause of previous hangs: openai==1.35.0 import itself is slow (SSL cert
loading, httpx transport init), and its OpenAI() constructor attempts a
network call. Fix: inject a MagicMock into sys.modules['openai'] BEFORE any
import that would trigger it — the real package never loads at all.

Run:
    PYTHONPATH=. ./venv/bin/python3.11 run_test_plan_demo.py
"""
import sys
import os
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── 1. Env vars for pydantic-settings (must precede settings import) ──────────
_MOCK_ENV = {
    "OPENROUTER_API_KEY":        "mock-key",
    "OPENROUTER_BASE_URL":       "https://openrouter.ai/api/v1",
    "JIRA_BASE_URL":             "https://mock.atlassian.net",
    "JIRA_EMAIL":                "mock@test.com",
    "JIRA_TOKEN":                "mock-token",
    "JIRA_PROJECT_KEY":          "QA",
    "TELEGRAM_BOT_TOKEN":        "123456789:mock",
    "TELEGRAM_QA_LEADS_CHAT_ID": "-100000001",
    "TELEGRAM_QA_TEAM_CHAT_ID":  "-100000002",
    "TELEGRAM_QA_OPS_CHAT_ID":   "-100000003",
    "TELEGRAM_QA_BUGS_CHAT_ID":  "-100000004",
}
for _k, _v in _MOCK_ENV.items():
    os.environ.setdefault(_k, _v)

# ── 2. Inject mock openai into sys.modules BEFORE any framework import ─────────
# Prevents `from openai import OpenAI` from triggering the real package
# (openai==1.35.0 triggers SSL/httpx initialisation and a network call
#  in OpenAI.__init__ that hangs indefinitely without internet access).
_mock_openai_mod = MagicMock()
_mock_openai_mod.OpenAI = MagicMock(return_value=MagicMock())
sys.modules.setdefault("openai",              _mock_openai_mod)
sys.modules.setdefault("openai.types",        MagicMock())
sys.modules.setdefault("openai.types.chat",   MagicMock())
sys.modules.setdefault("openai._client",      MagicMock())

# ── 3. Now safe: import framework ─────────────────────────────────────────────
from agents.test_plan_agent import (       # noqa: E402
    TestPlanAgent,
    _DT_PATTERNS, _PAIRWISE_PARAMS, _BVA_KEYWORDS, _ST_KEYWORDS,
)
from core.llm_client import llm_client     # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Mock requirements — exactly as specified
# ─────────────────────────────────────────────────────────────────────────────
REQUIREMENTS = {
    "ticket_id": "TEST-001",
    "feature_name": "cms_approve",
    "acceptance_criteria": [
        "If user is admin AND account is pending AND documents are verified THEN approve the account",
        "If user is viewer role THEN return 403 Forbidden",
        "If documents are missing THEN reject with reason",
        "Account status must transition: pending → approved or pending → rejected",
        "Approved account password must be set minimum 8 characters maximum 32 characters",
    ],
    "description": (
        "CMS admin workflow for approving or rejecting user registrations. "
        "Based on role, account status, and document completeness combination."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# Realistic mock LLM response — matches expected techniques for cms_approve
# ─────────────────────────────────────────────────────────────────────────────
MOCK_LLM_JSON = {
    "techniques_used": [
        "equivalence_partitioning",
        "error_guessing",
        "decision_table",
        "boundary_value_analysis",
        "state_transition",
    ],
    "technique_rationale": {
        "equivalence_partitioning": (
            "Always included as baseline. Partitions: role (admin/viewer/other), "
            "account status (pending/active/rejected), documents (verified/missing). "
            "One test case per partition."
        ),
        "error_guessing": (
            "Always included. Covers: null user_id, duplicate approval, "
            "session expiry mid-approval, concurrent approve+reject race, "
            "XSS in rejection reason, SQL injection in reason field."
        ),
        "decision_table": (
            "AC-1: 'If admin AND pending AND docs_verified THEN approve' — "
            "three interacting boolean conditions yield 8 rule columns. "
            "Description also states 'based on role, account status, and "
            "document completeness combination' — explicit multi-condition logic."
        ),
        "boundary_value_analysis": (
            "AC-5: 'minimum 8 characters maximum 32 characters' is an explicit "
            "numeric range. BVA generates 7 test cases: 7(min-1), 8(min), "
            "9(min+1), 20(nominal), 31(max-1), 32(max), 33(max+1)."
        ),
        "state_transition": (
            "AC-4: 'Account status must transition: pending → approved or "
            "pending → rejected' is a named state machine. Tests both valid "
            "transitions and invalid ones (approved→pending, rejected→approved)."
        ),
    },
    "scenarios": [
        {
            "scenario_id": "TC-001",
            "scenario_name": "Admin approves account — all conditions met (DT Rule 1: Y/Y/Y → APPROVE)",
            "technique": "decision_table",
            "type": "happy_path",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": [
                "CMS admin is authenticated",
                "Target account status is PENDING",
                "All required documents are VERIFIED",
            ],
            "inputs": {"role": "admin", "account_status": "pending", "documents_verified": True},
            "expected_outcome": "HTTP 200 — account transitions to APPROVED, welcome email sent",
            "risk_level": "high",
            "tags": ["smoke", "regression", "decision_table"],
        },
        {
            "scenario_id": "TC-002",
            "scenario_name": "Admin rejects — documents missing (DT Rule 2: Y/Y/N → REJECT)",
            "technique": "decision_table",
            "type": "negative",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": [
                "CMS admin is authenticated",
                "Account status PENDING",
                "Documents NOT uploaded",
            ],
            "inputs": {"role": "admin", "account_status": "pending", "documents_verified": False},
            "expected_outcome": "HTTP 400 — rejection reason required, status transitions to REJECTED",
            "risk_level": "high",
            "tags": ["regression", "decision_table"],
        },
        {
            "scenario_id": "TC-003",
            "scenario_name": "Viewer role gets 403 — regardless of account/docs state (DT Rules 5–8)",
            "technique": "decision_table",
            "type": "negative",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Viewer-role user authenticated", "Target account PENDING"],
            "inputs": {"role": "viewer", "account_status": "pending", "documents_verified": True},
            "expected_outcome": "HTTP 403 Forbidden — account status unchanged",
            "risk_level": "high",
            "tags": ["regression", "security"],
        },
        {
            "scenario_id": "TC-004",
            "scenario_name": "State: PENDING → APPROVED (valid transition)",
            "technique": "state_transition",
            "type": "state_transition",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account PENDING", "Docs verified"],
            "inputs": {"from_state": "PENDING", "action": "approve"},
            "expected_outcome": "Status = APPROVED — HTTP 200",
            "risk_level": "high",
            "tags": ["regression", "state_transition"],
        },
        {
            "scenario_id": "TC-005",
            "scenario_name": "State: PENDING → REJECTED (valid transition)",
            "technique": "state_transition",
            "type": "state_transition",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account PENDING"],
            "inputs": {"from_state": "PENDING", "action": "reject", "reason": "Missing ID"},
            "expected_outcome": "Status = REJECTED — HTTP 200",
            "risk_level": "high",
            "tags": ["regression", "state_transition"],
        },
        {
            "scenario_id": "TC-006",
            "scenario_name": "State: APPROVED → PENDING (invalid — must return 409)",
            "technique": "state_transition",
            "type": "negative",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account is APPROVED"],
            "inputs": {"from_state": "APPROVED", "action": "reset"},
            "expected_outcome": "HTTP 409 Conflict — reverse transition blocked",
            "risk_level": "high",
            "tags": ["regression", "state_transition"],
        },
        {
            "scenario_id": "TC-007",
            "scenario_name": "State: REJECTED → APPROVED (invalid — must return 409)",
            "technique": "state_transition",
            "type": "negative",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account is REJECTED"],
            "inputs": {"from_state": "REJECTED", "action": "approve"},
            "expected_outcome": "HTTP 409 Conflict — cannot approve a rejected account",
            "risk_level": "medium",
            "tags": ["regression", "state_transition"],
        },
        {
            "scenario_id": "TC-008",
            "scenario_name": "BVA: password 7 chars (min−1) — rejected",
            "technique": "boundary_value_analysis",
            "type": "boundary",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Account just approved"],
            "inputs": {"password": "Short1!", "length": 7},
            "expected_outcome": "HTTP 400 — minimum 8 characters required",
            "risk_level": "high",
            "tags": ["boundary", "regression"],
        },
        {
            "scenario_id": "TC-009",
            "scenario_name": "BVA: password 8 chars (min exact) — accepted",
            "technique": "boundary_value_analysis",
            "type": "boundary",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Account just approved"],
            "inputs": {"password": "Valid12!", "length": 8},
            "expected_outcome": "HTTP 200 — password set successfully",
            "risk_level": "high",
            "tags": ["boundary", "smoke"],
        },
        {
            "scenario_id": "TC-010",
            "scenario_name": "BVA: password 9 chars (min+1) — accepted",
            "technique": "boundary_value_analysis",
            "type": "boundary",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Account just approved"],
            "inputs": {"password": "Valid123!", "length": 9},
            "expected_outcome": "HTTP 200 — password accepted",
            "risk_level": "medium",
            "tags": ["boundary", "regression"],
        },
        {
            "scenario_id": "TC-011",
            "scenario_name": "BVA: password 32 chars (max exact) — accepted",
            "technique": "boundary_value_analysis",
            "type": "boundary",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Account just approved"],
            "inputs": {"password": "A" * 29 + "1a!", "length": 32},
            "expected_outcome": "HTTP 200 — password accepted",
            "risk_level": "medium",
            "tags": ["boundary", "regression"],
        },
        {
            "scenario_id": "TC-012",
            "scenario_name": "BVA: password 33 chars (max+1) — rejected",
            "technique": "boundary_value_analysis",
            "type": "boundary",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Account just approved"],
            "inputs": {"password": "A" * 30 + "1a!", "length": 33},
            "expected_outcome": "HTTP 400 — maximum 32 characters allowed",
            "risk_level": "medium",
            "tags": ["boundary", "regression"],
        },
        {
            "scenario_id": "TC-013",
            "scenario_name": "EP valid: pending account with all conditions met → approved",
            "technique": "equivalence_partitioning",
            "type": "happy_path",
            "priority": "P1",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account PENDING", "Docs verified"],
            "inputs": {"partition": "valid_all_conditions"},
            "expected_outcome": "HTTP 200 — status = APPROVED",
            "risk_level": "high",
            "tags": ["regression", "ep"],
        },
        {
            "scenario_id": "TC-014",
            "scenario_name": "EP invalid: non-pending status cannot be approved",
            "technique": "equivalence_partitioning",
            "type": "negative",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account is ACTIVE (not pending)"],
            "inputs": {"partition": "invalid_status", "current_status": "active"},
            "expected_outcome": "HTTP 409 — account not in approvable state",
            "risk_level": "medium",
            "tags": ["regression", "ep"],
        },
        {
            "scenario_id": "TC-015",
            "scenario_name": "Error guessing: concurrent approve + reject same account (race)",
            "technique": "error_guessing",
            "type": "edge_case",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Two admin sessions", "Account PENDING"],
            "inputs": {"concurrent": ["approve", "reject"], "race_ms": 50},
            "expected_outcome": "Exactly one succeeds; second returns 409 or is idempotent",
            "risk_level": "high",
            "tags": ["edge_case", "concurrency"],
        },
        {
            "scenario_id": "TC-016",
            "scenario_name": "Error guessing: null user_id",
            "technique": "error_guessing",
            "type": "negative",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated"],
            "inputs": {"user_id": None},
            "expected_outcome": "HTTP 400 — user_id is required",
            "risk_level": "medium",
            "tags": ["negative", "validation"],
        },
        {
            "scenario_id": "TC-017",
            "scenario_name": "Error guessing: XSS in rejection_reason field",
            "technique": "error_guessing",
            "type": "edge_case",
            "priority": "P2",
            "platforms": ["api"],
            "preconditions": ["Admin authenticated", "Account PENDING", "Docs missing"],
            "inputs": {"rejection_reason": "<script>alert(1)</script>"},
            "expected_outcome": "HTTP 400 or sanitized — no JS executed",
            "risk_level": "high",
            "tags": ["security", "edge_case"],
        },
    ],
    "decision_table": [
        {"condition": "Role = admin",           "rules": ["Y", "Y", "Y", "Y", "N", "N", "N", "N"]},
        {"condition": "Status = pending",        "rules": ["Y", "Y", "N", "N", "Y", "Y", "N", "N"]},
        {"condition": "Documents verified",      "rules": ["Y", "N", "Y", "N", "Y", "N", "Y", "N"]},
        {"condition": "→ APPROVE",              "rules": ["✅", "❌", "❌", "❌", "❌", "❌", "❌", "❌"]},
        {"condition": "→ REJECT (missing docs)", "rules": ["❌", "✅", "❌", "✅", "❌", "❌", "❌", "❌"]},
        {"condition": "→ 403 Forbidden",        "rules": ["❌", "❌", "❌", "❌", "✅", "✅", "✅", "✅"]},
    ],
    "pairwise_matrix": [],
    "state_diagram": {
        "states": ["PENDING", "APPROVED", "REJECTED"],
        "transitions": [
            {"from": "PENDING",   "event": "admin_approve + docs_verified", "to": "APPROVED"},
            {"from": "PENDING",   "event": "admin_reject OR docs_missing",  "to": "REJECTED"},
        ],
        "invalid_transitions": [
            {"from": "APPROVED", "to": "PENDING",  "expected": "409"},
            {"from": "APPROVED", "to": "REJECTED", "expected": "409"},
            {"from": "REJECTED", "to": "PENDING",  "expected": "409"},
            {"from": "REJECTED", "to": "APPROVED", "expected": "409"},
        ],
    },
    "coverage_per_ac": {
        "AC1-admin-approve":        100.0,
        "AC2-viewer-403":           100.0,
        "AC3-missing-docs-reject":  100.0,
        "AC4-state-transition":     100.0,
        "AC5-password-boundary":     85.7,
    },
    "total_scenarios": 17,
    "estimated_coverage_percent": 97.4,
    "test_data_requirements": [
        "CMS admin account (role=admin) in staging DB",
        "CMS viewer account (role=viewer) in staging DB",
        "User account in PENDING state with documents VERIFIED",
        "User account in PENDING state with documents MISSING",
        "User account already in APPROVED state",
        "User account already in REJECTED state",
    ],
    "environment_prerequisites": [
        "VPN connected to staging environment",
        "Staging DB accessible (hono_dev)",
        "CMS API deployed to staging (api-dev.thehono.com)",
        "CMS_EMAIL and CMS_PASSWORD set in .env",
    ],
    "entry_criteria": [
        "cms_approve feature deployed to staging",
        "Test data seeded — at least 3 accounts in PENDING state",
        "CMS admin and viewer accounts confirmed",
    ],
    "exit_criteria": [
        "All P1 scenarios passed",
        "No open Critical or High bugs",
        "Coverage >= 90% across all 5 ACs",
        "Decision table: all 8 rule columns executed",
        "State machine: valid transitions pass, invalid return 409",
    ],
    "estimated_execution_time_minutes": 50,
}


def build_mock_response() -> MagicMock:
    resp = MagicMock()
    resp.content     = json.dumps(MOCK_LLM_JSON)
    resp.model       = "mock/gpt-demo"
    resp.tokens_used = 3842
    return resp


def hr(char: str = "─", width: int = 70) -> None:
    print(char * width)


def section(title: str) -> None:
    hr()
    print(f"  {title}")
    hr()


def main() -> None:
    # ── 4. Patch complete_text on the already-constructed llm_client instance ─
    with patch.object(llm_client, "complete_text", return_value=build_mock_response()):

        agent = TestPlanAgent()

        # ────────────────────────────────────────────────────────────────────
        # STEP 1 — Technique selection with full evidence
        # ────────────────────────────────────────────────────────────────────
        section("STEP 1 — _select_techniques()  —  which patterns fired")

        techniques = agent._select_techniques(REQUIREMENTS)

        full_text = " ".join([
            REQUIREMENTS["description"],
            REQUIREMENTS["feature_name"],
            "\n".join(REQUIREMENTS["acceptance_criteria"]),
        ]).lower()

        print(f"\n  Selected techniques: {techniques}\n")
        print("  ── Evidence per technique ──\n")

        print("  ✅  equivalence_partitioning   [ALWAYS — baseline rule]")
        print("      Included regardless of content — valid/invalid partitions.\n")

        print("  ✅  error_guessing             [ALWAYS — baseline rule]")
        print("      Included regardless of content — null, empty, special chars.\n")

        dt_hits = [(p.pattern, m.group()) for p in _DT_PATTERNS
                   if (m := p.search(full_text))]
        sym = "✅" if dt_hits else "❌"
        print(f"  {sym}  decision_table             [{len(dt_hits)} pattern(s) matched]")
        for pat, match in dt_hits[:4]:
            print(f'      /{pat}/  →  "{match[:68]}"')
        print()

        pw_hits = [kw for kw in _PAIRWISE_PARAMS if kw in full_text]
        sym = "✅" if len(pw_hits) >= 3 else "❌"
        note = "TRIGGERED" if len(pw_hits) >= 3 else f"NOT triggered — {len(pw_hits)}/3 threshold"
        print(f"  {sym}  pairwise                   [{note}]")
        print(f"      Params in text: {pw_hits or 'none'}\n")

        bva_hits = [kw for kw in _BVA_KEYWORDS if kw in full_text]
        sym = "✅" if bva_hits else "❌"
        print(f"  {sym}  boundary_value_analysis   [{len(bva_hits)} keyword(s) matched]")
        print(f"      Keywords: {bva_hits}\n")

        st_hits = [kw for kw in _ST_KEYWORDS if kw in full_text]
        sym = "✅" if st_hits else "❌"
        print(f"  {sym}  state_transition           [{len(st_hits)} keyword(s) matched]")
        print(f"      Keywords: {st_hits}\n")

        # ────────────────────────────────────────────────────────────────────
        # STEP 2 — Full create_test_plan
        # ────────────────────────────────────────────────────────────────────
        section("STEP 2 — create_test_plan()  —  full agent pipeline")
        print("  Running agent.create_test_plan(REQUIREMENTS) …\n")

        output = agent.create_test_plan(REQUIREMENTS)

        print(f"  ✅  Agent returned TestPlanOutput")
        print(f"      model_used:     {output.model_used}")
        print(f"      tokens_used:    {output.tokens_used}")
        print(f"      prompt_version: {output.prompt_version}")
        print(f"      generated_at:   {output.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # ────────────────────────────────────────────────────────────────────
        # STEP 3 — Print results
        # ────────────────────────────────────────────────────────────────────
        section("STEP 3 — Results")

        print("\n  techniques_used:")
        for t in output.techniques_used:
            print(f"    • {t}")

        print("\n  technique_rationale:")
        for tech, rationale in output.technique_rationale.items():
            print(f"\n    [{tech}]")
            words, lines, line = rationale.split(), [], []
            for w in words:
                if sum(len(x) + 1 for x in line) + len(w) > 68:
                    lines.append(" ".join(line))
                    line = [w]
                else:
                    line.append(w)
            if line:
                lines.append(" ".join(line))
            for ln in lines:
                print(f"      {ln}")

        print(f"\n  total_scenarios:             {output.total_scenarios}")
        print(f"  estimated_coverage_percent:  {output.estimated_coverage_percent}%")

        print("\n  coverage_per_ac:")
        for ac, pct in output.coverage_per_ac.items():
            filled = int(pct // 10)
            bar = "█" * filled + "░" * (10 - filled)
            print(f"    {ac:<40} {bar}  {pct:.1f}%")

        print(f"\n  estimated_execution_time:    {output.estimated_execution_time_minutes} min")

        print("\n  test_data_requirements:")
        for t in output.test_data_requirements:
            print(f"    • {t}")

        print("\n  environment_prerequisites:")
        for e in output.environment_prerequisites:
            print(f"    • {e}")

        print("\n  entry_criteria:")
        for e in output.entry_criteria:
            print(f"    • {e}")

        print("\n  exit_criteria:")
        for e in output.exit_criteria:
            print(f"    • {e}")

        # ── First 3 scenarios in full detail ─────────────────────────
        print()
        hr("-")
        print("  First 3 scenarios — full detail")
        hr("-")
        for sc in output.scenarios[:3]:
            print(f"\n  ┌─ {sc.scenario_id}  [{sc.technique}]  {sc.type.upper()}  {sc.priority}")
            print(f"  │  Name:     {sc.scenario_name}")
            print(f"  │  Risk:     {sc.risk_level}   Platforms: {sc.platforms}")
            print(f"  │  Tags:     {sc.tags}")
            if sc.preconditions:
                print(f"  │  Pre:")
                for p in sc.preconditions:
                    print(f"  │    - {p}")
            if sc.inputs:
                print(f"  │  Inputs:  {json.dumps(sc.inputs, ensure_ascii=False)}")
            print(f"  │  Expect:  {sc.expected_outcome}")
            print(f"  └{'─' * 66}")

        # ── Decision Table ────────────────────────────────────────────
        if output.decision_table:
            print()
            hr("-")
            print(f"  Decision Table  ({len(output.decision_table)} condition rows × 8 rule columns)")
            hr("-")
            rule_headers = "   ".join(f"R{i+1}" for i in range(8))
            print(f"  {'Condition':<44}  │  {rule_headers}")
            hr("-")
            for row in output.decision_table:
                rules_str = "   ".join(f"{r:^3}" for r in row.rules)
                print(f"  {row.condition[:44]:<44}  │  {rules_str}")

        # ── State Diagram ─────────────────────────────────────────────
        if output.state_diagram:
            print()
            hr("-")
            print("  State Diagram")
            hr("-")
            sd = output.state_diagram
            print(f"  States: {sd.get('states', [])}")
            valid_t   = sd.get("transitions", [])
            invalid_t = sd.get("invalid_transitions", [])
            print(f"\n  Valid transitions ({len(valid_t)}):")
            for t in valid_t:
                print(f"    {t['from']:10} + [{t['event']}]  →  {t['to']}")
            print(f"\n  Invalid transitions ({len(invalid_t)}) — must all return 409:")
            for t in invalid_t:
                print(f"    {t['from']:12} → {t['to']:<12}  HTTP {t.get('expected','?')}")

        # ── Boundary Value Analysis ───────────────────────────────────
        bva_sc = [s for s in output.scenarios if s.technique == "boundary_value_analysis"]
        if bva_sc:
            print()
            hr("-")
            print(f"  Boundary Value Analysis  ({len(bva_sc)} test cases  |  field: password  |  min=8 max=32)")
            hr("-")
            print(f"  {'ID':<8}  {'len':>4}  {'type':<12}  {'prio'}  Expected")
            hr("-")
            for sc in bva_sc:
                length = sc.inputs.get("length", "?")
                print(f"  {sc.scenario_id:<8}  {str(length):>4}  {sc.type:<12}  {sc.priority}   {sc.expected_outcome[:50]}")

        # ────────────────────────────────────────────────────────────────────
        # STEP 4 — Save (JSON + Excel + CSV)
        # ────────────────────────────────────────────────────────────────────
        section("STEP 4 — Save  →  reports/test_plans/  (JSON + Excel + CSV)")
        saved = agent.save_report(output, "TEST-001", "test_plan")
        print(f"  ✅  JSON:   {saved['json']}")
        print(f"  ✅  Excel:  {saved['excel']}")
        print(f"  ✅  CSV:    {saved['csv']}")

        # ────────────────────────────────────────────────────────────────────
        # STEP 5 — Verify all 3 files
        # ────────────────────────────────────────────────────────────────────
        section("STEP 5 — Verify saved files")

        # JSON
        p_json = Path(saved["json"])
        if p_json.exists():
            text     = p_json.read_text()
            data     = json.loads(text)
            size_kb  = p_json.stat().st_size / 1024
            print(f"  ✅  JSON  {p_json.name}")
            print(f"      {len(text.splitlines())} lines  |  {size_kb:.1f} KB  |  "
                  f"{len(data.get('scenarios',[]))} scenarios  |  "
                  f"coverage {data.get('estimated_coverage_percent')}%")
        else:
            print(f"  ❌  JSON NOT found"); sys.exit(1)

        # Excel
        p_xl = Path(saved["excel"])
        if p_xl.exists():
            from openpyxl import load_workbook
            wb     = load_workbook(p_xl)
            sheets = wb.sheetnames
            rows   = wb["Test Scenarios"].max_row - 1  # minus header
            size_kb = p_xl.stat().st_size / 1024
            print(f"  ✅  Excel {p_xl.name}")
            print(f"      {size_kb:.1f} KB  |  sheets: {sheets}  |  {rows} scenario rows")
        else:
            print(f"  ❌  Excel NOT found"); sys.exit(1)

        # CSV
        p_csv = Path(saved["csv"])
        if p_csv.exists():
            import csv as _csv
            with open(p_csv) as f:
                csv_rows = list(_csv.reader(f))
            size_kb = p_csv.stat().st_size / 1024
            print(f"  ✅  CSV   {p_csv.name}")
            print(f"      {size_kb:.1f} KB  |  {len(csv_rows)-1} data rows  |  "
                  f"columns: {csv_rows[0]}")
        else:
            print(f"  ❌  CSV NOT found"); sys.exit(1)

        hr("═")
        print("  ALL 5 STEPS COMPLETE — TestPlanAgent verified ✅")
        hr("═")


if __name__ == "__main__":
    main()
