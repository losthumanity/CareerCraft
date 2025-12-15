# 🚀 Quick Start: Smart Watcher v2

## Installation (5 minutes)

```powershell
# 1. Navigate to project
cd D:\PYTHON\FUN\Jobify

# 2. Activate virtual environment
.\venv\Scripts\activate

# 3. Install new dependencies
pip install sentence-transformers numpy torch

# 4. Install Playwright browsers (one-time)
playwright install chromium

# 5. Create logs directory if missing
mkdir logs -ErrorAction SilentlyContinue
```

## First Run (Test Mode)

```powershell
# Run with verbose output to see what it finds
cd watcher
python smart_watcher_v2.py --verbose

# Expected output:
# 🎯 Smart Job Watcher v2 - Semantic Matching Edition
# Profile: 2026 AI/ML Graduate | Python, PyTorch, CV
# Threshold: 0.70 | Boards: False
#
# 📍 Phase 1: Scanning 9 company career pages...
#   → LY Corporation (LINE)...
#   ✅ Found match: AI Engineer - New Graduate 2026 (score: 0.82)
#   → Rakuten Group...
#   ...
#
# ✅ Scan complete!
#    Total matches found: 12
#    New jobs added: 12
```

## View Results

```powershell
# Open dashboard
cd ../dashboard
streamlit run dashboard.py

# Dashboard opens at: http://localhost:8501
# You'll see your matched jobs in the Pipeline view
```

## Understanding Match Scores

| Score | Meaning | Action |
|-------|---------|--------|
| **0.85-1.0** | Excellent match | Apply ASAP |
| **0.75-0.84** | Good match | Review and apply |
| **0.70-0.74** | Decent match | Read carefully before applying |
| **< 0.70** | Not matched | Filtered out (not shown) |

## Customization

### Adjust Matching Threshold

```powershell
# More strict (only excellent matches)
python smart_watcher_v2.py --threshold 0.80

# More relaxed (catch more possibilities)
python smart_watcher_v2.py --threshold 0.65
```

### Include Job Board Aggregators

```powershell
# Scan companies + Japan Dev, TokyoDev, etc.
python smart_watcher_v2.py --include-boards

# Warning: Slower, more duplicates
```

### Edit Your Profile

Open `smart_watcher_v2.py` and edit line 27:

```python
YOUR_PROFILE = """
2026 Graduate seeking AI Engineer / ML Engineer position in Japan.
Experience: 6-month AI internship at Johnson Controls (Fortune 500).
Skills: Python, PyTorch, TensorFlow, FastAPI, Computer Vision, Industrial AI.
Looking for: New graduate program, English-speaking role, visa sponsorship.

# ADD YOUR SPECIFICS:
Projects: RAG system with LangChain, CNN for deepfake detection, sentiment analysis.
Interests: Reinforcement learning, industrial automation, anime culture.
Preferences: Tokyo-based, April 2026 start, relocation support.
"""
```

### Add/Remove Companies

Edit the `PRIORITY_COMPANIES` dictionary (line 41):

```python
PRIORITY_COMPANIES = {
    'Your Target Company': 'https://their-career-page.com',
    # Add more...
}
```

## Automate It (Run Daily)

### Option 1: Windows Task Scheduler

```powershell
# Create scheduled task (runs daily at 9 AM)
$action = New-ScheduledTaskAction -Execute "D:\PYTHON\FUN\Jobify\venv\Scripts\python.exe" -Argument "D:\PYTHON\FUN\Jobify\watcher\smart_watcher_v2.py" -WorkingDirectory "D:\PYTHON\FUN\Jobify\watcher"

$trigger = New-ScheduledTaskTrigger -Daily -At 9am

Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "JobWatcherSmartV2" -Description "Daily job scan for 2026 AI/ML roles"
```

### Option 2: Manual Batch File

Create `run_smart_watcher.bat`:

```batch
@echo off
cd /d D:\PYTHON\FUN\Jobify
call venv\Scripts\activate
cd watcher
python smart_watcher_v2.py
pause
```

Double-click to run whenever you want.

## Troubleshooting

### Error: "No module named 'sentence_transformers'"

```powershell
pip install sentence-transformers
```

### Error: "Playwright browser not found"

```powershell
playwright install chromium
```

### Error: "Database is locked"

Dashboard and watcher can't run simultaneously. Close dashboard, then run watcher.

### No Jobs Found

Common reasons:
1. **Sites changed layout** - Normal, requires scraper update
2. **No new 2026 postings yet** - Check back in Jan-Feb 2025
3. **Threshold too high** - Try `--threshold 0.65`
4. **Sites down** - Check URLs manually

### False Positives (Wrong Jobs Matched)

1. Lower threshold: `--threshold 0.75`
2. Add to `BAD_SIGNALS` in code (line 69)
3. Update `YOUR_PROFILE` to be more specific

### Performance Issues

- **First run slow?** Model downloads 80MB (one-time)
- **Every run slow?** Disable job boards: don't use `--include-boards`
- **High CPU?** Normal - model runs on CPU

## Daily Workflow

### Morning Routine (5 minutes)

```powershell
# 1. Run watcher
cd D:\PYTHON\FUN\Jobify\watcher
python smart_watcher_v2.py

# 2. Check dashboard
cd ../dashboard
streamlit run dashboard.py

# 3. Review new jobs
# - Check "Pending" status
# - Read job descriptions
# - Mark good ones as "CV Generated"

# 4. Apply
# - Generate tailored resume
# - Submit application
# - Update status to "Applied"
```

### Weekly Review (30 minutes)

1. **Check success rate** in Analytics tab
2. **Update companies** if any aren't posting
3. **Refine profile** if getting wrong matches
4. **Network on LinkedIn** with target companies

## Success Metrics

Track these in the dashboard:

- **Response Rate**: Applied → Interview (target: >10%)
- **Time to Apply**: Job found → Applied (target: <48 hours)
- **Quality Score**: Average match score (target: >0.75)
- **Coverage**: Are all target companies monitored? (target: 100%)

## Next-Level Optimizations

Once you're comfortable:

1. **Add more companies** specific to your interests
2. **Build company-specific scrapers** for better accuracy
3. **Integrate with LinkedIn** for auto-applying
4. **Add email alerts** for high-match jobs (>0.85)
5. **Track application outcomes** to refine matching

## Remember

**The scraper is 20% of success. The other 80%:**

- ✅ Tailored resume for each application
- ✅ Strong GitHub portfolio
- ✅ LinkedIn networking
- ✅ Following up on applications
- ✅ Interview prep

Now go find those opportunities! 🎯🇯🇵
