@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===========================================================================
echo PHONE SALES DATA WAREHOUSE - BUSINESS INTELLIGENCE DASHBOARD
echo Dang mo trinh duyet tai: http://localhost:8050
echo ===========================================================================
start "" "http://localhost:8050"
.venv\Scripts\python.exe -u web_app.py
pause

