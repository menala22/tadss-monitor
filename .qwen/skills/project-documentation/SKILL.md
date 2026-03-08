---
name: project-documentation
description: >
  Manage living development documentation for a solo developer actively building
  a project. Use this skill whenever the user asks "what should I document",
  "update my docs", "log this bug", "add this to the backlog", "I just finished
  a feature", "what's next", "I made a decision", "let's start coding", "wrap
  up for today", "audit my docs", or any variant of starting/ending a session.
  Also triggers on: "write a changelog", "log what I did", "track this bug",
  "why did I decide X", "what have I built so far", "document this feature",
  "design this component", "how does X work", "spec out the data structure",
  "write a feature doc", "write a README", "update my README", "create a README".
  Use proactively after any feature completion, bug fix, env var addition, or
  technical decision — don't wait to be asked.
  This skill covers apps of any type: web, mobile, API, CLI, bots, scripts.
---

# Project Documentation Skill

Helps a solo developer maintain 7 living document types that cover project
progress, decisions, bugs, tasks, changes, feature design, and the project's
public face — updated continuously as the project evolves.

---

## The 7 Core Development Documents

| # | File | Purpose | Cadence |
|---|------|---------|---------|
| 1 | `README.md` | What it is, how to run it, how to configure it | When behavior, setup, or status changes |
| 2 | `docs/devlog.md` | What was done each session | Every session |
| 3 | `docs/tasks.md` | Backlog, in-progress, done | Ongoing |
| 4 | `docs/bugs.md` | Known bugs + troubleshooting notes | When found/fixed |
| 5 | `docs/decisions.md` | Why key choices were made | When a tech decision is made |
| 6 | `docs/changelog.md` | What changed between versions/milestones | After each feature or release |
| 7 | `docs/features/[feature-name].md` | Design + implementation record per feature | Draft before building, finalize after |

`README.md` lives at the repo root. Docs 2–6 are single files in `/docs`. Doc 7 is a **folder** — one file per feature in `docs/features/`. Every file has a `_Last updated: YYYY-MM-DD_` line.

### README vs the other docs
README is the **public face** — written for a reader (future-you, a collaborator, GitHub). It answers "what is this and how do I run it?" in under 5 minutes. It links *to* the other docs; it does not replace them. Keep it accurate and minimal — a README that describes features you haven't built yet is worse than none.

---

## Feature Doc Lifecycle

Feature docs follow a two-phase lifecycle:

```
PHASE 1 — Before building (Status: Draft)
  → Think through design, data structures, logic, open questions
  → Use it to plan, not just record

PHASE 2 — After building (Status: Done)
  → Update to reflect what was actually built
  → Capture any divergence from the original design
  → Add known limitations or follow-up tasks
```

This makes each feature doc both a **spec** and a **reference** — one document serves both purposes.

---

## Proactive Triggers — When to Update Docs

The agent should suggest a doc update in these moments **without being asked**:

| Moment | Action |
|--------|--------|
| Project is new with no README | Create README immediately using the minimal template |
| Start of coding session | Ask: "What are you working on today?" → pre-fill `tasks.md` |
| End of coding session | Prompt a 1-2 line `devlog.md` entry + update `tasks.md` status |
| User says "I'm going to build X" | Draft a feature doc in `docs/features/x.md` before writing code |
| Feature completed (user-visible) | Update README "What it does" + finalize feature doc + update `changelog.md` |
| Feature completed (internal only) | Finalize feature doc + update `changelog.md` — README likely unchanged |
| New `.env` variable added | Update README configuration table immediately |
| Setup/install step changes | Update README quick start immediately |
| Bug found | Add entry to `bugs.md` immediately |
| Bug fixed | Update `bugs.md` entry with resolution |
| Technical decision made | Add entry to `decisions.md` |
| User asks "what's next" | Read `tasks.md` and summarize open items |

---

## Step-by-Step Workflows

### Workflow A — Session Start

Use when the user says "let's start", "starting a session", "what should I work on".

**Step 1 — Read `tasks.md`**
Summarize: what's in progress, what's highest priority in the backlog.

**Step 2 — Confirm today's focus**
Ask: "What are you planning to work on today?" (one line is enough).

**Step 3 — Update `tasks.md`**
Move the chosen task(s) to `In Progress`. Add new tasks if mentioned.

**Step 4 — Note session start in `devlog.md`**
Add a new entry: `## YYYY-MM-DD` with one line: `Started: [task name]`.

---

### Workflow B — Session End

Use when the user says "done for today", "wrapping up", "end of session", "good session".

**Step 1 — Prompt a brief summary**
Ask: "What did you get done today? (1-2 lines is fine)"

