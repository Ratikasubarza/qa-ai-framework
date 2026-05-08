"""
Excel & CSV Writer Skill — exports test cases to both formats.
Naming convention: test_plan_<feature_name>_<YYYYMMDD>.csv/xlsx
"""
import csv
import structlog
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from core.agent_contracts import TestCaseAgentOutput

logger = structlog.get_logger(__name__)

# Column definitions — matches spec
COLUMNS = [
    "Case ID", "Title", "Preconditions", "Steps",
    "Expected Result", "Priority", "Tags", "Platform", "AI Generated"
]

# Priority colors for Excel
PRIORITY_COLORS = {
    "P0": "FFCCCC",  # Red — critical
    "P1": "FFE5CC",  # Orange — medium
    "P2": "CCFFCC",  # Green — low
}

HEADER_COLOR  = "1E293B"
HEADER_FONT   = "FFFFFF"


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
            # Map test_type to priority if not set
            priority_map = {"smoke": "P0", "regression": "P1",
                           "e2e": "P1", "negative": "P1", "boundary": "P2"}
            priority = priority_map.get(s.test_type.value, "P1")

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

    def write_excel(self, output: TestCaseAgentOutput) -> Path:
        """Write test cases to formatted Excel file."""
        path = self._get_filename(output.feature, "xlsx")
        rows = self._build_rows(output)

        wb = Workbook()
        ws = wb.active
        ws.title = "Test Cases"

        # ── Header styling ──────────────────────────────────
        header_fill = PatternFill("solid", fgColor=HEADER_COLOR)
        header_font = Font(bold=True, color=HEADER_FONT, size=11)
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"),
        )

        for col_idx, col_name in enumerate(COLUMNS, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill    = header_fill
            cell.font    = header_font
            cell.alignment = header_align
            cell.border  = thin_border

        # ── Data rows ────────────────────────────────────────
        for row_idx, row in enumerate(rows, 2):
            priority = row[5]  # Priority column
            row_color = PRIORITY_COLORS.get(priority, "FFFFFF")
            row_fill  = PatternFill("solid", fgColor=row_color)

            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=str(value))
                cell.fill      = row_fill
                cell.border    = thin_border
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        # ── Column widths ────────────────────────────────────
        col_widths = [10, 35, 25, 50, 35, 10, 20, 12, 14]
        for i, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # ── Row heights ──────────────────────────────────────
        ws.row_dimensions[1].height = 30
        for row_idx in range(2, len(rows) + 2):
            ws.row_dimensions[row_idx].height = 60

        # ── Freeze header row ────────────────────────────────
        ws.freeze_panes = "A2"

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
