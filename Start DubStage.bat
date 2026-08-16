@echo off
rem  DubStage starten. Beim ersten Mal richtet sich alles selbst ein.
rem  Start DubStage. On the first run it sets itself up.
setlocal
cd /d "%~dp0"
set "TRIED="

rem ---------------------------------------------- Sprache / language
set "L=en"
set "LOC="
for /f "tokens=2,*" %%a in ('reg query "HKCU\Control Panel\International" /v LocaleName 2^>nul') do set "LOC=%%b"
if /i "%LOC:~0,2%"=="de" set "L=de"
if exist "dubstage_settings.json" call :fromjson "dubstage_settings.json"

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
%PY% -c "import numpy, PIL, sounddevice" >nul 2>&1
if errorlevel 1 goto :setup
if exist "toolsfmpeg.exe" goto :mark
where ffmpeg >nul 2>&1
if errorlevel 1 goto :setup

:mark
if not exist "tools" mkdir "tools" >nul 2>&1
>"tools\.setup-done" echo %L%
goto :run

:setup
if defined TRIED goto :giveup
echo.
call :say "  Der erste Start richtet noch kurz alles ein." "  First start - setting things up. This only happens once."
echo.
call "%~dp0Setup.bat" %L%
set "TRIED=1"
goto :detect

:giveup
echo.
call :say "  Es fehlt noch etwas. Bitte Setup.bat ausfuehren und danach" "  Something is still missing. Please run Setup.bat, then start"
call :say "  'Start DubStage.bat' erneut starten." "  'Start DubStage.bat' again."
echo.
pause
exit /b 1

:run
start "" %PYW% "%~dp0DubStage.pyw"
exit /b 0

rem ---------------------------------------------- Helfer / helpers

:say
if "%L%"=="de" echo(%~1
if not "%L%"=="de" echo(%~2
goto :eof

:fromjson
findstr /i /c:"\"lang\": \"de\"" %1 >nul 2>&1 && set "L=de"
findstr /i /c:"\"lang\": \"en\"" %1 >nul 2>&1 && set "L=en"
goto :eof
