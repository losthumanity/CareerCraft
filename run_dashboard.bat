@echo off
REM Launch Mission Control Dashboard
cd /d %~dp0
call venv\Scripts\activate
cd dashboard
streamlit run dashboard.py
