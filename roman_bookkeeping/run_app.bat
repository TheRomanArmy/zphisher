@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
  echo Run: py -3 -m venv .venv
  exit /b 1
)

.venv\Scripts\python.exe -m flask --app run.py run
