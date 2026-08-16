@echo off
rem  DubForge starten. Beim ersten Mal richtet sich alles selbst ein.
rem  Start DubForge. On the first run it sets itself up.
setlocal
cd /d "%~dp0"
set "TRIED="

:detect
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

rem Der Microsoft-Store-Platzhalter heisst auch "python", oeffnet aber nur
rem den Store.  /  The Microsoft Store stub is called "python" too.
if defined PY ( %PY% -c "import sys" >nul 2>&1 || set "PY=" )
if not defined PY goto :setup

rem Fenster ohne Konsole starten, wenn es das gibt.
set "PYW=%PY%"
where pyw >nul 2>&1 && set "PYW=pyw -3"
if "%PYW%"=="%PY%" ( where pythonw >nul 2>&1 && set "PYW=pythonw" )

rem Nach der Einrichtung liegt tools\.setup-done - dann geht es sofort los.
if exist "tools\.setup-done" goto :run

rem Sonst einmal nachsehen, ob trotzdem alles da ist (Einrichtung von Hand).
%PY% -c "import numpy" >nul 2>&1
if errorlevel 1 goto :setup
if exist "tools\ffmpeg.exe" goto :mark
where ffmpeg >nul 2>&1
if errorlevel 1 goto :setup

:mark
if not exist "tools" mkdir "tools" >nul 2>&1
>"tools\.setup-done" echo ok
goto :run

:setup
if defined TRIED goto :giveup
echo.
echo   Der erste Start richtet noch kurz alles ein.
echo   First start - setting things up. This only happens once.
echo.
call "%~dp0Setup.bat"
set "TRIED=1"
goto :detect

:giveup
echo.
echo   Es fehlt noch etwas. Bitte Setup.bat ausfuehren und danach
echo   "Start DubForge.bat" erneut starten.
echo   Something is still missing. Please run Setup.bat, then start
echo   "Start DubForge.bat" again.
echo.
pause
exit /b 1

:run
start "" %PYW% "%~dp0DubForge.pyw"
