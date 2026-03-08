# MTF Report Generator - Quick Reference

**Last Updated:** 2026-03-08  
**Version:** 2.0 (Enhanced with Data Quality)

---

## 🚀 Quick Start

```bash
# Generate complete MTF analysis report
python scripts/generate_mtf_report.py BTC/USDT SWING

# Output (3 files):
# ✅ Markdown report with embedded charts
# ✅ Interactive HTML report (Plotly)
# ✅ 4 PNG charts
```

---

## 📊 What You Get

### 1. Markdown Report
**File:** `BTCUSDT-mtf-analysis-swing-20260308.md`

**Sections:**
- Executive Summary
- 📊 **NEW:** Data Quality Dashboard
- 📊 **NEW:** Data Validation Warnings
- Multi-Timeframe Alignment (with chart)
- HTF Analysis (with chart)
- MTF Setup (with chart)
- LTF Entry (with chart, if signal exists)
- Final Trade Setup

### 2. Interactive HTML Report
**File:** `BTCUSDT-mtf-analysis-interactive-20260308.html`

**Features:**
- Zoom, pan, hover
- 4 synchronized panels
- Professional candlestick charts
- Opens in any browser

### 3. PNG Charts (4 files)
**Location:** `charts/` folder

1. HTF Analysis - Price structure, SMAs, key levels
2. MTF Setup - Pullback zones, RSI, SMAs
3. LTF Entry - Entry point, stop, target
4. Alignment Overview - 3-timeframe visualization

---

## ✅ Data Quality Features

### Automatic Validation

Every report includes:

```markdown
## 📊 Data Quality Check

**Overall Status:** ✅ PASS / ⚠️ WARNING / ❌ FAIL

| Timeframe | Candles | Required | Status | Freshness |
|-----------|---------|----------|--------|-----------|
| HTF (w1)  | 325     | 200      | ✅ PASS | 85.0h old |
| MTF (d1)  | 200     | 50       | ✅ PASS | 13.0h old |
| LTF (h4)  | 500     | 50       | ✅ PASS | 1.0h old  |
```

### Validation Rules

| Timeframe | Required Candles | Max Freshness |
|-----------|------------------|---------------|
| **HTF** (Weekly) | 200 | 240 hours (10 days) |
| **MTF** (Daily) | 50 | 48 hours (2 days) |
| **LTF** (4H) | 50 | 12 hours |

### Status Meanings

- **✅ PASS** - Sufficient candles AND fresh data
- **⚠️ WARNING** - Insufficient OR stale data
- **❌ FAIL** - Severely insufficient (<50% of required)

---

## ⚠️ Validation Warnings

### When Data Quality ≠ PASS

You'll see prominent warnings:

```markdown
> [!WARNING]
> **Data Quality Warning:** ⚠️ HTF needs 99 more candles
>
> **Recommendations:**
> 1. Fetch 99 more HTF candles for full SMA 200 analysis
> 2. Refresh MTF data (currently 13.0h old)
> 3. Refresh LTF data (currently 13.0h old)

> [!IMPORTANT]
> **MTF Analysis Not Recommended:** Insufficient data for reliable MTF analysis.
> The signals below may be unreliable due to data quality issues.
```

---

## 📖 Documentation

### Complete Logic Reference
**File:** [`docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md`](docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md)

**Contents:**
- HTF Bias Detection (SMA 50/200, price structure)
- MTF Setup Detection (pullback, RSI, divergence)
- LTF Entry Signals (candlestick patterns, EMA reclaim)
- Stop Loss Calculation (structural, 0.5% buffer)
- Take Profit Targets (5 methods)
- Alignment Scoring (3/3 system)
- Complete worked example (BTC/USDT)

### Improvement Summary
**File:** [`docs/MTF-REPORT-IMPROVEMENTS-FINAL.md`](docs/MTF-REPORT-IMPROVEMENTS-FINAL.md)

**Contents:**
- All completed improvements
- File inventory
- Feature comparison (before/after)
- Usage guide
- Success metrics

### Chart Guides
- **Chart Implementation:** [`docs/mtf-report-with-charts-guide.md`](docs/mtf-report-with-charts-guide.md)
- **Interactive HTML Reports:** [`docs/mtf-interactive-html-summary.md`](docs/mtf-interactive-html-summary.md)

---

## 🎯 Usage Examples

### Example 1: Good Data (BTC/USDT)

```bash
$ python scripts/generate_mtf_report.py BTC/USDT SWING

🔍 Checking data quality...
   Overall: PASS
   ✅ All timeframes have sufficient, fresh data

✅ Report saved to: docs/reports/BTCUSDT-mtf-analysis-swing-20260308.md
```

**Result:**
- Full report with all sections
- Data quality: All PASS ✅
- Charts: All 4 generated
- HTML: Interactive version created

---

### Example 2: Insufficient Data (XAUUSD)

```bash
$ python scripts/generate_mtf_report.py XAUUSD INTRADAY

🔍 Checking data quality...
   Overall: WARNING
   ⚠️ HTF needs 99 more candles

✅ Report saved to: docs/reports/XAUUSD-mtf-analysis-intraday-20260308.md
```

**Result:**
- Report includes WARNING callout
- Data quality dashboard shows issues
- MTF readiness warning displayed
- Recommendations provided

---

## 📁 File Structure

