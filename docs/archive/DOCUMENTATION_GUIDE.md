# Documentation Best Practices Guide

> **For Non-Technical Stakeholders** – Simple, practical guide to keeping project documentation up-to-date without overwhelm.

**Version:** 1.0  
**Last Updated:** 2026-02-27  
**Time Commitment:** ~25 minutes per week

---

## 🎯 The Golden Rule

> **Document for your future self, not for auditors.**

You're not writing a novel. You're leaving breadcrumbs so Future-You doesn't get lost.

---

## 📚 The 4-Document System

You only need **4 documents** to run a professional software project:

```
┌─────────────────────────────────────────────────────────────┐
│  1. README.md        → "What is this?"                     │
│  2. PROJECT_STATUS.md → "Where are we?"                     │
│  3. CHANGELOG.md     → "What changed?"                      │
│  4. API_DOCS.md      → "How do I use it?" (optional)        │
└─────────────────────────────────────────────────────────────┘
```

### Why These Four?

| Document | Answers | Reader |
|----------|---------|--------|
| README.md | What does this do? | New people, investors |
| PROJECT_STATUS.md | Are we on track? | Team, management |
| CHANGELOG.md | What's new? | Everyone |
| API_DOCS.md | How do I call this? | Developers, users |

---

## 📝 Document-by-Document Guide

### 1. README.md (The Front Page)

**Purpose:** First impression. Explains the project in 2 minutes.

**Location:** `README.md` (project root)

**Update Frequency:** Monthly or after major milestones

---

#### What to Include

```markdown
# Project Name

## What Is This?
[One paragraph in plain English]

## Key Features
- Feature 1
- Feature 2
- Feature 3

## Quick Start (5 minutes)
1. Step one
2. Step two
3. Step three

## Current Status
- Progress: [X]%
- Tests: [X] passing

## Who To Contact
- Developer: [name]
- Questions: [email]
```

---

#### When to Update

| Trigger | Action | Time |
|---------|--------|------|
| Project kickoff | Create initial version | 30 min |
| Major feature completed | Update feature list | 5 min |
| Progress milestone (25%, 50%, 75%) | Update progress badge | 2 min |
| Contact info changes | Update contact section | 1 min |

---

#### Example from Your Project

```markdown
# TA-DSS: Post-Trade Position Monitoring System

> Technical Analysis Decision Support System for monitoring trades.

**Status:** 🟢 ~75% Complete  
**Tests:** 56 passing (100%)

## What Is This?
TA-DSS helps traders who execute trades manually on external exchanges
and want automated monitoring with technical analysis signals.

## Key Features
✅ Position Logging – Log trades after execution
✅ Technical Analysis – RSI, MACD, EMA calculations
✅ Signal Generation – BULLISH/BEARISH/NEUTRAL signals
🚧 Telegram Alerts – Coming soon
🚧 Dashboard – Coming soon
```

---

### 2. PROJECT_STATUS.md (The Dashboard)

**Purpose:** Know progress without status meetings.

**Location:** `PROJECT_STATUS.md` (project root)

**Update Frequency:** Weekly (Friday recommended)

---

#### What to Include

```markdown
# Project Status

**Last Updated:** [Date]
**Overall Progress:** [X]%

## ✅ Completed This Week
- Item 1
- Item 2

## 🚧 In Progress
- Item 1 (50% done)
- Item 2 (waiting on X)

## 📋 Next Week's Goals
- Goal 1
- Goal 2

## 🚨 Blockers/Issues
- Issue 1 (who is fixing, by when)

## 📊 Progress by Area
| Area | Progress |
|------|----------|
| Backend | 85% |
| Frontend | 40% |
| Testing | 60% |
```

---

#### When to Update

| Trigger | Action | Time |
|---------|--------|------|
| End of week (Friday) | Weekly status update | 10 min |
| Complete a feature | Move to "Completed" section | 2 min |
| Start a new task | Add to "In Progress" | 1 min |
| Hit a blocker | Document in "Blockers" | 2 min |
| Before status meetings | Quick review | 5 min |

---

#### Weekly Update Template

Copy this every Monday and fill in:

```markdown
## Week of [Date]

### Goals for This Week
- [ ] Complete [feature]
- [ ] Start [feature]
- [ ] Fix [bug]

### Status Check
- On track: Yes/No
- Blockers: [list or "none"]
- Need help with: [list or "nothing"]
```

---

### 3. CHANGELOG.md (The History Book)

