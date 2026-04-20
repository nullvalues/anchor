#!/usr/bin/env python3
"""
PostToolUse hook — Pair Partner + Validator roles.

Fires after every file write/edit. Thin relay only.
Sends file change event to sidebar for UML delta + spec check.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

PIPE_PATH = "/tmp/companion.pipe"
STATE_PATH = ".companion/state.json"
DENY_RATIONALE_PATH = ".claude/settings.deny-rationale.json"

WATCHED_TOOLS = {"Write", "Edit", "MultiEdit"}

# Pattern to extract glob from Edit(...) or Write(...) or Bash(...)
_RULE_RE = re.compile(r'^(?:Edit|Write|Bash)\((.+)\)$')


def _load_deny_rationale(cwd: str) -> list[dict]:
    """Load deny-rationale.json rules; return [] if absent or unparseable."""
    path = Path(cwd) / DENY_RATIONALE_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("rules", [])
    except Exception:
        return []


def _check_protected(file_path: str, cwd: str) -> tuple[bool, str, str]:
    """
    Check if file_path matches any deny-rationale rule.

    Returns (protected, protection_rule, non_negotiable).
    If no match, returns (False, "", "").
    """
    if not file_path:
        return False, "", ""

    rules = _load_deny_rationale(cwd)
    if not rules:
        return False, "", ""

    # Normalise path — make relative to cwd if absolute
    rel_path = file_path
    if os.path.isabs(file_path):
        try:
            rel_path = str(Path(file_path).relative_to(cwd))
        except ValueError:
            rel_path = file_path

    for rule in rules:
        pattern_str = rule.get("pattern", "")
        m = _RULE_RE.match(pattern_str)
        if not m:
            continue
        glob = m.group(1)
        if fnmatch.fnmatch(rel_path, glob):
            return True, pattern_str, rule.get("non_negotiable", "")

    return False, "", ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in WATCHED_TOOLS:
        sys.exit(0)

    if not os.path.exists(PIPE_PATH):
        sys.exit(0)

    # get file path from tool input
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    cwd = data.get("cwd") or os.getcwd()

    loaded_modules = []
    try:
        state = json.loads(open(STATE_PATH).read())
        loaded_modules = state.get("last_loaded_modules", [])
    except Exception:
        pass

    # Check if this file is protected
    protected, protection_rule, non_negotiable = _check_protected(file_path, cwd)

    try:
        fd = os.open(PIPE_PATH, os.O_WRONLY | os.O_NONBLOCK)
        msg: dict = {
            "event": "post_tool_use",
            "type": "file_changed",
            "path": file_path,
            "tool": tool_name,
            "file_path": file_path,
            "loaded_modules": loaded_modules,
            "session_id": data.get("session_id"),
            "cwd": cwd,
        }
        if protected:
            msg["protected"] = True
            msg["protection_rule"] = protection_rule
            msg["non_negotiable"] = non_negotiable
        event = json.dumps(msg) + "\n"
        os.write(fd, event.encode())
        os.close(fd)
    except (OSError, BlockingIOError):
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
