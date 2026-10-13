@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run this first:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo Starting Local Testcase Generator on http://localhost:8501
echo Press Ctrl+C in this window to stop it.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
pause
