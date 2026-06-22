"""
Excel & CSV Writer Skill — exports test cases and test plans to both formats.
Naming conventions:
  test_cases:  test_plan_<feature>_<YYYYMMDD>.csv/xlsx
              test_plan_<feature>_<platform>_<YYYYMMDD>.csv  (per-platform)
  test_plans:  <feature>_test_plan_<YYYYMMDD>.csv/xlsx
              <feature>_test_plan_<platform>_<YYYYMMDD>.csv  (per-platform)
"""
import csv
import json as _json
import structlog
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from core.agent_contracts import TestCaseAgentOutput, TestPlanOutput

logger = structlog.get_logger(__name__)

# Column definitions — matches spec
COLUMNS = [
    "Case ID", "Title", "Preconditions", "Steps",
    "Expected Result", "Priority", "Tags", "Platform", "AI Generated",
    "Regression Candidate", "Regression Risk Area"
]

# Priority colors for Excel
PRIORITY_COLORS = {
    "P0": "FFCCCC",  # Red — critical
    "P1": "FFE5CC",  # Orange — medium
    "P2": "CCFFCC",  # Green — low
}

HEADER_COLOR = "1E293B"
HEADER_FONT  = "FFFFFF"

_THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)


def _write_ws_header(ws, columns: list[str]) -> None:
    """Shared helper — writes a styled header row to any worksheet."""
    header_fill = PatternFill("solid", fgColor=HEADER_COLOR)
    header_font = Font(bold=True, color=HEADER_FONT, size=11)
    center      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for ci, col in enumerate(columns, 1):
        cell = ws.cell(row=1, column=ci, value=col)
        cell.fill      = header_fill
        cell.font      = header_font
        cell.alignment = center
        cell.border    = _THIN_BORDER
    ws.row_dimensions[1].height = 25
    ws.freeze_panes = "A2"


