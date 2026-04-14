#!/usr/bin/env python3
"""Test the live chart rendering without a real Claude Code session.

Simulates pipe events to exercise the MiniSession + build_chart flow.
No LLM calls — just tests the rendering logic.
"""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sidebar_dir = Path(__file__).parent.parent / "skills" / "companion" / "scripts"
sys.path.insert(0, str(sidebar_dir))
import sidebar

# Create a temp modules.json so get_file_module works
tmp_dir = Path(tempfile.mkdtemp(prefix="anchor-chart-test-"))
companion_dir = tmp_dir / ".companion"
companion_dir.mkdir()
(companion_dir / "modules.json").write_text(json.dumps([
    {"name": "finance-twin", "paths": ["al/finance_twin/"]},
    {"name": "decision-ledger", "paths": ["al/decision_ledger/"]},
    {"name": "alerts", "paths": ["al/alerts/"]},
    {"name": "web-api", "paths": ["al/web/"]},
]))
os.chdir(tmp_dir)

# Reset the modules cache
sidebar._modules_cache = None

loaded_modules = ["finance-twin", "decision-ledger"]

print("=== Testing MiniSession + build_chart ===\n")

# Simulate a sequence of file changes
events = [
    {"event": "post_tool_use", "file_path": "al/finance_twin/models.py", "cwd": str(tmp_dir)},
    {"event": "post_tool_use", "file_path": "al/decision_ledger/generator.py", "cwd": str(tmp_dir)},
    {"event": "post_tool_use", "file_path": "al/decision_ledger/punch_list/builder.py", "cwd": str(tmp_dir)},
    {"event": "post_tool_use", "file_path": "al/alerts/evaluator.py", "cwd": str(tmp_dir)},  # boundary!
    {"event": "post_tool_use", "file_path": "al/decision_ledger/cfo_context.py", "cwd": str(tmp_dir)},
]

mini = sidebar.MiniSession(started_at="10:00:00")

for i, event in enumerate(events):
    sidebar.update_mini_session(mini, event, loaded_modules)
    chart = sidebar.build_chart(mini, loaded_modules)
    print(f"\n--- After event {i + 1}: {event['file_path']} ---")
    sidebar.console.print(chart)

# Verify state
print(f"\n=== Final state ===")
print(f"Modules touched: {mini.module_order}")
print(f"Module statuses: {mini.modules}")
print(f"Files tracked: {len(mini.files)}")
print(f"Boundary crossings: {[m for m, s in mini.modules.items() if s == 'boundary']}")

# Verify boundary detection
assert "alerts" in mini.modules, "alerts should be detected"
assert mini.modules["alerts"] == "boundary", "alerts should be a boundary crossing"
assert mini.modules["finance-twin"] == "loaded", "finance-twin should be loaded"

print("\n✓ ALL CHECKS PASSED")

# Cleanup
import shutil
shutil.rmtree(tmp_dir, ignore_errors=True)
