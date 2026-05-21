"""
Prep script — collect test files, DEV-BUG comments, api_spec, and gherkin into
knowledge_base/sources/ so the indexer can pick them up.

Run once before indexer:
  PYTHONPATH=. ./venv/bin/python3.11 knowledge_base/_prep_sources.py
"""
import glob
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCES = Path(__file__).parent / "sources"

# ── 1. Test files → test_history/ ─────────────────────────────────────────────
test_history_dir = SOURCES / "test_history"
test_history_dir.mkdir(parents=True, exist_ok=True)

test_files = sorted(glob.glob(str(ROOT / "features/**/steps/**/*test*.py"), recursive=True))
test_files = [f for f in test_files if "__pycache__" not in f]

written_tests = 0
for filepath in test_files:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    # Name by feature folder + filename, e.g. "login_api__login_api_test.md"
    feature_dir = path.parts[-4]  # e.g. "login"
    dest_name = f"{feature_dir}__{path.stem}.md"
    dest = test_history_dir / dest_name
    dest.write_text(
        f"# Test file: {path.relative_to(ROOT)}\n\n```python\n{content}\n```",
        encoding="utf-8",
    )
    written_tests += 1

print(f"[test_history]  {written_tests} files written")

# ── 2. DEV-BUG comments → bug_history/ ────────────────────────────────────────
bug_history_dir = SOURCES / "bug_history"
bug_history_dir.mkdir(parents=True, exist_ok=True)

result = subprocess.run(
    ["grep", "-rn", "DEV-BUG", "features/", "--include=*.py"],
    capture_output=True, text=True, cwd=str(ROOT)
)
bug_lines = [l for l in result.stdout.splitlines() if "__pycache__" not in l]

# Group by file
from collections import defaultdict
by_file: dict[str, list[str]] = defaultdict(list)
for line in bug_lines:
    parts = line.split(":", 2)
    if len(parts) >= 3:
        by_file[parts[0]].append(f"  line {parts[1]}: {parts[2].strip()}")

sections = ["# DEV-BUG Comments — Extracted from Test Files\n"]
for filepath, entries in sorted(by_file.items()):
    sections.append(f"\n## {filepath}\n")
    sections.extend(entries)

dest_bugs = bug_history_dir / "dev_bugs_extracted.md"
dest_bugs.write_text("\n".join(sections), encoding="utf-8")
print(f"[bug_history]   dev_bugs_extracted.md  ({len(bug_lines)} entries across {len(by_file)} files)")

# ── 3. api_spec.yaml → requirements/ ──────────────────────────────────────────
requirements_dir = SOURCES / "requirements"
requirements_dir.mkdir(parents=True, exist_ok=True)

api_spec_src = ROOT / "api_spec.yaml"
api_spec_dst = requirements_dir / "api_spec.md"
api_spec_content = api_spec_src.read_text(encoding="utf-8")
api_spec_dst.write_text(
    f"# Hono API Spec (OpenAPI 3.0)\n\n```yaml\n{api_spec_content}\n```",
    encoding="utf-8",
)
print(f"[requirements]  api_spec.md  ({api_spec_src.stat().st_size} bytes)")

# ── 4. Gherkin .feature files → requirements/ ─────────────────────────────────
feature_files = sorted(glob.glob(str(ROOT / "features/**/gherkin/**/*.feature"), recursive=True))

gherkin_sections = ["# Gherkin Scenarios — Hono QA Framework\n"]
for filepath in feature_files:
    path = Path(filepath)
    rel = path.relative_to(ROOT)
    content = path.read_text(encoding="utf-8")
    gherkin_sections.append(f"\n## {rel}\n\n```gherkin\n{content}\n```")

gherkin_dst = requirements_dir / "gherkin_scenarios.md"
gherkin_dst.write_text("\n".join(gherkin_sections), encoding="utf-8")
print(f"[requirements]  gherkin_scenarios.md  ({len(feature_files)} feature files)")

# ── 5. Pipeline skill_gap reports → bug_history/ ──────────────────────────────
skill_gap_dir = SOURCES / "bug_history"
skill_gap_dir.mkdir(parents=True, exist_ok=True)

gap_files = sorted(glob.glob(str(ROOT / "reports/runs/*/skill_gap/skill_gap_report.json"), recursive=True))
# Also check legacy path
gap_files += sorted(glob.glob(str(ROOT / "reports/gap_reports/*.json"), recursive=True))

written_gaps = 0
for filepath in gap_files:
    path = Path(filepath)
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        feature = data.get("feature", path.stem)
        run_id  = data.get("run_id", "unknown")
        missing = "\n".join(f"- {s}" for s in data.get("missing_scenarios", []))
        recs    = "\n".join(f"- {r}" for r in data.get("recommendations", []))
        content = (
            f"# Skill Gap Report: {feature} (run {run_id})\n\n"
            f"Coverage: {data.get('coverage_percentage', 0):.1f}%\n\n"
            f"## Missing Scenarios\n{missing or '_None_'}\n\n"
            f"## Recommendations\n{recs or '_None_'}\n"
        )
        dest = skill_gap_dir / f"gap_{feature}_{run_id}.md"
        dest.write_text(content, encoding="utf-8")
        written_gaps += 1
    except Exception as e:
        print(f"  [skip] {path.name}: {e}")

print(f"[bug_history]   skill_gap reports: {written_gaps} files written")

# ── 6. Pipeline final summaries → test_history/ ───────────────────────────────
summary_files = sorted(glob.glob(str(ROOT / "reports/runs/*/final_summary.md"), recursive=True))
written_summaries = 0
for filepath in summary_files:
    path = Path(filepath)
    run_id = path.parent.name
    dest = test_history_dir / f"pipeline_run_{run_id}.md"
    try:
        dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        written_summaries += 1
    except Exception as e:
        print(f"  [skip] {path.name}: {e}")

print(f"[test_history]  pipeline summaries: {written_summaries} files written")

print("\nPrep complete — running indexer to update vector store...")

# ── Auto-index after prep ──────────────────────────────────────────────────────
try:
    import sys
    sys.path.insert(0, str(ROOT))
    from knowledge_base.indexer import index_all
    report = index_all()
    print("\nRAG Indexing complete:")
    for source, count in report.items():
        status = "OK" if count > 0 else "WARN (0 files)"
        print(f"  [{status}] {source}: {count} document(s)")
    print(f"\n  Total indexed: {sum(report.values())} document(s)")
except Exception as e:
    print(f"\n  [WARN] Indexer could not run automatically: {e}")
    print("  Run manually: PYTHONPATH=. ./venv/bin/python3.11 -m knowledge_base.indexer")