class ExcelWriter:
    def __init__(self, output_dir: str = "reports/excel"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_filename(self, feature: str, ext: str) -> Path:
        """Generate filename: test_plan_<feature>_<YYYYMMDD>.<ext>"""
        feature_slug = feature.lower().replace(" ", "_").replace("/", "_")
        date_str     = datetime.now().strftime("%Y%m%d")
        return self.output_dir / f"test_plan_{feature_slug}_{date_str}.{ext}"

    def _build_rows(self, output: TestCaseAgentOutput) -> list[list]:
        """Convert TestCaseAgentOutput to list of rows."""
        rows = []
        for s in output.scenarios:
            # Preserve scenario priority instead of deriving it from test type.
            priority_map = {"high": "P0", "medium": "P1", "low": "P2"}
            priority = priority_map.get(s.priority.value, "P1")

            # Build Gherkin steps from scenario steps
            steps_text = ""
            if s.steps:
                step_lines = []
                for i, step in enumerate(s.steps):
                    prefix = "Given" if i == 0 else "When" if i < len(s.steps) - 1 else "Then"
                    step_lines.append(f"{prefix} {step.action}")
                steps_text = "\n".join(step_lines)
            else:
                steps_text = f"Given fresh state\nWhen test is executed\nThen {s.expected_result}"

            tags = ", ".join(s.tags) if s.tags else s.test_type.value
            platforms = ", ".join(p.value.upper() for p in s.platforms) if s.platforms else "WEB"

            rows.append([
                s.scenario_id,
                s.name,
                s.precondition or "Fresh/blank state",
                steps_text,
                s.expected_result,
                priority,
                tags,
                platforms,
                "true",
                "true" if s.regression_candidate else "false",
                ", ".join(s.regression_risk_area),
            ])
        return rows

    def write_csv(self, output: TestCaseAgentOutput) -> Path:
        """Write test cases to CSV file."""
        path = self._get_filename(output.feature, "csv")
        rows = self._build_rows(output)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerows(rows)

        logger.info("csv_written", path=str(path), rows=len(rows))
        return path

    def write_per_platform_csv(self, output: TestCaseAgentOutput) -> dict[str, Path]:
        """Write one CSV per platform. Returns {platform_value: Path}.

        Scenarios tagged with multiple platforms appear in each relevant file.
        Scenarios with no platform tag fall back to the first available platform.
        """
        by_platform: dict[str, list] = defaultdict(list)
        for s in output.scenarios:
            if s.platforms:
                for p in s.platforms:
                    by_platform[p.value].append(s)
            else:
                by_platform["web"].append(s)

        if not by_platform:
            return {}

        feature_slug = output.feature.lower().replace(" ", "_").replace("/", "_")
        date_str     = datetime.now().strftime("%Y%m%d")
        paths: dict[str, Path] = {}

        for platform, scenarios in by_platform.items():
            subset = TestCaseAgentOutput(
                feature=output.feature,
                scenarios=scenarios,
                coverage_summary=output.coverage_summary,
                total_scenarios=len(scenarios),
                prompt_version=output.prompt_version,
                model_used=output.model_used,
                generated_at=output.generated_at,
                tokens_used=output.tokens_used,
            )
            path = self.output_dir / f"test_plan_{feature_slug}_{platform}_{date_str}.csv"
            rows = self._build_rows(subset)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)
                writer.writerows(rows)
            logger.info("csv_per_platform_written", path=str(path), platform=platform, rows=len(rows))
            paths[platform] = path

        return paths

    def write_excel(self, output: TestCaseAgentOutput) -> Path:
        """Write test cases to formatted Excel file."""
        path = self._get_filename(output.feature, "xlsx")
        rows = self._build_rows(output)

        wb = Workbook()
        ws = wb.active
        ws.title = "Test Cases"

        _write_ws_header(ws, COLUMNS)
        ws.row_dimensions[1].height = 30  # test-case header is slightly taller

        # ── Data rows ────────────────────────────────────────
        for row_idx, row in enumerate(rows, 2):
            priority  = row[5]  # Priority column
            row_fill  = PatternFill("solid", fgColor=PRIORITY_COLORS.get(priority, "FFFFFF"))
            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=str(value))
                cell.fill      = row_fill
                cell.border    = _THIN_BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        # ── Column widths ────────────────────────────────────
        col_widths = [10, 35, 25, 50, 35, 10, 20, 12, 14, 20, 35]
        for i, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        for row_idx in range(2, len(rows) + 2):
            ws.row_dimensions[row_idx].height = 60

        # ── Add metadata sheet ───────────────────────────────
        meta = wb.create_sheet("Metadata")
        meta["A1"] = "Feature"
        meta["B1"] = output.feature
        meta["A2"] = "Generated At"
        meta["B2"] = output.generated_at.strftime("%Y-%m-%d %H:%M")
        meta["A3"] = "Model"
        meta["B3"] = output.model_used
        meta["A4"] = "Prompt Version"
        meta["B4"] = output.prompt_version
        meta["A5"] = "Total Scenarios"
        meta["B5"] = output.total_scenarios
        meta["A6"] = "Coverage Summary"
        meta["B6"] = output.coverage_summary

        wb.save(path)
        logger.info("excel_written", path=str(path), rows=len(rows))
        return path

    def write_both(self, output: TestCaseAgentOutput) -> dict[str, Path]:
        """Write both CSV and Excel. Returns dict of paths."""
        return {
            "csv":   self.write_csv(output),
            "excel": self.write_excel(output),
        }


excel_writer = ExcelWriter()


# ─────────────────────────────────────────────────────────────────────────────
# Test Plan export (TestPlanOutput → CSV + multi-sheet XLSX)
# ─────────────────────────────────────────────────────────────────────────────

TP_SCENARIO_COLUMNS = [
    "TC ID", "Name", "Technique", "Type", "Priority",
    "Platforms", "Preconditions", "Inputs", "Expected Outcome",
    "Risk Level", "Tags",
]

TECHNIQUE_COLORS = {
    "decision_table":             "D6E4FF",  # blue
    "boundary_value_analysis":    "FFF2CC",  # yellow
    "state_transition":           "E2EFDA",  # green
    "equivalence_partitioning":   "FCE4EC",  # pink
    "error_guessing":             "F3E5F5",  # purple
    "pairwise":                   "E0F7FA",  # teal
}


