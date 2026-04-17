"""Tests for pairmode Jinja2 templates CLAUDE.md.j2 and CLAUDE.build.md.j2."""

import pathlib
import jinja2
import pytest


TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "skills" / "pairmode" / "templates"

CLAUDE_MD_CONTEXT = {
    "project_name": "myapp",
    "project_description": "a sample web application for testing",
    "stack": "Python 3.11+ / FastAPI / PostgreSQL",
    "domain_model": "multi-tenant SaaS with organisation and workspace hierarchy",
    "build_command": "uv run pytest",
    "test_command": "uv run pytest tests/ -x -q",
    "checklist_items": [
        {
            "name": "HOOK PERFORMANCE",
            "description": "Do any hook scripts make API calls or block? Hooks are thin relays only.",
            "severity": "CRITICAL",
        },
        {
            "name": "PIPE CONTRACT",
            "description": "Do all hook scripts write only to /tmp/companion.pipe?",
            "severity": "CRITICAL",
        },
        {
            "name": "SKILL ISOLATION",
            "description": "Do any skill scripts use hardcoded absolute paths?",
            "severity": "MEDIUM",
        },
    ],
    "protected_paths": [
        "hooks/",
        "skills/seed/scripts/",
        ".claude-plugin/plugin.json",
    ],
}

CLAUDE_BUILD_MD_CONTEXT = {
    "project_name": "myapp",
    "build_command": "PATH=$HOME/.local/bin:$PATH uv run pytest tests/pairmode/ -x -q",
    "test_command": "PATH=$HOME/.local/bin:$PATH uv run pytest tests/ -x -q",
    "migration_command": "uv run alembic upgrade head",
}

CLAUDE_BUILD_MD_NO_MIGRATION_CONTEXT = {
    "project_name": "myapp",
    "build_command": "PATH=$HOME/.local/bin:$PATH uv run pytest tests/pairmode/ -x -q",
    "test_command": "PATH=$HOME/.local/bin:$PATH uv run pytest tests/ -x -q",
    "migration_command": "",
}


def render(template_name: str, context: dict) -> str:
    loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
    env = jinja2.Environment(loader=loader, undefined=jinja2.StrictUndefined)
    template = env.get_template(template_name)
    return template.render(**context)


# ---------------------------------------------------------------------------
# CLAUDE.md.j2 tests
# ---------------------------------------------------------------------------

class TestClaudeMdTemplate:
    def setup_method(self):
        self.output = render("CLAUDE.md.j2", CLAUDE_MD_CONTEXT)

    def test_renders_without_error(self):
        assert self.output

    def test_project_context_block(self):
        assert "myapp" in self.output
        assert "a sample web application for testing" in self.output
        assert "Python 3.11+ / FastAPI / PostgreSQL" in self.output
        assert "multi-tenant SaaS with organisation and workspace hierarchy" in self.output

    def test_session_modes_section_present(self):
        assert "## Session modes" in self.output

    def test_build_mode_present(self):
        assert "**Build mode**" in self.output
        assert "Build Phase N" in self.output
        assert "Build next story" in self.output
        assert "Continue building" in self.output

    def test_review_mode_present(self):
        assert "**Review mode**" in self.output
        assert "adversarial checker" in self.output

    def test_review_checklist_header(self):
        assert "## Review checklist" in self.output

    def test_custom_checklist_items_rendered(self):
        assert "HOOK PERFORMANCE" in self.output
        assert "PIPE CONTRACT" in self.output
        assert "SKILL ISOLATION" in self.output

    def test_universal_protected_files_item(self):
        assert "PROTECTED FILES" in self.output
        assert "hooks/" in self.output
        assert ".claude-plugin/plugin.json" in self.output

    def test_universal_story_scope_item(self):
        assert "STORY SCOPE" in self.output

    def test_universal_build_gate_item(self):
        assert "BUILD GATE" in self.output
        assert "uv run pytest" in self.output

    def test_review_output_format_section(self):
        assert "## Review output format" in self.output
        assert "PASS / FAIL" in self.output
        assert "CRITICAL" in self.output
        assert "HIGH" in self.output
        assert "MEDIUM" in self.output
        assert "LOW" in self.output

    def test_loop_breaker_section(self):
        assert "## Loop-breaker mode" in self.output
        assert "LOOP-BREAKER:" in self.output
        assert "first principles" in self.output

    def test_story_test_verification_section(self):
        assert "## Story test verification" in self.output
        assert "uv run pytest tests/pairmode/" in self.output


# ---------------------------------------------------------------------------
# CLAUDE.build.md.j2 tests
# ---------------------------------------------------------------------------

class TestClaudeBuildMdTemplate:
    def setup_method(self):
        self.output = render("CLAUDE.build.md.j2", CLAUDE_BUILD_MD_CONTEXT)

    def test_renders_without_error(self):
        assert self.output

    def test_project_name_in_title(self):
        assert "myapp" in self.output

    def test_session_modes_section(self):
        assert "## Session modes" in self.output
        assert "**Build mode**" in self.output
        assert "Build Phase N" in self.output

    def test_build_loop_steps(self):
        assert "## Build loop" in self.output
        assert "### Step 1" in self.output
        assert "### Step 2" in self.output
        assert "### Step 3" in self.output

    def test_spawn_builder_instruction(self):
        assert "Spawn the `builder` subagent" in self.output

    def test_spawn_reviewer_instruction(self):
        assert "Spawn the `reviewer` subagent" in self.output

    def test_checkpoint_sequence_section(self):
        assert "## Checkpoint sequence" in self.output

    def test_checkpoint_steps_present(self):
        assert "### 1. Build gate" in self.output
        assert "### 2. Security audit" in self.output
        assert "### 3. Intent review" in self.output
        assert "### 4. Tag the checkpoint" in self.output
        assert "### 5. Report" in self.output

    def test_build_command_substituted(self):
        assert "PATH=$HOME/.local/bin:$PATH uv run pytest tests/pairmode/ -x -q" in self.output

    def test_test_command_substituted(self):
        assert "PATH=$HOME/.local/bin:$PATH uv run pytest tests/ -x -q" in self.output

    def test_migration_command_present_when_provided(self):
        assert "uv run alembic upgrade head" in self.output
        assert "## Running migrations" in self.output

    def test_loop_breaker_section(self):
        assert "## Loop-breaker" in self.output
        assert "LOOP-BREAKER:" in self.output

    def test_rules_section(self):
        assert "## Rules" in self.output
        assert "Do not write code" in self.output

    def test_before_first_build_loop_section(self):
        assert "## Before the first build loop" in self.output
        assert "git log --oneline" in self.output


class TestClaudeBuildMdNoMigration:
    def setup_method(self):
        self.output = render("CLAUDE.build.md.j2", CLAUDE_BUILD_MD_NO_MIGRATION_CONTEXT)

    def test_migration_section_absent_when_empty(self):
        assert "## Running migrations" not in self.output
        assert "alembic" not in self.output

    def test_other_sections_still_present(self):
        assert "## Build loop" in self.output
        assert "## Checkpoint sequence" in self.output