**Step 2 — Append to `devlog.md`**
Under today's date entry, add: `Done: [summary]`. Keep it to 1-2 lines.

**Step 3 — Update `tasks.md`**
Move completed tasks to `Done`. Move unfinished tasks back to `Backlog` or leave `In Progress`.

**Step 4 — Check if changelog or decisions need updating**
Ask: "Did you complete a feature or make any tech decisions today?" If yes, trigger Workflow D or E.

---

### Workflow C — Bug Found or Fixed

Use when the user says "found a bug", "something's broken", "this isn't working", "fixed it", "resolved".

**On bug found — add to `bugs.md`:**
```
## BUG-[###]: [Short title]
- **Status**: Open
- **Found**: YYYY-MM-DD
- **Description**: [What's broken]
- **Reproduce**: [Steps or conditions that trigger it]
- **Impact**: [Low / Medium / High]
- **Notes**: [Any initial observations]
```

**On bug fixed — update the entry:**
```
- **Status**: Resolved
- **Resolved**: YYYY-MM-DD
- **Fix**: [What was changed to fix it]
```

Increment bug number (`BUG-001`, `BUG-002`, etc.) for easy reference.

---

### Workflow D — Feature Completed / Changelog Update

Use when a feature is done or the user says "I finished X", "that feature is working now".

**Step 1 — Add entry to `changelog.md`**
Use this format:
```
## [v0.x / Milestone name] — YYYY-MM-DD
### Added
- [Feature name]: [one-line description]
### Changed
- [What behavior changed]
### Fixed
- [Bug fixed, reference BUG-### if applicable]
```

**Step 2 — Close task in `tasks.md`**
Move the corresponding task to `Done` with the completion date.

**Step 3 — Check if README needs updating**
Ask these two questions:
- Does this change how the app is used or run? → Update "What it does" + "How it works"
- Does this add a new `.env` variable or setup step? → Update configuration table + quick start

If yes to either, trigger Workflow I.

---

### Workflow E — Technical Decision

Use when the user says "I decided to use X", "going with Y instead of Z", "I chose this approach because...".

**Step 1 — Add entry to `decisions.md`:**
```
## DEC-[###]: [Decision title]
- **Date**: YYYY-MM-DD
- **Decision**: [What was decided]
- **Alternatives considered**: [What else was on the table]
- **Rationale**: [Why this choice]
- **Consequences**: [What this means going forward]
```

Increment decision number (`DEC-001`, `DEC-002`, etc.).

**Step 2 — Cross-reference if relevant**
If the decision is tied to a bug fix or feature, add a reference note in the relevant `bugs.md` or `changelog.md` entry.

---

### Workflow F — Feature Doc: Draft Before Building

Use when the user says "I'm about to build X", "let's design this feature", "how should I structure X", "spec out the data model", "plan the fetch logic".

**Step 1 — Create the file**
Create `docs/features/[feature-name].md`. Use kebab-case: `telegram-alerts.md`, `data-fetcher.md`, `dashboard.md`.

**Step 2 — Fill in the Draft template**
Gather answers to these sections before writing any code:

```markdown
# Feature: [Feature Name]
_Status: Draft_
_Last updated: YYYY-MM-DD_

## What It Does
[1-2 sentence description of the feature's purpose and user-facing outcome]

## Data Structure
[Key data objects, fields, types. Can be a table, JSON shape, or prose.]

## Logic / Flow
[Step-by-step description of how it works: inputs → processing → outputs]

## Key Design Decisions
[Choices made upfront — link to DEC-### entries if relevant]

## Open Questions
[Things not yet decided. Resolve these before or during building.]

## Out of Scope
[What this feature deliberately does NOT do]
```

**Step 3 — Use it as a thinking tool**
Before touching code, ask: "Does this design make sense end-to-end?" 
If there are open questions, resolve them now — not mid-build.

**Step 4 — Add a task to `tasks.md`**
Create a corresponding task: `Build [feature name] — see docs/features/[name].md`.

---

### Workflow G — Feature Doc: Finalize After Building

Use when a feature is completed or the user says "I finished building X", "that's working now".

**Step 1 — Update Status**
Change `_Status: Draft_` → `_Status: Done_` and update the date.

**Step 2 — Record what actually got built**
Add a `## As Built` section below the draft content:

```markdown
## As Built
_Added after implementation — YYYY-MM-DD_

### What Changed from Design
[Any divergence from the original draft: different data structure, changed logic, cut scope]

### Final Data Structure
[Update if it changed during building]

### Known Limitations
[Edge cases not handled, known weaknesses, tech debt]

### Follow-up Tasks
[Things deferred — add these to tasks.md backlog too]
```