**Purpose:** Track what changed and when. No guessing.

**Location:** `CHANGELOG.md` (project root)

**Update Frequency:** After each task (2 minutes)

---

#### What to Include

```markdown
# Changelog

## [Unreleased]
- New features in development

## [YYYY-MM-DD]
### Added
- New features

### Fixed
- Bug fixes

### Changed
- Modifications

### Removed
- Deleted features
```

---

#### When to Update

| Trigger | Action | Time |
|---------|--------|------|
| Complete a coding task | Add one line | 2 min |
| Fix a bug | Add one line | 2 min |
| Before release | Review and finalize | 10 min |
| End of week | Move to dated section | 2 min |

---

#### Label Guide

| Label | Use When |
|-------|----------|
| `Added` | New feature, new file, new capability |
| `Fixed` | Bug fix, error correction |
| `Changed` | Modified existing feature |
| `Removed` | Deleted feature or file |
| `Security` | Security-related changes |

---

#### Example Entries

```markdown
## [2026-02-27]
### Added
- Technical analysis module with RSI, MACD, EMA
- Signal engine for position health evaluation
- 56 unit tests (all passing)
- Data fetcher with retry logic

### Fixed
- Timeframe validation for h4 on yfinance
- Database connection cleanup on close

### Changed
- Updated API response format for positions
```

---

### 4. API_DOCS.md (The User Manual) – Optional

**Purpose:** Help developers use your API.

**Location:** `API_DOCS.md` (project root)

**Update Frequency:** When API changes

---

#### What to Include

```markdown
# API Documentation

## Base URL
`http://localhost:8000`

## Authentication
[How to get API key/token]

## Endpoints

### [Endpoint Name]
**METHOD** `/path/to/endpoint`

**Request:**
```json
{ "field": "value" }
```

**Response:**
```json
{ "result": "success" }
```
```

---

#### When to Update

| Trigger | Action | Time |
|---------|--------|------|
| New endpoint added | Add endpoint section | 10 min |
| Request format changes | Update request example | 5 min |
| Response format changes | Update response example | 5 min |
| Authentication changes | Update auth section | 5 min |

---

## 📅 Your Documentation Schedule

### Weekly Routine (25 minutes total)

| Day | Task | Document | Time |
|-----|------|----------|------|
| **Monday** | Review status, set goals | PROJECT_STATUS.md | 5 min |
| **Wednesday** | Quick progress check | PROJECT_STATUS.md | 2 min |
| **Friday** | Weekly status update | PROJECT_STATUS.md | 10 min |
| **As needed** | Log completed tasks | CHANGELOG.md | 2 min each |
| **Monthly** | Review README accuracy | README.md | 15 min |

---

### Monthly Checklist

```
□ First Week:
  □ Review README.md – is progress accurate?
  □ Review PROJECT_STATUS.md – update milestones
  □ Archive last month's changelog entries

□ Mid Month:
  □ Check for outdated information
  □ Update contact info if needed
  □ Review blocker status

□ End of Month:
  □ Finalize CHANGELOG.md for the month
  □ Update progress percentages
  □ Plan next month's goals
```

---

## ✅ Quick Reference Cards

### Card 1: When I Complete a Feature

```
1. Open CHANGELOG.md
2. Add under [Unreleased]:
   - Added: [Feature name] – [one line description]
3. Open PROJECT_STATUS.md
4. Move feature from "In Progress" to "Completed"
5. Update progress percentage if needed

Total time: 5 minutes
```

---

### Card 2: When I Fix a Bug

```
1. Open CHANGELOG.md
2. Add under [Unreleased]:
   - Fixed: [Bug description] – [brief explanation]
3. Note in PROJECT_STATUS.md if it was a blocker

Total time: 3 minutes
```

---

### Card 3: Friday Status Update

```
1. Open PROJECT_STATUS.md
2. Update "Last Updated" date
3. Review "In Progress" – update percentages
4. Move completed items to "Completed This Week"
5. Add goals for next week
6. Note any new blockers

Total time: 10 minutes
```

---

### Card 4: Before a Demo/Meeting

```
1. Open README.md – check accuracy
2. Open PROJECT_STATUS.md – know current status
3. Open CHANGELOG.md – know what's new
4. Prepare 3 key points:
   - What we completed
   - What we're working on
   - What's next

