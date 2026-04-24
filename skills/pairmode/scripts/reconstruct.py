"""
reconstruct.py — Refresh docs/reconstruction.md from ideology.md and brief.md.

Reads docs/ideology.md and docs/brief.md from a target project and writes (or
refreshes) docs/reconstruction.md without requiring a full bootstrap.
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import click
import jinja2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

IDEOLOGY_PLACEHOLDER_MARKER = "_(not yet specified"


# ---------------------------------------------------------------------------
# HTML comment stripping
# ---------------------------------------------------------------------------

def _strip_html_comments(text: str) -> str:
    """Remove HTML comments (<!-- ... -->) from text."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Ideology parsing
# ---------------------------------------------------------------------------

def _extract_top_level_sections(text: str) -> dict[str, str]:
    """Split text by ## headings, returning {heading_text: body_text} mapping."""
    # Split on ## headings (not ###)
    parts = re.split(r"^(##\s+[^\n]+)$", text, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if re.match(r"^##\s+", chunk):
            heading = chunk.strip()
            body = parts[i + 1] if (i + 1) < len(parts) else ""
            sections[heading] = body
            i += 2
        else:
            i += 1
    return sections


def _extract_subsections(text: str) -> dict[str, str]:
    """Split text by ### headings, returning {heading_text: body_text} mapping."""
    parts = re.split(r"^(###\s+[^\n]+)$", text, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if re.match(r"^###\s+", chunk):
            heading = chunk.strip()
            body = parts[i + 1] if (i + 1) < len(parts) else ""
            sections[heading] = body
            i += 2
        else:
            i += 1
    return sections


def _bullet_lines(body: str) -> list[str]:
    """Extract bullet lines from body, skipping placeholders and empty lines."""
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(IDEOLOGY_PLACEHOLDER_MARKER):
            continue
        if stripped.startswith("- "):
            lines.append(stripped[2:])
        elif stripped.startswith("-"):
            lines.append(stripped[1:].strip())
    return lines


def _find_section(sections: dict[str, str], keyword: str) -> str:
    """Return body for section whose heading contains keyword (case-insensitive)."""
    keyword_lower = keyword.lower()
    for heading, body in sections.items():
        if keyword_lower in heading.lower():
            return body
    return ""


def parse_ideology(text: str) -> dict:
    """Parse ideology.md text into a context dict for the reconstruction template."""
    text = _strip_html_comments(text)

    # Extract project_name from first line: # Ideology — ProjectName
    project_name = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # e.g. "# Ideology — ProjectName" or "# Ideology - ProjectName"
            rest = re.sub(r"^#\s+", "", line)
            # strip "Ideology — " or "Ideology - " prefix
            rest = re.sub(r"^[Ii]deology\s*[—\-–]\s*", "", rest).strip()
            project_name = rest
            break

    top_sections = _extract_top_level_sections(text)

    # --- Core convictions ---
    convictions_body = _find_section(top_sections, "core convictions")
    convictions = _bullet_lines(convictions_body)

    # --- Value hierarchy ---
    value_hierarchy_body = _find_section(top_sections, "value hierarchy")
    value_hierarchy = _bullet_lines(value_hierarchy_body)

    # --- Accepted constraints ---
    constraints_body = _find_section(top_sections, "accepted constraints")
    constraints = []
    constraint_subsections = _extract_subsections(constraints_body)
    for sub_heading, sub_body in constraint_subsections.items():
        name = re.sub(r"^###\s*", "", sub_heading).strip()
        if name.startswith("_(not yet specified"):
            continue
        rule = ""
        rationale = ""
        for line in sub_body.splitlines():
            stripped = line.strip()
            if stripped.startswith("**Rule:**"):
                rule = stripped[len("**Rule:**"):].strip()
            elif stripped.startswith("**Rationale:**"):
                rationale = stripped[len("**Rationale:**"):].strip()
        constraints.append({"name": name, "rule": rule, "rationale": rationale})

    # --- Reconstruction guidance ---
    reconstruction_body = _find_section(top_sections, "reconstruction guidance")
    recon_subsections = _extract_subsections(reconstruction_body)

    must_preserve_body = _find_section(recon_subsections, "must preserve")
    must_preserve = _bullet_lines(must_preserve_body)

    should_question_body = _find_section(recon_subsections, "should question")
    should_question = _bullet_lines(should_question_body)

    free_to_change_body = _find_section(recon_subsections, "free to change")
    free_to_change = _bullet_lines(free_to_change_body)

    # --- Comparison basis ---
    comparison_body = _find_section(top_sections, "comparison basis")
    comparison_dimensions = []
    for line in comparison_body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(IDEOLOGY_PLACEHOLDER_MARKER):
            continue
        # Pattern: - **Name:** description
        m = re.match(r"^-\s+\*\*(.+?)\*\*:\s*(.+)$", stripped)
        if m:
            comparison_dimensions.append({"name": m.group(1), "description": m.group(2)})

    return {
        "project_name": project_name,
        "convictions": convictions,
        "value_hierarchy": value_hierarchy,
        "constraints": constraints,
        "must_preserve": must_preserve,
        "should_question": should_question,
        "free_to_change": free_to_change,
        "comparison_dimensions": comparison_dimensions,
    }


# ---------------------------------------------------------------------------
# brief.md parsing
# ---------------------------------------------------------------------------

def parse_brief(text: str) -> dict[str, str]:
    """Extract reconstruction_what and reconstruction_why from brief.md."""
    top_sections = _extract_top_level_sections(text)

    what = ""
    why = ""
    for heading, body in top_sections.items():
        heading_lower = heading.lower()
        if "what this project produces" in heading_lower:
            body = body.strip()
            if body and not body.startswith("_(not yet specified"):
                what = body
        elif "why it exists" in heading_lower:
            body = body.strip()
            if body and not body.startswith("_(not yet specified"):
                why = body

    return {"reconstruction_what": what, "reconstruction_why": why}


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def _render_reconstruction(context: dict) -> str:
    """Render the reconstruction.md.j2 template with context."""
    loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
    env = jinja2.Environment(
        loader=loader,
        undefined=jinja2.Undefined,
        keep_trailing_newline=True,
    )
    template = env.get_template("docs/reconstruction.md.j2")
    return template.render(**context)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False),
    default=".",
    help="Target project directory.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing docs/reconstruction.md without prompting.",
)
def reconstruct(project_dir: str, force: bool) -> None:
    """Refresh docs/reconstruction.md from ideology.md and brief.md."""

    resolved = Path(project_dir).resolve()

    # Path traversal guard (same as bootstrap/audit/sync)
    if len(resolved.parts) < 3 or not resolved.is_dir():
        click.echo(
            f"error: project-dir resolves to a suspicious path: {resolved}",
            err=True,
        )
        sys.exit(1)

    # Check ideology.md exists
    ideology_path = resolved / "docs" / "ideology.md"
    if not ideology_path.exists():
        click.echo(
            "error: docs/ideology.md not found in project. "
            "Run /anchor:pairmode bootstrap first, or create docs/ideology.md manually.",
            err=True,
        )
        sys.exit(1)

    # Parse ideology.md
    ideology_text = ideology_path.read_text(encoding="utf-8")
    ideology_ctx = parse_ideology(ideology_text)

    # Parse brief.md (optional)
    brief_path = resolved / "docs" / "brief.md"
    brief_ctx = {"reconstruction_what": "", "reconstruction_why": ""}
    if brief_path.exists():
        brief_text = brief_path.read_text(encoding="utf-8")
        brief_ctx = parse_brief(brief_text)

    # Build full render context
    context = {
        **ideology_ctx,
        **brief_ctx,
        "generated_date": datetime.date.today().isoformat(),
    }

    # Check if output already exists
    output_path = resolved / "docs" / "reconstruction.md"
    if output_path.exists() and not force:
        overwrite = click.confirm("docs/reconstruction.md already exists. Overwrite?")
        if not overwrite:
            sys.exit(0)

    # Render and write
    content = _render_reconstruction(context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    click.echo("✓ docs/reconstruction.md written.")


if __name__ == "__main__":
    reconstruct()