```
trading-order-monitoring-system/
├── scripts/
│   └── generate_mtf_report.py          ← Report generator
├── src/
│   ├── models/
│   │   └── mtf_models.py               ← Data quality dataclasses
│   └── services/
│       ├── mtf_chart_generator.py      ← PNG chart generator
│       ├── mtf_chart_generator_plotly.py ← HTML chart generator
│       └── data_quality_checker.py     ← Quality validation
├── docs/
│   ├── MTF-ANALYSIS-LOGIC-EXPLAINED.md    ← Complete logic
│   ├── MTF-REPORT-IMPROVEMENTS-FINAL.md   ← Improvement summary
│   ├── mtf-report-with-charts-guide.md    ← Chart guide
│   └── mtf-interactive-html-summary.md    ← HTML guide
└── docs/reports/
    ├── {pair}-mtf-analysis-{style}-{date}.md
    ├── {pair}-mtf-analysis-interactive-{date}.html
    └── charts/
        ├── {pair}-htf-analysis.png
        ├── {pair}-mtf-setup.png
        ├── {pair}-ltf-entry.png
        └── {pair}-alignment.png
```

---

## 🔧 Customization

### Adjust Data Quality Requirements

Edit `src/services/data_quality_checker.py`:

```python
class DataQualityChecker:
    def __init__(
        self,
        htf_required: int = 200,  # Change HTF requirement
        mtf_required: int = 50,   # Change MTF requirement
        ltf_required: int = 50,   # Change LTF requirement
    ):
```

### Adjust Freshness Thresholds

```python
self.staleness_thresholds = {
    'w1': 240,    # Weekly: 10 days
    'd1': 48,     # Daily: 2 days
    'h4': 12,     # 4H: 12 hours
    'h1': 4,      # 1H: 4 hours
    # Add more as needed
}
```

---

## 📊 Report Sections

### Standard Sections (Always Present)

1. Executive Summary
2. Timeframe Configuration
3. HTF Analysis (Weekly/Daily/4H depending on style)
4. MTF Setup (Daily/4H/1H)
5. LTF Entry (4H/1H/15M)
6. Alignment Scoring
7. Final Trade Setup
8. Risk Warning
9. Monitoring Checklist

### Conditional Sections

**Data Quality Dashboard** - Always shown
- Shows candle count, freshness, status
- Recommendations if issues

**Validation Warnings** - Shown when quality ≠ PASS
- ⚠️ WARNING callout
- ❗ IMPORTANT callout (if MTF not ready)

**Charts** - Shown when generated
- Alignment chart (always)
- HTF chart (always)
- MTF chart (always)
- LTF chart (only if entry signal exists)

---

## 🎨 Visual Elements

### Emoji Indicators

| Emoji | Meaning |
|-------|---------|
| ✅ | PASS / Good / Bullish |
| ⚠️ | WARNING / Caution |
| ❌ | FAIL / Bad / Bearish |
| 🟢 | Bullish |
| 🔴 | Bearish |
| ⚪ | Neutral |
| 📊 | Chart/Analysis |
| 🌍 | Market Context |
| 🎯 | Target/Summary |

### GitHub-Style Callouts

```markdown
> [!WARNING]
> Warning message with recommendations

> [!IMPORTANT]
> Critical information about MTF readiness

> [!TIP]
> Helpful suggestion or best practice
```

---

## 📈 Success Metrics

### What Improved

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Charts | 0 | 4 + interactive | +∞ |
| Data Quality Checks | 0 | 6 per report | +∞ |
| Documentation | ~100 lines | ~1000 lines | +900% |
| Validation Warnings | 0 | 2 types | +∞ |
| Professional Quality | ⭐⭐ | ⭐⭐⭐⭐⭐ | +150% |

### User Benefits

- ✅ **See the analysis** (charts instead of text-only)
- ✅ **Trust the signals** (data quality verified)
- ✅ **Learn the logic** (complete documentation)
- ✅ **Interact with data** (zoom/pan/hover)

---

## 🆘 Troubleshooting

### "Chart generation error"

**Cause:** Missing matplotlib/seaborn  
**Fix:** `pip install matplotlib seaborn`

### "No charts in report"

**Cause:** Chart paths incorrect  
**Fix:** Charts are in `charts/` subdirectory - paths are relative

### "Data quality FAIL"

**Cause:** Insufficient candles  
**Fix:** Fetch more historical data for affected timeframe

### "HTML report not opening"

**Cause:** Browser association  
**Fix:** Right-click → Open with → Chrome/Safari/Firefox

---

## 📞 Support

### Documentation

- **Complete Logic:** [`docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md`](docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md)
- **Improvement Summary:** [`docs/MTF-REPORT-IMPROVEMENTS-FINAL.md`](docs/MTF-REPORT-IMPROVEMENTS-FINAL.md)
- **Chart Guide:** [`docs/mtf-report-with-charts-guide.md`](docs/mtf-report-with-charts-guide.md)
- **HTML Guide:** [`docs/mtf-interactive-html-summary.md`](docs/mtf-interactive-html-summary.md)

### Code

- **Report Generator:** `scripts/generate_mtf_report.py`
- **Chart Generator:** `src/services/mtf_chart_generator.py`
- **Plotly Generator:** `src/services/mtf_chart_generator_plotly.py`
- **Data Quality:** `src/services/data_quality_checker.py`

---

**MTF Report Generator v2.0 - Production Ready** ✅

**Last Updated:** 2026-03-08