**Step 3 — Update `changelog.md`**
Add an entry referencing the feature doc: `See docs/features/[name].md for full design`.

**Step 4 — Link any related decisions**
If DEC-### entries were made during building, add references to them in the feature doc.

---

### Workflow I — README: Create or Update

Use when the user says "write a README", "update my README", "create a README", or when a README-triggering event occurs (new env var, changed setup, user-visible feature).

#### Creating a README from scratch

**Step 1 — Choose a style**
- **Minimal** (recommended for solo/private projects): What it does, quick start, configuration. ~30–50 lines. Low maintenance.
- **Full** (for shared or open-source projects): All 6 sections below. Self-contained.

**Step 2 — Gather inputs before writing**
Do NOT draft blindly. Collect: what the app does in one sentence, how to run it, all `.env` variables, current project status (WIP / stable / experimental).

**Step 3 — Draft using the template below**
Use the README template from the Output Formats section. Mark unknown fields with `<!-- TODO: -->`.

**Step 4 — Verify the quick start works end-to-end**
Every step in the quick start must be accurate. Missing a step costs 20 minutes when revisiting cold.

#### Updating an existing README

Apply only the sections affected by the change:

| What changed | Section to update |
|---|---|
| New user-visible feature | "What it does", "How it works" |
| New `.env` variable | Configuration table |
| New dependency or install step | Quick start |
| Project status changed | "Status / known issues" |
| New feature doc written | "How it works" → add link to `docs/features/` |

**Rule**: Update README the same session the change is made — never defer it.

---

### Workflow H — Audit Existing Docs

Use when the user says "audit my docs", "are my docs up to date", "what's missing".

**Step 1 — Inventory**
Check which of the 7 doc types exist. Flag each: ✅ Present | ⚠️ Stale | ❌ Missing.

**Step 2 — Check for staleness signals**
- `README.md`: describes features not yet built, or missing recently added env vars / setup steps?
- `devlog.md`: last entry older than a week while project is active?
- `tasks.md`: tasks stuck in "In Progress" with no recent update?
- `bugs.md`: open bugs with no activity or missing resolution notes?
- `changelog.md`: features in code not mentioned in changelog?
- `decisions.md`: recent tech choices not recorded?
- `docs/features/`: features being built without a doc? Draft docs never finalized?

**Step 3 — Output audit report**
Use the format in the Output Formats section below.

---

## Output Formats

### README.md (minimal style — recommended for solo projects)
```markdown
# [Project Name]
_Status: WIP | Stable | Experimental_
_Last updated: YYYY-MM-DD_

> [One sentence: what goes in, what comes out, what it does]

## Quick Start
1. Clone the repo
2. `cp .env.example .env` — fill in values (see Configuration below)
3. `pip install -r requirements.txt`
4. `python main.py` _(or however it runs)_

## Configuration
| Variable | Description | Example |
|----------|-------------|---------|
| `VAR_NAME` | What it controls | `example-value` |

## How It Works
[5–10 lines describing the main flow. Link to feature docs for detail.]
- [Component A] → does X → see [docs/features/component-a.md](docs/features/component-a.md)
- [Component B] → does Y → see [docs/features/component-b.md](docs/features/component-b.md)

## Project Structure
```
[file-or-folder]/   # one-line explanation
[file-or-folder]/   # one-line explanation
```

## Status / Known Issues
[Honest one-liner: "In active development", "Stable", or "X is not working yet"]
See [docs/bugs.md](docs/bugs.md) for open issues.
```

**What NOT to put in README** (link to these instead):
- Full feature designs → `docs/features/`
- Changelog history → `docs/changelog.md`
- Bug list → `docs/bugs.md`
- Architecture deep-dives → `docs/features/`

---

### devlog.md
```markdown
# Dev Log
_Last updated: YYYY-MM-DD_

## YYYY-MM-DD
Started: [task or focus area]
Done: [1-2 line summary of what was accomplished]

## YYYY-MM-DD
...
```

### tasks.md
```markdown
# Task Tracker
_Last updated: YYYY-MM-DD_

## In Progress
- [ ] [Task name] — started YYYY-MM-DD

## Backlog
- [ ] [Task name] — [optional priority: High / Med / Low]
- [ ] [Task name]

## Done
- [x] [Task name] — completed YYYY-MM-DD
```

### bugs.md
```markdown
# Bug Tracker
_Last updated: YYYY-MM-DD_

## BUG-001: [Short title]
- **Status**: Open | Resolved
- **Found**: YYYY-MM-DD
- **Resolved**: YYYY-MM-DD _(if resolved)_
- **Description**: ...
- **Reproduce**: ...
- **Fix**: ... _(if resolved)_
```

