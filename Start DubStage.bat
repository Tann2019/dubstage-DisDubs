@echo off
cd /d "%~dp0"
set "PY="
where pyw >nul 2>&1 && set "PY=pyw -3"
if not defined PY ( where pythonw >nul 2>&1 && set "PY=pythonw" )
if not defined PY ( where py >nul 2>&1 && set "PY=py -3" )
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

rem Store-Platzhalter aussortieren / weed out the Microsoft Store stub
if defined PY ( %PY% -c "import sys" >nul 2>&1 || set "PY=" )

if not defined PY (
  echo Python wurde nicht gefunden. Bitte zuerst Setup.bat ausfuehren.
  echo Python was not found. Please run Setup.bat first.
  pause
  exit /b 1
)

start "" %PY% "%~dp0DubStage.pyw"