Total time: 5 minutes
```

---

## 🚫 Common Mistakes (And How to Avoid Them)

### Mistake 1: Waiting Until "Perfect"

**Wrong:** "I'll document everything at the end"  
**Right:** "I'll document 2 minutes after each task"

**Why:** You'll forget details. Future-You will be angry.

---

### Mistake 2: Writing Essays

**Wrong:**
```markdown
## Progress Update

This week we worked extensively on the technical analysis module,
which involved significant research into various indicators including
RSI, MACD, and moving averages. After careful consideration...
[continues for 2 paragraphs]
```

**Right:**
```markdown
## ✅ Completed This Week
- Technical analysis module (RSI, MACD, EMA)
- 56 unit tests (all passing)
```

**Why:** Bullet points > paragraphs. Always.

---

### Mistake 3: Hiding Problems

**Wrong:**
```markdown
## 🚨 Blockers
None (everything is fine!)
```

**Right:**
```markdown
## 🚨 Blockers
- Telegram API rate limiting – investigating solutions (John, by Friday)
- Dashboard design pending approval – waiting on stakeholder (Sarah)
```

**Why:** Blockers are normal. Hiding them causes delays.

---

### Mistake 4: Updating Only One Document

**Wrong:** Only updating CHANGELOG.md, ignoring PROJECT_STATUS.md

**Right:** Update both:
- CHANGELOG.md for the historical record
- PROJECT_STATUS.md for current status

**Why:** Different documents serve different purposes.

---

### Mistake 5: No Dates

**Wrong:**
```markdown
**Last Updated:** Recently
```

**Right:**
```markdown
**Last Updated:** 2026-02-27
```

**Why:** "Recently" could be yesterday or last month. Dates don't lie.

---

## 🎓 Documentation Quality Checklist

Before considering documentation "done," check:

```
□ Is it honest? (No sugar-coating problems)
□ Is it current? (Updated within the week)
□ Is it clear? (A non-technical person can understand)
□ Is it concise? (Bullet points, not essays)
□ Is it dated? (Always show "Last Updated")
□ Is it accessible? (In the project root, easy to find)
```

---

## 📊 Time Investment vs. Benefit

| Activity | Time/Week | Benefit |
|----------|-----------|---------|
| Weekly status updates | 15 min | No status meetings needed |
| Task logging | 10 min | Know exactly what was done |
| Monthly README review | 15 min | Always demo-ready |
| **Total** | **~40 min/month** | **Saves 4+ hours in meetings** |

---

## 🏆 The 80/20 Rule of Documentation

**80% of the value comes from 20% of the effort:**

1. **Update PROJECT_STATUS.md weekly** (10 min)
2. **Log tasks in CHANGELOG.md** (2 min each)
3. **Keep README.md accurate** (15 min/month)

Everything else is nice-to-have.

---

## 📞 When in Doubt

**Ask yourself:**
> "If I get hit by a bus tomorrow, will the next person know what's going on?"

If the answer is no, document it.

---

## 🤖 AI Prompts for Documentation Updates

**For Non-Technical Users** – Copy-paste these prompts to Qwen (or any AI assistant) to update documentation quickly.

---

### Prompt 1: Update CHANGELOG.md (After Completing a Task)

**When to Use:**
- ✅ Just finished a feature
- ✅ Fixed a bug
- ✅ Completed a testing session
- **Time:** 2 minutes
- **Frequency:** As needed (typically 3-5x per week)

---

**Copy This Prompt:**
```
I just completed a task. Help me update CHANGELOG.md.

Task Details:
- What I did: [Describe in plain English, e.g., "Built the login page"]
- Type: [Added / Fixed / Changed / Removed]
- Impact: [One line on why it matters, e.g., "Users can now authenticate"]

Please:
1. Read the current CHANGELOG.md
2. Add an entry under [Unreleased] section
3. Use the format: "- [Type]: [Description] – [Impact]"
4. Keep it under 2 lines
5. Show me the updated section for review
```

---

**Example Usage:**
```
I just completed a task. Help me update CHANGELOG.md.

Task Details:
- What I did: Built technical analysis module with RSI, MACD, and EMA indicators
- Type: Added
- Impact: System can now generate trading signals automatically

Please:
1. Read the current CHANGELOG.md
2. Add an entry under [Unreleased] section
3. Use the format: "- [Type]: [Description] – [Impact]"
4. Keep it under 2 lines
5. Show me the updated section for review
```

**Expected Output:**
```markdown
## [Unreleased]
### Added
- Technical analysis module with RSI, MACD, EMA – Automatic signal generation
```

---

### Prompt 2: Update PROJECT_STATUS.md (Weekly)

**When to Use:**
- 📅 Every Friday (recommended)
- 📅 Before status meetings
- 📅 End of sprint
- **Time:** 10 minutes
- **Frequency:** Weekly

---

**Copy This Prompt:**
```
Help me update PROJECT_STATUS.md for this week's status.

