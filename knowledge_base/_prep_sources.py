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

print("\nPrep complete — run the indexer next.")