### decisions.md
```markdown
# Decision Log
_Last updated: YYYY-MM-DD_

## DEC-001: [Decision title]
- **Date**: YYYY-MM-DD
- **Decision**: ...
- **Alternatives considered**: ...
- **Rationale**: ...
- **Consequences**: ...
```

### changelog.md
```markdown
# Changelog
_Last updated: YYYY-MM-DD_

## [v0.2 / Milestone name] — YYYY-MM-DD
### Added
- ...
### Changed
- ...
### Fixed
- ...

## [v0.1 / Initial build] — YYYY-MM-DD
...
```

### docs/features/[feature-name].md
```markdown
# Feature: [Feature Name]
_Status: Draft | In Progress | Done_
_Last updated: YYYY-MM-DD_

## What It Does
[1-2 sentence purpose and outcome]

## Data Structure
[Key objects, fields, types — table or JSON shape]

## Logic / Flow
[Inputs → processing → outputs, step by step]

## Key Design Decisions
[Choices made — link DEC-### if applicable]

## Open Questions
[Unresolved items — clear before or during build]

## Out of Scope
[What this feature deliberately does NOT do]

---
## As Built
_Added after implementation — YYYY-MM-DD_

### What Changed from Design
[Divergence from original draft]

### Known Limitations
[Edge cases not handled, tech debt]

### Follow-up Tasks
[Deferred items — also add to tasks.md]
```

### Audit Report
```
## Documentation Audit — YYYY-MM-DD

| Doc | Status | Issue |
|-----|--------|-------|
| README.md             | ⚠️ Stale    | Missing 2 new env vars added last week |
| devlog.md             | ✅ Current  | — |
| tasks.md              | ⚠️ Stale    | 3 tasks stuck In Progress for 2 weeks |
| bugs.md               | ✅ Current  | — |
| decisions.md          | ❌ Missing  | — |
| changelog.md          | ⚠️ Stale    | v0.3 features not logged |
| features/ (4 files)   | ⚠️ Partial  | 2 Drafts never finalized |

### Top Actions
1. Update `README.md` — add missing env vars to configuration table
2. Create `decisions.md` — no decisions recorded yet
3. Finalize `features/telegram-alerts.md` and `features/data-fetcher.md` — still Draft
```

---

## Common Mistakes to Avoid

| Mistake | Why It Hurts | Fix |
|---------|-------------|-----|
| README describes features not yet built | Misleading when revisiting cold | README reflects current reality only |
| README contains full feature docs or changelogs | Gets too long, hard to maintain | Link to `docs/` — don't duplicate content |
| Not updating README when adding `.env` vars | Future-you spends 20 min hunting config | Update configuration table same session |
| Only updating docs at big milestones | Lose context on small decisions made weeks ago | Log at every session end |
| Writing long devlog entries | Becomes a chore, stops happening | Hard limit: 1-2 lines per session |
| Not numbering bugs/decisions | Can't cross-reference them | Always use BUG-### and DEC-### |
| Leaving bugs only in code comments | Invisible when reviewing docs cold | Always update `bugs.md` status |
| `tasks.md` becomes a graveyard | Hard to see what's actually active | Archive done items monthly to `docs/archive/tasks-YYYY-MM.md` |
| Skipping `decisions.md` for "obvious" choices | In 3 months, nothing is obvious | If you spent >10 min deciding, log it |
| Writing feature docs only after building | Misses the design-thinking value | Always draft before coding, even if rough |
| Never finalizing Draft feature docs | Doc stays inaccurate forever | Finalize within one session of completing the feature |
| One giant feature doc for the whole app | Too broad to be useful | One file per distinct feature or component |

---

## Quality Checklist

**README.md**
- [ ] Exists at repo root
- [ ] "What it does" matches current actual behavior (not aspirations)
- [ ] Quick start works end-to-end
- [ ] Every `.env` variable is listed in the configuration table
- [ ] Links to `docs/features/` for deeper detail rather than duplicating content
- [ ] Has a "Status / known issues" line that's honest

**Docs 2–6 (single files in `/docs`)**
- [ ] All 5 exist with `_Last updated: YYYY-MM-DD_`
- [ ] `devlog.md` has an entry for every active coding session
- [ ] `tasks.md` reflects actual current state (not wishful thinking)
- [ ] Every open bug in `bugs.md` has enough context to debug cold
- [ ] Every significant tech choice is in `decisions.md`
- [ ] `changelog.md` entry exists for every completed feature

**Feature docs (`docs/features/`)**
- [ ] Folder exists with one file per major feature
- [ ] Every feature doc is either `Draft` (pre-build) or `Done` (post-build) — none abandoned mid-state
- [ ] All `Done` feature docs have an `## As Built` section