class TestPlanExcelWriter:
    def __init__(self, output_dir: str = "reports/test_plans"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _slug(self, feature: str) -> str:
        return feature.lower().replace(" ", "_").replace("/", "_").replace(":", "")

    def _get_path(self, feature: str, ext: str) -> Path:
        date_str = datetime.now().strftime("%Y%m%d")
        return self.output_dir / f"{self._slug(feature)}_test_plan_{date_str}.{ext}"

    def _scenario_rows(self, output: TestPlanOutput) -> list[list]:
        rows = []
        for s in output.scenarios:
            rows.append([
                s.scenario_id,
                s.scenario_name,
                s.technique,
                s.type,
                s.priority,
                ", ".join(s.platforms),
                "\n".join(s.preconditions),
                _json.dumps(s.inputs, ensure_ascii=False) if s.inputs else "",
                s.expected_outcome,
                s.risk_level,
                ", ".join(s.tags),
            ])
        return rows

    def write_csv(self, output: TestPlanOutput) -> Path:
        """Write test plan scenarios to CSV."""
        path = self._get_path(output.feature_name, "csv")
        rows = self._scenario_rows(output)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(TP_SCENARIO_COLUMNS)
            writer.writerows(rows)
        logger.info("test_plan_csv_written", path=str(path), rows=len(rows))
        return path

    def write_per_platform_csv(self, output: TestPlanOutput) -> dict[str, Path]:
        """Write one CSV per platform from test plan scenarios. Returns {platform: Path}.

        Scenarios tagged with multiple platforms appear in each relevant file.
        """
        by_platform: dict[str, list] = defaultdict(list)
        for s in output.scenarios:
            if s.platforms:
                for p in s.platforms:
                    by_platform[p].append(s)
            else:
                by_platform["web"].append(s)

        if not by_platform:
            return {}

        date_str = datetime.now().strftime("%Y%m%d")
        paths: dict[str, Path] = {}

        for platform, scenarios in by_platform.items():
            path = self.output_dir / f"{self._slug(output.feature_name)}_test_plan_{platform}_{date_str}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(TP_SCENARIO_COLUMNS)
                for s in scenarios:
                    writer.writerow([
                        s.scenario_id,
                        s.scenario_name,
                        s.technique,
                        s.type,
                        s.priority,
                        platform,
                        "\n".join(s.preconditions),
                        _json.dumps(s.inputs, ensure_ascii=False) if s.inputs else "",
                        s.expected_outcome,
                        s.risk_level,
                        ", ".join(s.tags),
                    ])
            logger.info("test_plan_csv_per_platform_written", path=str(path), platform=platform, rows=len(scenarios))
            paths[platform] = path

        return paths

    def write_excel(self, output: TestPlanOutput) -> Path:
        """Write test plan to formatted multi-sheet Excel."""
        path = self._get_path(output.feature_name, "xlsx")
        wb   = Workbook()

        # ── Sheet 1: Test Scenarios ───────────────────────────────────────────
        ws = wb.active
        ws.title = "Test Scenarios"
        _write_ws_header(ws, TP_SCENARIO_COLUMNS)
        for ri, row in enumerate(self._scenario_rows(output), 2):
            technique = output.scenarios[ri - 2].technique
            fill      = PatternFill("solid", fgColor=TECHNIQUE_COLORS.get(technique, "FFFFFF"))
            for ci, val in enumerate(row, 1):
                cell = ws.cell(row=ri, column=ci, value=str(val))
                cell.fill      = fill
                cell.border    = _THIN_BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            ws.row_dimensions[ri].height = 55
        for i, w in enumerate([10, 38, 22, 14, 10, 14, 28, 32, 38, 12, 22], 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # ── Sheet 2: Decision Table ───────────────────────────────────────────
        if output.decision_table:
            wsd = wb.create_sheet("Decision Table")
            max_rules = max((len(r.rules) for r in output.decision_table), default=0)
            _write_ws_header(wsd, ["Condition"] + [f"R{i+1}" for i in range(max_rules)])
            rule_fills = [
                PatternFill("solid", fgColor=c) for c in
                ["E8F5E9", "FFF9C4", "E3F2FD", "FCE4EC",
                 "F3E5F5", "E0F7FA", "FFF3E0", "F1F8E9"]
            ]
            for ri, row in enumerate(output.decision_table, 2):
                cond_cell = wsd.cell(row=ri, column=1, value=row.condition)
                cond_cell.font      = Font(bold=True)
                cond_cell.border    = _THIN_BORDER
                cond_cell.alignment = Alignment(vertical="center", wrap_text=True)
                for ci, rule in enumerate(row.rules, 2):
                    cell = wsd.cell(row=ri, column=ci, value=rule)
                    cell.fill      = rule_fills[(ci - 2) % len(rule_fills)]
                    cell.border    = _THIN_BORDER
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            wsd.column_dimensions["A"].width = 30
            for i in range(2, max_rules + 2):
                wsd.column_dimensions[get_column_letter(i)].width = 8

        # ── Sheet 3: State Diagram ────────────────────────────────────────────
        sd = output.state_diagram
        if sd:
            wss = wb.create_sheet("State Diagram")
            _write_ws_header(wss, ["Type", "From State", "Event / Condition", "To State", "Expected HTTP"])
            ri = 2
            valid_fill   = PatternFill("solid", fgColor="E2EFDA")
            invalid_fill = PatternFill("solid", fgColor="FFCCCC")
            for t in sd.get("transitions", []):
                for ci, val in enumerate([
                    "VALID", t.get("from", ""), t.get("event", ""), t.get("to", ""), "200"
                ], 1):
                    cell = wss.cell(row=ri, column=ci, value=val)
                    cell.fill      = valid_fill
                    cell.border    = _THIN_BORDER
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                ri += 1
            for t in sd.get("invalid_transitions", []):
                for ci, val in enumerate([
                    "INVALID", t.get("from", ""), "—", t.get("to", ""), t.get("expected", "409")
                ], 1):
                    cell = wss.cell(row=ri, column=ci, value=val)
                    cell.fill      = invalid_fill
                    cell.border    = _THIN_BORDER
                    cell.alignment = Alignment(vertical="center")
                ri += 1
            for i, w in enumerate([10, 16, 42, 16, 16], 1):
                wss.column_dimensions[get_column_letter(i)].width = w

        # ── Sheet 4: Summary ──────────────────────────────────────────────────
        wsm = wb.create_sheet("Summary")
        bold = Font(bold=True)
        summary_rows = [
            ("Feature",                  output.feature_name),
            ("Ticket ID",                output.ticket_id),
            ("Generated At",             output.generated_at.strftime("%Y-%m-%d %H:%M")),
            ("Model Used",               output.model_used),
            ("Prompt Version",           output.prompt_version),
            ("Techniques Used",          ", ".join(output.techniques_used)),
            ("Total Scenarios",          output.total_scenarios),
            ("Estimated Coverage",       f"{output.estimated_coverage_percent:.1f}%"),
            ("Est. Execution Time",      f"{output.estimated_execution_time_minutes} min"),
            ("", ""),
            ("Coverage per AC", ""),
        ]
        for ac, pct in output.coverage_per_ac.items():
            summary_rows.append((f"  {ac}", f"{pct:.1f}%"))
        summary_rows += [
            ("", ""),
            ("Test Data Requirements", ""),
        ]
        for item in output.test_data_requirements:
            summary_rows.append((f"  • {item}", ""))
        summary_rows += [("", ""), ("Environment Prerequisites", "")]
        for item in output.environment_prerequisites:
            summary_rows.append((f"  • {item}", ""))
        summary_rows += [("", ""), ("Entry Criteria", "")]
        for item in output.entry_criteria:
            summary_rows.append((f"  • {item}", ""))
        summary_rows += [("", ""), ("Exit Criteria", "")]
        for item in output.exit_criteria:
            summary_rows.append((f"  • {item}", ""))

        for ri, (key, val) in enumerate(summary_rows, 1):
            ka = wsm.cell(row=ri, column=1, value=key)
            va = wsm.cell(row=ri, column=2, value=val)
            if key and not key.startswith(" ") and key != "":
                ka.font = bold
        wsm.column_dimensions["A"].width = 32
        wsm.column_dimensions["B"].width = 55

        wb.save(path)
        logger.info("test_plan_excel_written", path=str(path), scenarios=output.total_scenarios)
        return path

    def write_both(self, output: TestPlanOutput) -> dict[str, Path]:
        """Write CSV and Excel. Returns {csv: Path, excel: Path}."""
        return {
            "csv":   self.write_csv(output),
            "excel": self.write_excel(output),
        }


test_plan_excel_writer = TestPlanExcelWriter()
