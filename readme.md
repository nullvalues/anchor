Anchor — What We Designed
The Core Problem
AI coding agents start every session from zero. Planning decisions evaporate. Non-negotiables get violated in implementation. The code exists but the intent behind it lives nowhere the agent can read.

The Medical Metaphor
The project is the patient. Anchor maintains the chart.
MedicineAnchorPatientThe project / codebaseChartCanonical spec (spec.json per module)Known allergiesNon-negotiables — absolute prohibitionsTreatment historyLineage — decisions with claude --resume linksAttending physicianArchitect — briefs agent at session startMedical recordsHistorian — captures and maintains the chartNavigatorPair Partner — watches structural changes in real timeNurse + PharmacistValidator — checks implementation against spec
The key insight: a doctor who ignores the patient chart might prescribe something the patient is allergic to. An agent that ignores the spec might implement something the team already ruled out.

The Four Roles
Architect — fires at session start via /anchor:companion. Asks the developer what modules they're working on today (via AskUserQuestion with git-based suggestions), reads spec.json for those modules, injects them into agent context. The agent starts informed.
Historian — watches every planning conversation via the Stop hook. Extracts decisions, rules, tradeoffs in real time. Compares against the canonical spec — surfaces conflicts immediately in the sidebar. At session end, runs deep extraction and reconciles into the canonical spec.
Pair Partner — fires on every Write/Edit/MultiEdit via PostToolUse. Builds a running UML delta — what changed structurally in this session. Surfaces unexpected module boundary crossings and new dependencies.
Validator — checks what was just written against the spec's non-negotiables. Advisory only. Three conflict actions:

Snooze — drop silently
Record — write to conflicts_pending.json
Override — requires a typed reason, updates spec with lineage, archives old rule


The Canonical Spec
Each module has one spec.json:
json{
  "module": "auth-and-security",
  "summary": "JWT, OAuth, MFA, rate limiting...",
  "business_rules": ["All endpoints require JWT", "..."],
  "non_negotiables": ["Auth must never call billing directly"],
  "tradeoffs": [{"decision": "HS256 over RS256", "reason": "...", "accepted_cost": "..."}],
  "conflicts": [],
  "lineage": [{"session_id": "8fdc6432", "resume": "claude --resume 8fdc6432", ...}]
}
Key design decisions:

JSON not markdown — so programs can update it without parsing
summary is always rewritten — stays current
lineage is append-only — never modified, full audit trail with resume links
non-negotiables never auto-resolved — always requires developer decision


The Sidebar
A persistent terminal process. Single view, mode-switching:
Planning mode — shows live captures forming in real time, conflict alerts
Implementation mode — shows UML delta (which files changed, new dependencies) and spec violation alerts
╭──────────────── anchor ─────────────────╮
│ ● PLANNING                               │
│ Loaded: auth-and-security, decision-ledger│
╰─────────────────────────────────────────╯
s=snooze  r=record  o=override

14:23:11 ← stop event, extracting...
✅ JWT must include company_id scope
⚠️  implicit: WebAuthn as primary MFA — confirm?

The Two Commands
/anchor:seed — run once per product. Bootstraps the canonical spec from scratch:

Interactive setup (product name, which repos, where spec lives)
Module discovery (reads codebase, identifies 5-15 modules)
Spec writing (parallel subagents analyze each module, main agent writes spec.json)
Session mining (reads all historical Claude Code transcripts, extracts past decisions)
Reconcile (merges everything into canonical spec with full lineage)

/anchor:companion — run at the start of every session:

Ask what modules to load (AskUserQuestion with git suggestions)
Read spec.json for selected modules
Save to state.json
Start the sidebar in a new terminal window


Hook Architecture
All hooks are thin relays — no API calls, exit in milliseconds. The sidebar does all heavy work.
HookRoleWhat it doesStopHistorianRelay to sidebar for incremental extractionPermissionRequest (ExitPlanMode)—Flip mode to implementationPostToolUse (Write/Edit/MultiEdit)Pair Partner + ValidatorFile change → sidebar for UML delta + spec checkSessionEndHistorianSignal sidebar: final extraction + reconcile

Plugin Structure
anchor/
  .claude-plugin/
    plugin.json        ← name: "anchor"
  skills/
    seed/              ← /anchor:seed
    companion/         ← /anchor:companion
  hooks/
    hooks.json
    stop.py
    exit_plan_mode.py
    post_tool_use.py
    session_end.py
