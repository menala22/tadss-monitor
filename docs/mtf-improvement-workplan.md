# MTF Report Improvement Workplan

**Quick Reference Guide** | Created: 2026-03-08

---

## Priority Matrix

```
        HIGH IMPACT
            │
   ┌────────┴────────┐
   │  WEEK 1         │  WEEK 2
   │  Critical       │  High Priority
   │  • Data Quality │  • Trade Management
   │  • Market Ctx   │  • Pattern Stats
   │  • Exec Summary │  • Visual Hierarchy
   │                 │  • Scenarios
   └────────┬────────┘
            │
        LOW IMPACT
            │
   ┌────────┴────────┐
   │  WEEK 3-4       │  BACKLOG
   │  Medium         │  Nice to Have
   │  • Comparison   │  • Retrospective
   │  • Confluence   │  • Advanced charts
   │  • Volume       │
   └─────────────────┘
```

---

## Week 1: Critical (P0)

### Day 1: Data Quality Dashboard
- **File:** `src/services/data_quality_checker.py` (new)
- **File:** `src/models/mtf_models.py` (add `DataQualityReport`)
- **Task:** Add validation before report generation
- **Time:** 4 hours

### Day 2: Market Context Analyzer
- **File:** `src/services/market_context_analyzer.py` (new)
- **Task:** Add regime detection, volatility state, event calendar
- **Time:** 6 hours

### Day 3: Enhanced Executive Summary
- **File:** `scripts/generate_mtf_report.py` (template update)
- **Task:** Add TL;DR section, conviction score, key drivers
- **Time:** 4 hours

### Day 4: Data Validation Warnings
- **File:** `src/services/mtf_alignment_scorer.py`
- **Task:** Add prominent warnings for insufficient/stale data
- **Time:** 3 hours

### Day 5: Testing & Bug Fixes
- **Task:** Test all new features, fix issues
- **Time:** 4 hours

**Week 1 Total:** ~21 hours

---

## Week 2: High Priority (P1)

### Day 1: Trade Management Section
- **File:** `src/services/position_sizing.py` (new)
- **File:** Report template update
- **Task:** Position sizing, profit-taking plan, stop management
- **Time:** 5 hours

### Day 2: Pattern Performance Tracker
- **File:** `src/services/pattern_performance.py` (new)
- **File:** Database schema for pattern tracking
- **Task:** Historical pattern statistics
- **Time:** 6 hours

### Day 3: Visual Hierarchy Overhaul
- **File:** `scripts/generate_mtf_report.py` (major template update)
- **Task:** Emoji indicators, callout boxes, clean tables
- **Time:** 5 hours

### Day 4: Scenario Analysis
- **File:** Report template update
- **Task:** Base/bull/bear cases with probabilities
- **Time:** 4 hours

### Day 5: Testing & Documentation
- **Task:** Test features, update user guide
- **Time:** 4 hours

**Week 2 Total:** ~24 hours

---

## Week 3-4: Medium Priority (P2)

| Task | File | Time |
|------|------|------|
| Multi-asset comparison | `src/services/opportunity_ranker.py` | 6h |
| Confluence scoring | `src/services/confluence_scorer.py` | 5h |
| Volume profile | `src/services/support_resistance_detector.py` | 4h |
| Retrospective analysis | `src/services/trade_tracker.py` | 6h |
| Documentation updates | `docs/features/mtf-user-guide.md` | 3h |
| Testing + polish | All files | 4h |

**Week 3-4 Total:** ~28 hours

---

## Total Effort Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Week 1 (P0) | 21 hours | Data quality + market context |
| Week 2 (P1) | 24 hours | Trade management + visuals |
| Week 3-4 (P2) | 28 hours | Advanced features |
| **Total** | **73 hours** | **Complete overhaul** |

---

## Files to Create (New)

1. `src/services/data_quality_checker.py`
2. `src/services/market_context_analyzer.py`
3. `src/services/position_sizing.py`
4. `src/services/pattern_performance.py`
5. `src/services/opportunity_ranker.py`
6. `src/services/confluence_scorer.py`
7. `src/services/trade_tracker.py`

---

## Files to Modify

1. `src/models/mtf_models.py` (add new dataclasses)
2. `src/services/mtf_alignment_scorer.py` (add validation)
3. `scripts/generate_mtf_report.py` (template overhaul)
4. `src/services/support_resistance_detector.py` (volume profile)
5. `docs/features/mtf-user-guide.md` (documentation)

---

## Quick Start: First Steps

### 1. Review the Full Plan
```bash
open docs/mtf-report-improvement-plan.md
```

### 2. Start with Data Quality Checker
```bash
# Create new service file
touch src/services/data_quality_checker.py
```

### 3. Add DataQualityReport Model
```python
# In src/models/mtf_models.py
@dataclass
class DataQualityReport:
    status: str  # "PASS", "WARNING", "FAIL"
    candle_count: int
    required_count: int
    freshness_hours: float
    issues: List[str]
```

### 4. Update Report Generator
```python
# In scripts/generate_mtf_report.py
from src.services.data_quality_checker import DataQualityChecker

checker = DataQualityChecker()
quality_report = checker.check_all_data(data)
report = generate_report(..., quality_report=quality_report)
```

---

## Success Checklist

### Week 1 Completion Criteria
- [ ] All reports show data quality dashboard
- [ ] Market context section present
- [ ] Warnings for insufficient data
- [ ] Enhanced executive summary with TL;DR

### Week 2 Completion Criteria
- [ ] Trade management plan in all reports
- [ ] Pattern performance statistics
- [ ] Visual hierarchy improved (emojis, callouts)
- [ ] Scenario analysis with probabilities

### Week 3-4 Completion Criteria
- [ ] Multi-asset comparison table
- [ ] Confluence scoring visible
- [ ] Volume profile analysis
- [ ] Retrospective tracking working

---

## Contact & Support

For questions about this workplan:
- Review full plan: `docs/mtf-report-improvement-plan.md`
- Check MTF documentation: `docs/features/MTF-FINAL-DOCUMENTATION.md`
- User guide: `docs/features/mtf-user-guide.md`

---

**Last Updated:** 2026-03-08
**Version:** 1.0
