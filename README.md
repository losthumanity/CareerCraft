# 🎯 Job Sniper - Microservices Architecture

Automated job monitoring system for Japan 2026 New Graduate positions.

## 📁 Architecture

```
Jobify/
│
├── watcher/              # Service 1: Job Monitoring
│   ├── watcher.py        # Core scraping engine
│   └── README.md
│
├── tailor/               # Service 2: Resume Tailor (AI Brain)
│   ├── resume_tailor.py  # Gemini-powered tailoring engine
│   ├── tailor_cli.py     # Interactive CLI interface
│   ├── integration.py    # Watcher integration
│   ├── tailor_config.yaml # Your resume data
│   └── README.md
│
├── dashboard/            # Service 3: Mission Control UI
│   ├── dashboard.py      # Streamlit interface
│   └── README.md
│
├── shared/               # Service 4: Common Resources
│   ├── config.yaml       # Companies & keywords
│   ├── jobs.db           # SQLite database
│   └── README.md
│
├── templates/            # LaTeX templates
│   └── resume_template.tex
│
├── tailored_resumes/     # AI-generated resumes (auto-created)
├── logs/                 # Application logs
├── venv/                 # Python environment
│
├── run_watcher.bat       # Launch watcher
├── run_tailor.bat        # Launch resume tailor
├── run_dashboard.bat     # Launch dashboard
├── setup.bat             # Initial setup
│
├── .env                  # API keys & secrets
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Setup
```cmd
setup.bat
```

### 2. Configure
Edit `.env`:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_URL
GEMINI_API_KEY=your-gemini-api-key-here
```

Edit `tailor/tailor_config.yaml` with your resume data:
```yaml
personal_info:
  name: "Your Full Name"
  email: "your.email@example.com"

original_summary: "Your professional summary..."
original_experience:
  - "Your experience bullet 1"
  - "Your experience bullet 2"
```

### 3. Run Services
```cmd
run_watcher.bat      # Start monitoring
run_tailor.bat       # Generate tailored resumes
run_dashboard.bat    # Open UI at localhost:8501
```

## 🎯 Microservices

### 1️⃣ Watcher (Job Monitor)
- Scrapes 5 Japanese tech companies
- SQLite database integration
- Discord notifications
- Runs independently

**Location:** `watcher/watcher.py`

### 2️⃣ Tailor (AI Resume Brain) 🧠 **NEW**
- Uses Gemini 2.5 Pro to tailor resumes
- Analyzes job descriptions
- Reframes experience to match JD requirements
- Generates LaTeX resumes

**Location:** `tailor/resume_tailor.py`

### 3️⃣ Dashboard (Mission Control)
- Streamlit web interface
- Real-time job tracking
- Visual analytics
- Status management

**Location:** `dashboard/dashboard.py`

### 4️⃣ Shared Resources
- **config.yaml** - Target companies & keywords
- **jobs.db** - Centralized SQLite database
- Shared by all services

**Location:** `shared/`

## ⚙️ Configuration

Edit `shared/config.yaml`:
```yaml
companies:
  - name: "Company Name"
    url: "https://company.com/careers"
    keywords:
      - "New Graduate"
      - "2026"
```

## 🔧 Features

✅ **Phase 2 Complete:** 🎉
- **Resume Tailor operational**
- **Gemini 2.5 Pro integration working**
- **Interactive CLI ready**
- **Watcher integration complete**

⏳ **Future Phases:**
- P**Watcher** finds new jobs automatically
2. **Dashboard** shows new opportunities
3. **Tailor** generates custom resume for each job
4. Review and apply with confidence!

### Resume Tailoring Workflow 🧠
```cmd
# Interactive mode (easiest)
run_tailor.bat

# Or from discovered jobs
python tailor/integration.py
```

The AI will:
- Analyze the job description
- Rewrite your summary to match the role
- Reframe your experience bullets to highlight relevant skills
- Reorder your skills to prioritize what matters
- Generate a LaTeX resume ready to compileependent, scalable services

## 📊 Current Status

✅ **Phase 1 Complete:**
- Watcher service operational
- Dashboard functional
- Database integration working
- Microservices architecture implemented

⏳ **Future Phases:**
- Phase 2: AI Resume Tailoring (Feb 2025)
- Phase 3: PDF Generation (Mar 2025)

## 💡 Usage

### Daily Workflow
1. Dashboard shows new jobs automatically
2. Click "View Job" to read description
3. Update status: Pending → Applied → Interview
4. Track progress in analytics

### tailor/README.md** - Resume tailoring guide 🧠
- **Automation
Schedule watcher with Windows Task Scheduler:
- Run `run_watcher.bat` twice daily (8 AM, 8 PM)

## 📈 Architecture Benefits

✅ **Separation of Concerns:** Each service has one job
✅ **Independent Scaling:** Run multiple watchers if needed
✅ **Shared Database:** Single source of truth
✅ **Easy Maintenance:** Update services independently

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
**Architecture:** Microservices
**Status:** ✅ Production Ready
**AI:** Gemini 2.5 Pro
**Current Phase:** Phase 2 Complete - Resume Tailoring Live! 🎉

🎯 **"Smart Watching + Smart Tailoring = Dream Job

- **watcher/README.md** - Monitoring service details
- **dashboard/README.md** - UI service details
- **shared/README.md** - Configuration guide
- **START_HERE.md** - Complete setup guide
- **CHECKLIST.md** - Validation steps

## 🎯 Target Companies

- Woven by Toyota
- Sony
- Rakuten
- Mercari
- Preferred Networks

---

**Built:** December 2025
**Architecture:** Microservices
**Status:** ✅ Production Ready
**Next:** AI Resume Tailoring (Phase 2)

🎯 **"The Job Sniper - Apply First, Win First"**
