# TA-DSS: UX Improvement Backlog

> **Purpose:** Track UX improvements and polish items that don't block core functionality. Review and prioritize during polish sprints.

**Created:** 2026-02-28  
**Last Updated:** 2026-02-28

---

## 🎯 How to Use This Log

1. **Add items** as you discover them (don't stop development)
2. **Assign priority** (High/Medium/Low)
3. **Estimate effort** (S/M/L)
4. **Review weekly** during polish sprints
5. **Batch similar items** together for efficiency

---

## 📊 Priority Levels

| Priority | Description | Fix Timeline |
|----------|-------------|--------------|
| **High** | Blocks usability, confusing for users | Next sprint |
| **Medium** | Annoying but workable | Within 2 weeks |
| **Low** | Nice-to-have polish | When time permits |

---

## 🅿️ Backlog Items

### Item #1: Position Row Click - Visual Feedback

**Date Logged:** 2026-02-28  
**Priority:** 🟠 MEDIUM  
**Effort:** Small (30 min)  
**Category:** Navigation/UX

---

#### Problem

Current position table row click interaction lacks visual feedback:
- No hover effect (doesn't look clickable)
- No highlight when selected (user unsure if click registered)
- No "View Details" button (relying on row click only)
- No breadcrumb in detail view (user might feel lost)

---

#### Current Flow

```
Dashboard → Click row → Detail view → Click "Back" → Dashboard
```

**Issues:**
- ❌ Row doesn't change appearance on hover
- ❌ No visual feedback when row is selected
- ❌ User might not realize row is clickable
- ❌ No clear indication of navigation state

---

#### Proposed Solutions

**Option A: Quick Fix (15 min)**
- Add CSS hover effect on table rows
- Highlight selected row with different background
- Add cursor pointer on hover

**Option B: Add View Button (30 min)** ← **Recommended**
- Add "👁️ View" button in each row
- Keep row click as secondary
- Add breadcrumb navigation in detail view

**Option C: Two-Panel Layout (1 hour)**
- Left panel: Position list (always visible)
- Right panel: Detail view (updates on click)
- Gmail-style interaction

---

#### Impact

**Users affected:** All dashboard users  
**Frequency:** Every time user views position details  
**Severity:** Annoying but not blocking

---

#### Acceptance Criteria

- [ ] Row clearly looks clickable (hover effect)
- [ ] Selected row is highlighted
- [ ] User knows they're in detail view (breadcrumb or header)
- [ ] Easy to return to list view

---

#### Related Files

- `src/ui.py` - `render_positions_table()` function
- `src/ui.py` - `render_position_detail()` function
- `.streamlit/config.toml` - Theme colors

---

### Item #2: [Add Future Items Here]

**Date Logged:** [Date]  
**Priority:** [High/Medium/Low]  
**Effort:** [S/M/L]  
**Category:** [Navigation/Visual/Performance/etc.]

---

#### Problem

[Describe the issue]

---

#### Proposed Solution

[Describe the fix]

---

#### Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2

---

## 📅 Polish Sprint Schedule

| Sprint | Date | Focus Area | Items to Address |
|--------|------|------------|------------------|
| Sprint 1 | TBD | Navigation UX | Item #1 (Position row click) |
| Sprint 2 | TBD | Visual Polish | TBD |
| Sprint 3 | TBD | Performance | TBD |

---

## ✅ Completed Improvements

| Item | Completed | Sprint | Notes |
|------|-----------|--------|-------|
| [Item name] | [Date] | [Sprint #] | [Notes] |

---

## 🎯 Decision Log

### 2026-02-28: Position Row Click

**Decision:** Move to backlog, continue with next priority task

**Rationale:**
- Core functionality works (can view details)
- Not blocking other development
- Better to batch with other UX improvements
- Test full system first, then polish

**Approved by:** [Your name]

---

## 📝 Notes

- Review this log every Friday
- Batch similar items together (e.g., all navigation improvements)
- Don't let perfection block progress
- Polish sprints: 1-2 hours per week

---

**Last Reviewed:** 2026-02-28  
**Next Review:** [Next Friday's date]