Week Of: [Date range, e.g., "Feb 24-28, 2026"]

Completed This Week:
1. [Task 1]
2. [Task 2]
3. [Task 3]

Still In Progress:
1. [Task] – [X]% complete
2. [Task] – waiting on [person/thing]

Next Week's Goals:
1. [Goal 1]
2. [Goal 2]

Blockers (if any):
- [Blocker] – [Who is fixing] – [Due date]

Please:
1. Read the current PROJECT_STATUS.md
2. Update "Last Updated" to today's date
3. Move completed items to "Completed This Week" section
4. Update "In Progress" with percentages
5. Add next week's goals
6. List any blockers
7. Recalculate overall progress percentage
8. Show me a summary of changes before applying
```

---

**Example Usage:**
```
Help me update PROJECT_STATUS.md for this week's status.

Week Of: Feb 24-28, 2026

Completed This Week:
1. Technical analysis module (RSI, MACD, EMA)
2. Signal engine for position health
3. 56 unit tests (all passing)

Still In Progress:
1. Telegram integration – 0% (not started)
2. Dashboard UI – 0% (not started)
3. Background scheduler – 0% (not started)

Next Week's Goals:
1. Start Telegram bot integration
2. Design dashboard wireframe
3. Research APScheduler library

Blockers (if any):
- None

Please:
1. Read the current PROJECT_STATUS.md
2. Update "Last Updated" to today's date
3. Move completed items to "Completed This Week" section
4. Update "In Progress" with percentages
5. Add next week's goals
6. List any blockers
7. Recalculate overall progress percentage
8. Show me a summary of changes before applying
```

**Expected Output:**
```
Summary of Changes:
- Updated "Last Updated" to 2026-02-28
- Added 3 items to "Completed This Week"
- Overall progress: 75% → 80%
- Added 3 goals for next week
- No blockers reported

Ready to apply? (Yes/No)
```

---

### Prompt 3: Update README.md (Monthly/Milestone)

**When to Use:**
- 📅 End of month review
- 📅 Reached major milestone (25%, 50%, 75%, 100%)
- 📅 Before investor/demo meetings
- 📅 When features change significantly
- **Time:** 15 minutes
- **Frequency:** Monthly or per milestone

---

**Copy This Prompt:**
```
Help me review and update README.md for accuracy.

Current Status:
- Overall Progress: [X]% (was [Y]%)
- New Features Since Last Update: [List]
- Features Now Complete: [List]
- Upcoming Features: [List]
- Test Count: [X] tests ([Y] passing)
- Any Breaking Changes: [Yes/No – describe]

Please:
1. Read the current README.md
2. Check if progress percentage is accurate
3. Update feature status table (✅ vs 🚧)
4. Update test count if changed
5. Update "Current Progress" section
6. Check for outdated information
7. Show me a diff of proposed changes
```

---

**Example Usage:**
```
Help me review and update README.md for accuracy.

Current Status:
- Overall Progress: 85% (was 75%)
- New Features Since Last Update: Background scheduler with APScheduler
- Features Now Complete: Scheduler, Technical Analysis, Signal Engine, API
- Upcoming Features: Telegram bot, Streamlit dashboard
- Test Count: 56 tests (56 passing)
- Any Breaking Changes: No

Please:
1. Read the current README.md
2. Check if progress percentage is accurate
3. Update feature status table (✅ vs 🚧)
4. Update test count if changed
5. Update "Current Progress" section
6. Check for outdated information
7. Show me a diff of proposed changes
```

**Expected Output:**
```
Proposed Changes:
- Progress badge: 75% → 85%
- Feature table: Scheduler moved from 🚧 to ✅
- Test count: Still 56 passing (no change)
- Updated "Next Steps" section

Ready to apply? (Yes/No)
```

---

### Prompt 4: Create API Documentation (When API Changes)

**When to Use:**
- 📅 New endpoint added
- 📅 Request/response format changed
- 📅 Authentication changed
- 📅 Before releasing to external users
- **Time:** 10 minutes
- **Frequency:** As needed

---

**Copy This Prompt:**
```
Help me update API_DOCS.md for recent API changes.

