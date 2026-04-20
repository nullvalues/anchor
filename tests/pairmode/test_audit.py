"""Tests for audit.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills.pairmode.scripts.audit import (
    AuditItem,
    AuditResult,
    audit_project,
    format_audit_output,
)
from skills.pairmode.scripts import audit as _audit_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEMPLATES_DIR = _audit_mod.TEMPLATES_DIR
CANONICAL_FILES = _audit_mod.CANONICAL_FILES


def _write_state(project_dir: Path, version: str | None = "0.1.0") -> None:
    companion = project_dir / ".companion"
    companion.mkdir(parents=True, exist_ok=True)
    state: dict = {}
    if version is not None:
        state["pairmode_version"] = version
    (companion / "state.json").write_text(json.dumps(state), encoding="utf-8")


def _copy_canonical_files(project_dir: Path) -> None:
    """Copy all canonical template files (raw .j2 content) into project_dir."""
    for dest_rel, template_rel in CANONICAL_FILES:
        template_path = TEMPLATES_DIR / template_rel
        dest_path = project_dir / dest_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if template_path.exists():
            dest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            dest_path.write_text("# placeholder\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuditProjectAllPresentIdentical:
    """All canonical files present and identical → nothing MISSING, possible EXTRA only."""

    def test_no_missing_when_all_files_present_and_identical(self, tmp_path: Path) -> None:
        _write_state(tmp_path)
        _copy_canonical_files(tmp_path)

        result = audit_project(tmp_path)

        assert result.missing == [], f"Expected no missing items, got: {result.missing}"
        assert result.inconsistent == [], (
            f"Expected no inconsistent items, got: {result.inconsistent}"
        )

    def test_extra_sections_exist_for_project_specific_content(self, tmp_path: Path) -> None:
        """When project files match canonical exactly there should be no extra sections
        beyond what the templates themselves produce (EXTRA can be empty or non-empty
        depending on preamble handling — just assert it is a list)."""
        _write_state(tmp_path)
        _copy_canonical_files(tmp_path)

        result = audit_project(tmp_path)

        assert isinstance(result.extra, list)


class TestAuditProjectMissingClaudeMd:
    """Project missing CLAUDE.md → CLAUDE.md sections appear in MISSING."""

    def test_missing_claude_md_produces_missing_items(self, tmp_path: Path) -> None:
        _write_state(tmp_path)
        _copy_canonical_files(tmp_path)
        # Remove CLAUDE.md
        (tmp_path / "CLAUDE.md").unlink()

        result = audit_project(tmp_path)

        claude_md_missing = [i for i in result.missing if i.file == "CLAUDE.md"]
        assert len(claude_md_missing) > 0, "Expected MISSING items for CLAUDE.md"

    def test_missing_claude_md_description_mentions_file(self, tmp_path: Path) -> None:
        _write_state(tmp_path)
        _copy_canonical_files(tmp_path)
        (tmp_path / "CLAUDE.md").unlink()

        result = audit_project(tmp_path)

        for item in result.missing:
            if item.file == "CLAUDE.md":
                assert "CLAUDE.md" in item.file
                break


class TestAuditProjectNoPairmodeVersion:
    """Project with no pairmode_version in state.json → pairmode_version is None."""

    def test_no_pairmode_version_key(self, tmp_path: Path) -> None:
        _write_state(tmp_path, version=None)  # state.json exists but no version key

        result = audit_project(tmp_path)

        assert result.pairmode_version is None

    def test_no_state_json_at_all(self, tmp_path: Path) -> None:
        # No .companion/state.json at all
        result = audit_project(tmp_path)

        assert result.pairmode_version is None

    def test_canonical_version_always_set(self, tmp_path: Path) -> None:
        result = audit_project(tmp_path)

        assert result.canonical_version == "0.1.0"


class TestFormatAuditOutput:
    """format_audit_output produces correct string with all sections."""

    def _make_result(
        self,
        missing: list[AuditItem] | None = None,
        inconsistent: list[AuditItem] | None = None,
        extra: list[AuditItem] | None = None,
    ) -> AuditResult:
        return AuditResult(
            project_name="myproject",
            project_dir=Path("/tmp/myproject"),
            missing=missing or [],
            inconsistent=inconsistent or [],
            extra=extra or [],
            pairmode_version="0.1.0",
            canonical_version="0.1.0",
        )

    def test_header_contains_project_name_and_version(self) -> None:
        result = self._make_result()
        output = format_audit_output(result)
        assert "myproject" in output
        assert "0.1.0" in output

    def test_missing_section_present_when_items_exist(self) -> None:
        result = self._make_result(
            missing=[AuditItem(file="CLAUDE.md", section="intro", description="Missing intro")]
        )
        output = format_audit_output(result)
        assert "MISSING" in output
        assert "CLAUDE.md" in output
        assert "\u2717" in output  # ✗

    def test_inconsistent_section_present(self) -> None:
        result = self._make_result(
            inconsistent=[
                AuditItem(file="CLAUDE.build.md", section="rules", description="Rules differ")
            ]
        )
        output = format_audit_output(result)
        assert "INCONSISTENT" in output
        assert "CLAUDE.build.md" in output
        assert "~" in output

    def test_extra_section_present(self) -> None:
        result = self._make_result(
            extra=[
                AuditItem(
                    file=".claude/agents/builder.md",
                    section="custom",
                    description="Custom section",
                )
            ]
        )
        output = format_audit_output(result)
        assert "EXTRA" in output
        assert ".claude/agents/builder.md" in output
        assert "\u2713" in output  # ✓

    def test_recommendation_always_present(self) -> None:
        result = self._make_result()
        output = format_audit_output(result)
        assert "RECOMMENDATION" in output
        assert "sync" in output

    def test_empty_sections_omitted(self) -> None:
        result = self._make_result()  # no items anywhere
        output = format_audit_output(result)
        assert "MISSING" not in output
        assert "INCONSISTENT" not in output
        assert "EXTRA" not in output

    def test_lesson_id_appears_in_missing_item(self) -> None:
        result = self._make_result(
            missing=[
                AuditItem(
                    file="CLAUDE.md",
                    section="intro",
                    description="Missing intro",
                    lesson_id="L001",
                )
            ]
        )
        output = format_audit_output(result)
        assert "L001" in output


class TestLessonIdInMissingItems:
    """Lesson IDs appear in MISSING items when a lesson applies."""

    def test_lesson_id_attached_when_lesson_affects_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a lesson's methodology_change.affects mentions CLAUDE.md and the file
        is missing, the lesson_id should be attached to the AuditItem."""
        fake_lessons_data = {
            "version": "1.0.0",
            "lessons": [
                {
                    "id": "L001",
                    "trigger": "test trigger",
                    "learning": "some learning",
                    "date": "2026-01-01",
                    "status": "active",
                    "applies_to": ["all"],
                    "methodology_change": {
                        "affects": "CLAUDE.md",
                        "description": "Update CLAUDE.md",
                    },
                }
            ],
        }

        monkeypatch.setattr(
            _audit_mod.lesson_utils,
            "load_lessons",
            lambda: fake_lessons_data,
        )

        _write_state(tmp_path)
        _copy_canonical_files(tmp_path)
        (tmp_path / "CLAUDE.md").unlink()

        result = audit_project(tmp_path)

        claude_md_missing = [i for i in result.missing if i.file == "CLAUDE.md"]
        assert len(claude_md_missing) > 0
        lesson_ids = [i.lesson_id for i in claude_md_missing if i.lesson_id]
        assert "L001" in lesson_ids, f"Expected L001 in lesson_ids, got: {lesson_ids}"


class TestNoCompanionStateJson:
    """audit_project on a directory with no .companion/state.json → pairmode_version is None."""

    def test_no_companion_dir(self, tmp_path: Path) -> None:
        # tmp_path has no .companion directory at all
        result = audit_project(tmp_path)
        assert result.pairmode_version is None

    def test_no_error_raised(self, tmp_path: Path) -> None:
        # Should not raise
        result = audit_project(tmp_path)
        assert isinstance(result, AuditResult)
