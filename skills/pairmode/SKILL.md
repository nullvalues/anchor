---
name: anchor:pairmode
description: Bootstrap, audit, sync, and manage pairmode methodology for this project.
allowed-tools: AskUserQuestion, Bash, Read, Write
---

# anchor:pairmode

Manage the pairmode methodology lifecycle for a project — from initial scaffolding through ongoing
audit, sync, and lesson capture.

---

## Commands

### `/anchor:pairmode bootstrap`

**When to use:** When starting pairmode on a new or existing project for the first time, or when
re-scaffolding a project after a major methodology revision.

**Inputs expected:**
- `.companion/product.json` in the target project — used to populate project-specific values in
  the scaffold (project name, description, tech stack, team conventions).
- The project's Anchor spec (`openspec/specs/`) if available — used to derive non-negotiables
  for the deny list in `.claude/settings.json`.
- Target project root path (prompted if not provided).

**What it does:**
1. Reads `.companion/product.json` from the target project.
2. Reads the project's Anchor spec if available; falls back to blank-slate defaults if not.
3. Renders all Jinja2 templates in `skills/pairmode/templates/` against the project context.
4. Generates the deny list in `.claude/settings.json` from spec non-negotiables, each rule
   annotated with a comment linking it to the source non-negotiable.
5. Presents the full list of files that will be written and prompts for confirmation before
   writing anything.
6. Writes the scaffold only after explicit user approval.
7. Records `pairmode_version` in `.companion/state.json` for future audit comparisons.

**Outputs:**
- `CLAUDE.md` and `CLAUDE.build.md` at project root.
- `docs/architecture.md`, `docs/phase-prompts.md`, `docs/checkpoints.md`.
- `.claude/agents/builder.md`, `reviewer.md`, `loop-breaker.md`, `security-auditor.md`,
  `intent-reviewer.md`.
- `.claude/settings.json` with spec-derived deny list.
- `.companion/state.json` with `pairmode_version` set.

---

### `/anchor:pairmode audit`

**When to use:** Periodically, or before a sync, to understand how far a project's pairmode
scaffold has drifted from the current canonical methodology.

**Inputs expected:**
- `.companion/state.json` in the target project — must contain `pairmode_version`.
- Target project root path (prompted if not provided).

**What it does:**
1. Reads `pairmode_version` from `.companion/state.json`.
2. Loads the current canonical templates from `skills/pairmode/templates/`.
3. Loads applicable lessons from `anchor/lessons/lessons.json` whose `affects` field matches
   this project's attributes.
4. Renders canonical templates against the project's current context.
5. Diffs the rendered output against the project's existing scaffold files.
6. Produces a structured audit report: files that differ, sections that differ, lessons not yet
   incorporated, and a recommended action for each delta.

**Outputs:**
- A human-readable audit report printed to the session, summarizing all deltas and recommended
  actions. No files are written.

---

### `/anchor:pairmode sync`

**When to use:** After reviewing an audit report and deciding to incorporate upstream methodology
changes into the project.

**Inputs expected:**
- Audit report from a preceding `/anchor:pairmode audit` run (or the user confirms a fresh audit
  should be run first).
- Target project root path.
- User confirmation of which deltas to apply (all, or a selected subset).

**What it does:**
1. Runs (or reuses) an audit to identify deltas.
2. For each selected delta, applies the canonical update to the project file while preserving
   project-specific content in designated customisation zones (marked in templates with
   `{# PROJECT_CUSTOM #}` blocks).
3. Presents each proposed change to the user before writing.
4. Writes approved changes and updates `pairmode_version` in `.companion/state.json`.

**Outputs:**
- Updated scaffold files in the target project.
- Updated `pairmode_version` in `.companion/state.json`.
- A sync summary listing every file changed.

---

### `/anchor:pairmode lesson`

**When to use:** At the end of a session (or any time) when a meaningful methodology insight has
emerged — a workflow problem solved, a pattern discovered, a failure mode identified.

**Inputs expected (prompted interactively via AskUserQuestion, or as CLI arguments):**
- **trigger** — what situation or event prompted this lesson.
- **problem** — what went wrong or was inefficient.
- **learning** — the insight or corrective pattern.
- **methodology_change** — how the methodology (templates, process, tooling) should change as
  a result.
- **affects** — which components are affected (e.g. `reviewer_checklist`, `builder_agent`).
- **applies_to** — which project types this applies to (e.g. `all`, `python`, `typescript`).
- **source_project** — (optional) the project that produced this lesson; defaults to `unknown`.

**What it does:**
1. Loads the current `anchor/lessons/lessons.json`.
2. Generates the next sequential lesson ID (L001, L002, …).
3. Constructs a lesson entry with `id`, `date` (today), `source_project`, `trigger`, `problem`,
   `learning`, `methodology_change` (with `affects` and `description`), `applies_to`, and
   `status: captured`.
4. Appends the entry to `anchor/lessons/lessons.json` via `lesson_utils.save_lessons()`, which
   enforces the append-only invariant (existing entries may only have `status` changed).
5. Calls `lesson_utils.generate_lessons_md()` and writes the result to `lessons/LESSONS.md`.
6. Returns the captured lesson dict and prints a confirmation with the lesson `id`.

**Lesson schema written to lessons.json:**
```json
{
  "id": "L001",
  "date": "YYYY-MM-DD",
  "source_project": "project name or 'unknown'",
  "trigger": "...",
  "problem": "...",
  "learning": "...",
  "methodology_change": {
    "affects": ["reviewer_checklist"],
    "description": "..."
  },
  "applies_to": ["all"],
  "status": "captured"
}
```

**CLI invocation (for testing and direct use):**
```bash
uv run python skills/pairmode/scripts/lesson.py \
  --trigger "Builder skipped tests" \
  --problem "Tests failed after story was marked done." \
  --learning "Always run tests before marking a story done." \
  --methodology-change "Add test gate to builder checklist." \
  --affects reviewer_checklist \
  --affects builder_agent \
  --applies-to all \
  --source-project my-project
```

**Outputs:**
- New entry appended to `anchor/lessons/lessons.json`.
- `lessons/LESSONS.md` regenerated from the updated lessons store.
- Confirmation message with the lesson `id` printed to stdout.

---

### `/anchor:pairmode review`

**When to use:** When enough lessons have accumulated to warrant a methodology update cycle —
typically before a major bootstrap or sync campaign across projects.

**Inputs expected:**
- `anchor/lessons/lessons.json` — must exist with at least one `status: active` lesson.
- User approval for each proposed template change.

**What it does:**
1. Loads all lessons with `status: active` from `anchor/lessons/lessons.json`.
2. Groups lessons by their `affects` field to identify patterns across project types.
3. For each group, proposes specific, minimal template updates that incorporate the learning.
4. Presents each proposed change to the user with the source lesson(s) and rationale.
5. Writes approved template updates to `skills/pairmode/templates/`.
6. Updates the `status` of incorporated lessons to `incorporated` in `lessons.json`.
7. Increments the canonical `pairmode_version` if any templates were updated.

**Outputs:**
- Updated Jinja2 templates in `skills/pairmode/templates/`.
- Updated `status` fields in `anchor/lessons/lessons.json`.
- Updated canonical `pairmode_version`.
- A review summary listing every change made.