Changes Made:
- New Endpoints: [List with method and path]
- Modified Endpoints: [List with changes]
- Deprecated Endpoints: [List]
- Authentication Changes: [Describe]

For Each New Endpoint, Provide:
- Method (GET/POST/PUT/DELETE)
- Full path
- Request body example (JSON)
- Response example (JSON)
- Error codes

Please:
1. Read the current API_DOCS.md (or create if missing)
2. Add new endpoints in alphabetical order by path
3. Include curl examples for each
4. Update table of contents if present
5. Show me the new sections for review
```

---

**Example Usage:**
```
Help me update API_DOCS.md for recent API changes.

Changes Made:
- New Endpoints: POST /api/v1/positions/open, GET /api/v1/positions/open
- Modified Endpoints: None
- Deprecated Endpoints: None
- Authentication Changes: None

For Each New Endpoint, Provide:
- Method (GET/POST/PUT/DELETE)
- Full path
- Request body example (JSON)
- Response example (JSON)
- Error codes

Please:
1. Read the current API_DOCS.md (or create if missing)
2. Add new endpoints in alphabetical order by path
3. Include curl examples for each
4. Update table of contents if present
5. Show me the new sections for review
```

---

### Prompt 5: Generate Weekly Summary Report (For Stakeholders)

**When to Use:**
- 📅 Friday afternoon
- 📅 Before Monday standup
- 📅 Sending status email to team
- **Time:** 5 minutes
- **Frequency:** Weekly

---

**Copy This Prompt:**
```
Generate a weekly status summary from PROJECT_STATUS.md and CHANGELOG.md.

Audience: [Non-technical stakeholders / Investors / Management]
Format: [Email / Slack message / Bullet points]
Tone: [Professional / Casual / Executive]

Please:
1. Read PROJECT_STATUS.md and CHANGELOG.md
2. Extract key accomplishments this week
3. Note any blockers or risks
4. Summarize next week's focus
5. Keep it under 150 words
6. Include progress percentage
7. Format for [email/Slack]
```

---

**Example Usage:**
```
Generate a weekly status summary from PROJECT_STATUS.md and CHANGELOG.md.

Audience: Non-technical stakeholders
Format: Email
Tone: Professional

Please:
1. Read PROJECT_STATUS.md and CHANGELOG.md
2. Extract key accomplishments this week
3. Note any blockers or risks
4. Summarize next week's focus
5. Keep it under 150 words
6. Include progress percentage
7. Format for email
```

**Expected Output:**
```
Subject: TA-DSS Weekly Status – Feb 28, 2026

Hi Team,

Progress: 80% complete (+5% this week)

✅ Completed:
- Technical analysis module (RSI, MACD, EMA)
- Signal engine for position health evaluation
- 56 unit tests (100% passing)

🚧 In Progress:
- Telegram integration (starting next week)
- Dashboard UI design

⚠️ Blockers: None

Next Week: Starting Telegram bot integration and dashboard wireframes.

Full details: PROJECT_STATUS.md

Best,
[Your Name]
```

---

### Prompt 6: Pre-Meeting Documentation Check

**When to Use:**
- 📅 1 hour before demo/investor meeting
- 📅 Before sprint review
- 📅 Before stakeholder presentation
- **Time:** 5 minutes
- **Frequency:** Per meeting

---

**Copy This Prompt:**
```
I have a [meeting type] in 1 hour. Help me prepare the documentation.

