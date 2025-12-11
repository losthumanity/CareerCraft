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
├── dashboard/            # Service 2: Mission Control UI
│   ├── dashboard.py      # Streamlit interface
│   └── README.md
│
├── shared/               # Service 3: Common Resources
│   ├── config.yaml       # Companies & keywords
│   ├── jobs.db           # SQLite database
│   └── README.md
│
├── logs/                 # Application logs
├── venv/                 # Python environment
│
├── run_watcher.bat       # Launch watcher
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
```

### 3. Run Services
```cmd
run_watcher.bat      # Start monitoring
run_dashboard.bat    # Open UI at localhost:8501
```

## 🎯 Microservices

### 1️⃣ Watcher (Job Monitor)
- Scrapes 5 Japanese tech companies
- SQLite database integration
- Discord notifications
- Runs independently

**Location:** `watcher/watcher.py`

### 2️⃣ Dashboard (Mission Control)
- Streamlit web interface
- Real-time job tracking
- Visual analytics
- Status management

**Location:** `dashboard/dashboard.py`

### 3️⃣ Shared Resources
- **config.yaml** - Target companies & keywords
- **jobs.db** - Centralized SQLite database
- Shared by both services

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

- **Automated Monitoring:** 24/7 job discovery
- **Smart Notifications:** Discord alerts for new jobs
- **Visual Dashboard:** Track applications in real-time
- **Database Tracking:** No duplicate notifications
- **Microservice Design:** Independent, scalable services

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

### Automation
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
| Watcher can't find config | Check `shared/config.yaml` exists |
| Dashboard shows no data | Run watcher first to populate database |
| Path errors | Services use relative paths (`../shared/`) |

## 📚 Documentation

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
