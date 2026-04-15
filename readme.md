<p align="center">
<pre>
        ◉
       ━┿━
        │
        │
    ╭╴  │  ╶╮
     ╰╮ │ ╭╯
      ╰─┴─╯
</pre>
</p>

<h1 align="center">Anchor</h1>
<p align="center">
A context companion plugin for <a href="https://claude.ai/code">Claude Code</a><br/>
Persistent memory of decisions, specs, and architectural constraints across sessions.
</p>

---

## The Problem

AI coding agents start every session from zero. Planning decisions evaporate. Non-negotiables get violated in implementation. The code exists but the intent behind it lives nowhere the agent can read.

**Anchor is the patient chart that every agent reads before touching a single file** — and that every planning session writes into before implementation begins.

## How It Works

Anchor maintains a **canonical spec** for your product — a structured JSON record of what was decided, what must never be violated, and what tradeoffs were accepted. Four roles work together across your sessions:

| Role | When | What it does |
|---|---|---|
| **Architect** | Session start | Loads relevant specs into agent context |
| **Historian** | Every agent response | Extracts decisions, surfaces conflicts in real time |
| **Pair Partner** | Every file write | Tracks structural changes, flags boundary crossings |
| **Validator** | Every file write | Checks code against non-negotiables |

All of this runs in a **companion sidebar** — a separate terminal window that watches your Claude Code session and provides continuous feedback.

## Installation

```bash
# Add the marketplace
/plugin marketplace add nraychaudhuri/anchor

# Install the plugin
/plugin install anchor@nraychaudhuri-anchor
```

For development:
```bash
claude --plugin-dir /path/to/anchor
```

### First-time setup

```bash
# 1. Bootstrap the canonical spec (run once per product)
/anchor:seed

# 2. Start the companion for each session
/anchor:companion
```

The first time the companion sidebar starts, it will generate an OAuth token using your existing Claude subscription (no extra cost).

## The Two Commands

### `/anchor:seed` — Bootstrap (run once)

Reads your entire codebase and all historical Claude Code sessions to build the canonical spec from scratch:

1. **Setup** — Product name, repos, spec location
2. **Module discovery** — Identifies 5-15 major modules from your codebase
3. **Spec writing** — Parallel agents analyze each module
4. **Session mining** — Extracts decisions from all past Claude Code transcripts
5. **Reconcile** — Merges everything into canonical `spec.json` files with full lineage

### `/anchor:companion` — Start session (run every time)

1. **Module selection** — Asks what you're working on (with git-based suggestions)
2. **Recovery check** — Detects unreconciled sessions from previous runs
3. **Spec loading** — Reads `spec.json` for selected modules into agent context
4. **Sidebar launch** — Opens the companion in a new terminal window

## The Canonical Spec

Each module has one `spec.json`:

```json
{
  "module": "auth-and-security",
  "summary": "JWT, OAuth, MFA, rate limiting. All API access requires authentication.",
  "business_rules": [
    "All API endpoints except /public require a valid JWT",
    "JWT must include company_id for multi-tenant routing"
  ],
  "non_negotiables": [
    "Auth must never call billing directly — events only",
    "Google refresh tokens must be stored encrypted, never plaintext"
  ],
  "tradeoffs": [
    {
      "decision": "HS256 over RS256 for JWT signing",
      "reason": "Simpler at current scale",
      "accepted_cost": "Cannot verify tokens without the shared secret"
    }
  ],
  "conflicts": [],
  "lineage": [
    {
      "session_id": "8fdc6432-...",
      "summary": "Auth design session — JWT structure and MFA",
      "date": "2026-03-15",
      "resume": "claude --resume 8fdc6432-..."
    }
  ]
}
```

**Design principles:**
- **JSON not markdown** — programs can update it without parsing
- **Summary is always rewritten** — stays current with each reconcile
- **Lineage is append-only** — full audit trail with `claude --resume` links
- **Non-negotiables never auto-resolve** — always require a developer decision

## The Companion Sidebar

A persistent terminal window that watches your Claude Code session:

```
        ◉
       ━┿━     Anchor v0.1.0
        │      context companion
        │
    ╭╴  │  ╶╮
     ╰╮ │ ╭╯
      ╰─┴─╯

╭──────────────────────── Specs ────────────────────────╮
│   auth-and-security                                    │
│   JWT, OAuth, MFA, rate limiting...                    │
│   decision-ledger                                      │
│   Financial memory and reasoning layer...              │
│                                                        │
│ key points:                                            │
│   🔒 Auth must never call billing directly             │
│   🔒 Twin Objects are append-only                      │
╰────────────────────────────────────────────────────────╯

14:23:11 ← stop event, extracting...
14:23:15 ✓ 2 capture(s)
  • JWT must include company_id scope
  ⚖️ HS256 chosen — cost: shared secret required

╭─────────────── anchor ────────────────╮
│  auth ● ──→ decision-ledger ●         │
│                                       │
│  → jwt_handler.py [auth]              │
│  → claims.py [decision-ledger]        │
╰───────────────────────────────────────╯
```

### What you see

- **Specs panel** — loaded modules with key points (non-negotiables) always visible
- **Extraction results** — decisions, rules, tradeoffs captured from each conversation turn
- **Live chart** — module sequence diagram showing which modules are being touched
- **Conflict alerts** — when something violates a non-negotiable

### Conflict actions

When a conflict is detected:

- **`s`** — Snooze (dismiss, you're aware)
- **`r`** — Record (save to `conflicts_pending.json` with optional note)
- **`o`** — Override (requires a reason, updates the spec, archives the old rule)

## Hook Architecture

All hooks are thin relays — no API calls, exit in milliseconds. The sidebar does all heavy work asynchronously.

| Hook | Trigger | Role | What it does |
|---|---|---|---|
| `stop.py` | After each agent response | Historian | Relay to sidebar for incremental extraction |
| `exit_plan_mode.py` | Plan approved | Historian | Send plan content for impact analysis |
| `post_tool_use.py` | File written/edited | Pair Partner | File change to sidebar for module tracking |
| `session_end.py` | Session closes | — | Signal sidebar to show summary and exit |

## Data Flow

```
Planning conversation
    ↓
Stop hook → sidebar → LLM extraction → captures displayed
    ↓
persist_capture() → incremental.json (saved immediately per capture)
    ↓
Session ends → sidebar shows summary + exits
    ↓
Next /anchor:companion → detects unreconciled sessions → reconciles into spec.json
```

No data loss at any point. If the session crashes, captures are already on disk.

## Directory Structure

```
anchor/
  .claude-plugin/
    plugin.json              ← plugin manifest
  skills/
    seed/
      SKILL.md               ← /anchor:seed
      requirements.txt
      references/
        openspec_format.md   ← spec.json format reference
      scripts/
        setup.py             ← product config writer
        mine_sessions.py     ← transcript decision extractor
        reconcile.py         ← spec merger
    companion/
      SKILL.md               ← /anchor:companion
      requirements.txt
      scripts/
        sidebar.py           ← companion sidebar process
        start_sidebar.sh     ← shell launcher
        launch_sidebar.command  ← macOS Terminal launcher + OAuth setup
  hooks/
    hooks.json               ← hook configuration
    stop.py                  ← Historian: incremental capture
    exit_plan_mode.py        ← plan content relay
    post_tool_use.py         ← Pair Partner: file tracking
    session_end.py           ← session close signal
```

### Runtime files (not in plugin, created at runtime)

```
~/.anchor/
  auth.json                  ← OAuth token (generated on first run)

<project>/.companion/
  state.json                 ← current session state
  product.json               ← pointer to product config
  modules.json               ← module registry

<spec_location>/openspec/
  specs/<module>/spec.json   ← canonical spec per module
  changes/<session-id>/
    extraction.json          ← transcript-mined decisions
    incremental.json         ← sidebar-captured decisions
    proposal.md              ← human-readable session summary
    design.md                ← tradeoffs and decisions
```

## Requirements

- [Claude Code](https://claude.ai/code) CLI installed
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- macOS (sidebar uses Terminal.app; Linux support planned)

## License

MIT

---

*Built by [Nilanjan Roy](https://github.com/nilanjan) — March 2026*