Meeting Type: [Demo / Investor Update / Sprint Review / Status Meeting]
Audience: [Investors / Technical Team / Management / Clients]
Key Topics: [List 2-3 things you'll discuss]

Please:
1. Review README.md for accuracy
2. Review PROJECT_STATUS.md for current status
3. Review CHANGELOG.md for recent updates
4. Flag any outdated information
5. Prepare 3 key talking points
6. Note any embarrassing issues to address proactively
7. Create a 5-bullet summary I can reference
```

---

**Example Usage:**
```
I have a demo meeting in 1 hour. Help me prepare the documentation.

Meeting Type: Investor Demo
Audience: Investors (non-technical)
Key Topics: Technical analysis capabilities, API readiness, Timeline

Please:
1. Review README.md for accuracy
2. Review PROJECT_STATUS.md for current status
3. Review CHANGELOG.md for recent updates
4. Flag any outdated information
5. Prepare 3 key talking points
6. Note any embarrassing issues to address proactively
7. Create a 5-bullet summary I can reference
```

**Expected Output:**
```
✅ Documentation Status:
- README.md: Accurate (85% progress shown)
- PROJECT_STATUS.md: Updated 2 days ago
- CHANGELOG.md: Current

⚠️ Items to Address:
- Telegram integration shows 0% – be ready to explain timeline
- Dashboard not started – have design mockups ready

🎯 3 Key Talking Points:
1. Core backend 85% complete, all tests passing
2. Technical analysis fully functional (RSI, MACD, EMA)
3. On track for [date] launch

📋 5-Bullet Summary:
• 85% complete, 56 tests passing
• API ready for integration
• Technical signals working
• Telegram + Dashboard next
• No blockers
```

---

## 📋 AI Prompt Quick Reference

| Prompt | When | Time | Frequency |
|--------|------|------|-----------|
| **1. CHANGELOG Update** | After completing task | 2 min | 3-5x/week |
| **2. PROJECT_STATUS Update** | Friday EOD | 10 min | Weekly |
| **3. README Review** | Milestone reached | 15 min | Monthly |
| **4. API Docs** | API changed | 10 min | As needed |
| **5. Weekly Summary** | Status email needed | 5 min | Weekly |
| **6. Pre-Meeting Check** | 1 hour before meeting | 5 min | Per meeting |

**Total with AI:** ~20 minutes/week (vs. 40 min manual)

---

## 🎯 Summary: Your Documentation Habits

### Manual vs. AI-Assisted

| Habit | Frequency | Manual Time | AI Time | Document |
|-------|-----------|-------------|---------|----------|
| Log completed tasks | After each task | 5 min | 2 min | CHANGELOG.md |
| Weekly status update | Every Friday | 20 min | 10 min | PROJECT_STATUS.md |
| Monthly README review | Monthly | 30 min | 15 min | README.md |
| Pre-meeting prep | Per meeting | 15 min | 5 min | All |
| Weekly summary email | Weekly | 15 min | 5 min | All |
| **Total/Month** | | **~4 hours** | **~1.5 hours** | |

**Time Saved with AI:** ~60% (2.5 hours/month)

---

## 📊 Quick Start Calendar

### Week 1 (Build the Habit)
```
□ Day 1 (Monday): Set up all 4 documents
□ Day 3 (Wednesday): Try Prompt 1 (CHANGELOG) after a task
□ Day 5 (Friday): Use Prompt 2 (PROJECT_STATUS) for weekly update
□ Weekend: Review what worked, adjust prompts
```

### Week 2+ (Maintain)
```
□ Monday: 5-min goal setting (PROJECT_STATUS)
□ Wednesday: Quick progress check (2 min)
□ Friday: Weekly update with Prompt 2 (10 min)
□ As needed: CHANGELOG updates with Prompt 1 (2 min each)
```

### Monthly (Keep Accurate)
```
□ Last Friday: Monthly README review with Prompt 3 (15 min)
□ Update milestone progress (25% → 50% → 75% → 100%)
□ Archive old CHANGELOG entries
□ Plan next month's goals
```

---

## 🏆 Success Metrics

You're doing documentation **right** when:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Freshness** | Updated within 7 days | Check PROJECT_STATUS.md date |
| **Completeness** | All 4 docs exist | Count documents in root |
| **Accuracy** | Progress ±5% | Compare to actual completion |
| **Time Spent** | <30 min/week | Track your time |
| **Meeting Prep** | <10 min | Time before demos |

---

## 🚨 Red Flags (Course Correct)

| Warning Sign | Fix |
|--------------|-----|
| PROJECT_STATUS.md >2 weeks old | Set Friday calendar reminder |
| CHANGELOG.md empty for a week | Use Prompt 1 after each task |
| README.md shows 50% but you're at 80% | Use Prompt 3 immediately |
| Spending >1 hour/week | Use more AI prompts, less manual writing |
| Stakeholders asking "what's the status?" | Send Prompt 5 summary weekly |

---

## 📞 When in Doubt

**Ask yourself:**
> "If I get hit by a bus tomorrow, will the next person know what's going on?"

If the answer is no, document it.

**Ask Qwen:**
> "Help me update [DOCUMENT] based on [WHAT HAPPENED]"

Worst case: 2 minutes wasted. Best case: Hours saved.

---

**Remember:** Good documentation isn't about perfection. It's about consistency.

**With AI:** Good documentation is 20 minutes/week. Start today.

---

**Document Owner:** Project Team  
**Review Cycle:** Monthly  
**Next Review:** 2026-03-27  
**AI Prompts Version:** 1.0
