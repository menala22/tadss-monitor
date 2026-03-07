# Claude Skills — Solo Developer Usage Guide

A practical reference for setting up, loading, and using Claude Code skills
efficiently in day-to-day development.

_Last updated: 2026-03-07_

---

## What Is a Skill?

A skill is a `SKILL.md` file that teaches Claude how to handle a recurring
task reliably — like maintaining project docs, following coding standards, or
writing commit messages. Think of it as a standing operating procedure (SOP)
that Claude reads before tackling that type of task.

Skills are stored in your repo under `.claude/skills/` and registered in
`CLAUDE.md` so Claude picks them up automatically every session.

---

## How Skills Load (The 3-Level System)

Understanding this prevents over-engineering and token anxiety:

| Level | What loads | Always in context? | Size |
|-------|-----------|-------------------|------|
| 1 | Skill name + description | ✅ Yes, every session | ~100 words per skill |
| 2 | Full SKILL.md body | Only when triggered by relevance | < 500 lines |
| 3 | Reference files in `skills/[name]/references/` | On demand only | Unlimited |

**Key insight**: If you have 8 skills, you're paying for ~800 words of
descriptions constantly — not 8 full documents. Full skill bodies only load
when Claude decides they're relevant to what you're doing.

---

## Folder Structure

```
your-project/
├── CLAUDE.md                          ← session context, modes, skill registry
├── README.md
├── docs/                              ← your project documentation
└── .claude/
    └── skills/
        ├── project-documentation/
        │   └── SKILL.md
        ├── coding-standards/
        │   └── SKILL.md
        ├── git-workflow/
        │   └── SKILL.md
        └── debugging/
            └── SKILL.md
```

Skills travel with the repo. Any collaborator (or future-you on a new machine)
gets the same agent behavior automatically.

---

## Setting Up CLAUDE.md

`CLAUDE.md` is the most important file for controlling Claude's behavior. It
lives at the repo root and is read at the start of every session. At minimum,
include two blocks:

### Block 1 — Skill Registry

Tells Claude which skills exist and when to use them:

```markdown
## Skills

- **project-documentation** — `.claude/skills/project-documentation/SKILL.md`
  Manages all dev docs: README, devlog, tasks, bugs, decisions, changelog,
  feature docs. Use at session start/end, after features, bugs, decisions.

- **coding-standards** — `.claude/skills/coding-standards/SKILL.md`
  Code style, naming conventions, patterns for this project.

- **git-workflow** — `.claude/skills/git-workflow/SKILL.md`
  Commit message format, branching rules, PR conventions.

- **debugging** — `.claude/skills/debugging/SKILL.md`
  Systematic debug approach, logging conventions, common failure patterns.
```

### Block 2 — Session Modes

Named shortcuts that scope which skills are active for a session:

```markdown
## Session Modes

Declare a mode at the start of each session:

- **build mode**  → coding-standards + project-documentation
- **doc mode**    → project-documentation only
- **debug mode**  → debugging + project-documentation (bugs workflow only)
- **plan mode**   → project-documentation (feature drafting only)
- **review mode** → coding-standards (code review focus)
```

---

## How to Start a Session

### Option A — Declare a mode (recommended for focused sessions)
```
Build mode — working on the Telegram alert feature today
```
```
Doc mode — catching up on documentation, need to finalize 2 feature docs
```
```
Debug mode — the scheduler is skipping jobs intermittently
```

### Option B — Natural language (Claude auto-selects skill)
```
Let's start a session
```
```
Wrapping up for today
```
Claude reads your `CLAUDE.md` session modes and skill registry, so it knows
the right context without you spelling it out.

---

## Three Ways to Invoke Skills

### 1. Automatic (passive) — best for routine moments

Just talk naturally. Well-written skill descriptions trigger automatically:

| What you say | Skill that fires |
|---|---|
| `Found a bug — scheduler skipping 9am job` | project-documentation → bugs workflow |
| `I decided to use APScheduler over cron` | project-documentation → decisions workflow |
| `Wrapping up for today` | project-documentation → session-end workflow |
| `I'm about to build the alert feature` | project-documentation → feature doc draft |

No special syntax. The skill's description handles the routing.

---

### 2. Mode declaration (active) — best for full sessions

One word at session start scopes the entire session:

```
Build mode — building the data fetcher today
```

From that point, Claude stays within `coding-standards` + `project-documentation`
for the whole session without needing reminders.

---

### 3. Inline call (surgical) — best for one-off tasks mid-session

When you want one specific skill for one specific task:

```
Use the project-documentation skill to log this decision:
I chose pandas over polars because of better TA-Lib compatibility
```

```
Use the git-workflow skill to write a commit message for these changes
```

Invokes the skill for that task only, then returns to normal flow.

---

## How Many Skills to Load

### Token impact
- **Descriptions** (always loaded): ~100 words × number of skills
- **Full skill bodies** (loaded when triggered): ~200–400 lines each
- **Simultaneous full bodies**: 1–3 is normal; 4+ is a heavy session

### Practical limits

| Skills active simultaneously | Assessment |
|------------------------------|------------|
| 1–3 | ✅ Normal, negligible impact |
| 4–6 | ⚠️ Noticeable token use, fine for complex sessions |
| 7+ | ❌ Split into separate focused sessions |

### Recommended skill count per project

For a solo dev project, **4–6 skills** is the sweet spot:

```
.claude/skills/
├── project-documentation/   ← always useful
├── coding-standards/        ← active in build mode
├── git-workflow/            ← active when committing
└── debugging/               ← active in debug mode
```

### The real risk: dilution, not slowness

Token cost is minor. The bigger risk with too many skills is **ambiguity** —
if two skill descriptions overlap, Claude may apply the wrong one or hesitate.
One sharp, well-scoped skill beats three vague overlapping ones every time.

---

## Day-to-Day Workflow Example

```
You:    "Build mode — working on alert trigger logic today"
Claude: Reads CLAUDE.md → activates coding-standards + project-documentation
        Checks tasks.md → summarises what's in progress
        Asks: "What are you planning to work on today?"

--- (coding happens) ---

You:    "Found a bug — RSI returning None on missing candles"
Claude: Auto-triggers project-documentation bugs workflow
        Creates BUG-003 entry in docs/bugs.md

--- (bug fixed) ---

You:    "Fixed it — added a None guard in calculate_rsi()"
Claude: Updates BUG-003 status to Resolved, adds fix description

--- (feature done) ---

You:    "Alert trigger feature is working"
Claude: Prompts to finalize feature doc + update changelog + check README

--- (end of day) ---

You:    "Wrapping up"
Claude: Asks for 1-2 line devlog summary
        Updates tasks.md statuses
        Asks: "Any tech decisions or features completed today?"
```

---

## Quick Reference Card

```
SETUP
  Skills live in:      .claude/skills/[skill-name]/SKILL.md
  Register in:         CLAUDE.md → Skills block
  Define modes in:     CLAUDE.md → Session Modes block

LOADING
  Descriptions:        Always in context (Level 1)
  Full skill body:     Loaded when relevant (Level 2)
  Reference files:     Loaded on demand (Level 3)

INVOKING
  Automatic:           Just talk naturally — descriptions handle routing
  Mode declaration:    "Build mode" / "Doc mode" / "Debug mode" at session start
  Inline call:         "Use the [skill-name] skill to..." for one-off tasks

LIMITS
  Sweet spot:          4–6 skills per project
  Simultaneous:        1–3 full skill bodies active at once
  Main risk:           Overlapping descriptions → ambiguity, not token cost

SESSION PATTERN
  Start:    "[mode] — [today's focus]"
  During:   Talk naturally, skills auto-trigger
  End:      "Wrapping up"
```

---

## Troubleshooting

**Skill isn't triggering automatically**
→ Description is too vague. Add more specific trigger phrases. Make it "pushier".

**Wrong skill fires for a task**
→ Two skill descriptions overlap. Narrow the scope of one or both.

**Claude seems to forget the skill mid-session**
→ Context window got long. Re-declare the mode: `"Reminder: we're in build mode"`.

**Sessions feel slow or expensive**
→ Too many full skill bodies loaded at once. Use tighter mode declarations to
scope which skills are active.

**Skill works once then stops being applied**
→ Check that the skill body is under 500 lines. Oversized skills get
de-prioritised. Move overflow content to `references/` files.
