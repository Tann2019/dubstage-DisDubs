@echo off
title DubStage - auf GitHub veroeffentlichen
cd /d "%~dp0"

set "REPO=https://github.com/xmrius/dubstage.git"
set "TAG=v1.0.0"
set "MSG=DubForge and DubStage"
set "LOG=%~dp0push_log.txt"

echo ============================================================
echo   Veroeffentlichen nach %REPO%
echo ============================================================
echo.
echo Arbeitsordner: %CD%
echo.

echo ---- Lauf %DATE% %TIME% ---- > "%LOG%"
echo Ordner: %CD% >> "%LOG%"

rem ---------------------------------------------------------- Git da?
where git >nul 2>&1
if errorlevel 1 goto :nogit
for /f "delims=" %%v in ('git --version') do echo %%v >> "%LOG%"

rem ------------------------------------------------- Pfad kurz genug?
rem Windows kann Pfade nur bis 260 Zeichen. Git legt in .git tief
rem verschachtelte Dateien an, deshalb hier grosszuegig begrenzen.
set "P=%CD%"
call :laenge "%P%"
echo Pfadlaenge: %LEN% >> "%LOG%"
if %LEN% GTR 150 goto :zulang

rem ------------------------------------------------- Ordner freigeben
rem Auf exFAT/FAT32 (oft externe Platten) speichert Windows keine
rem Dateibesitzer. Git verweigert dann die Arbeit, bis der Ordner
rem ausdruecklich als vertrauenswuerdig eingetragen ist.
set "GITPATH=%CD:\=/%"
git config --global --get-all safe.directory 2>nul | findstr /i /x /c:"%GITPATH%" >nul
if errorlevel 1 git config --global --add safe.directory "%GITPATH%"
echo safe.directory: %GITPATH% >> "%LOG%"

rem ---------------------------------------------------------- schreibbar?
break > "%~dp0.schreibtest" 2>nul
if not exist "%~dp0.schreibtest" goto :nowrite
del "%~dp0.schreibtest" >nul 2>&1

rem ---------------------------------------------------------- Repo
if exist ".git\config" goto :vorhanden

echo [1/6] Repository anlegen ...
git init >> "%LOG%" 2>&1
if not exist ".git\config" goto :noinit
echo       ok
goto :remote

:vorhanden
echo [1/6] Vorhandenes Repository gefunden.

:remote
echo [2/6] Verbindung zum Repo setzen ...
git remote remove origin >nul 2>&1
git remote add origin "%REPO%"
if errorlevel 1 goto :fail
echo       ok

echo [3/6] Stand aus dem Repo holen ...
git fetch origin main >> "%LOG%" 2>&1
if errorlevel 1 goto :fetchfail
echo       ok

rem Nur beim ersten Mal auf den Remote-Stand aufsetzen
git rev-parse --verify HEAD >nul 2>&1
if not errorlevel 1 goto :ident
git checkout -b main FETCH_HEAD >> "%LOG%" 2>&1
if errorlevel 1 goto :fail

:ident
git config user.name >nul 2>&1
if errorlevel 1 git config user.name "xmrius"
git config user.email >nul 2>&1
if errorlevel 1 git config user.email "xmrius@users.noreply.github.com"

rem ---------------------------------------------------------- Commit
echo [4/6] Dateien vormerken ...
git add -A
if errorlevel 1 goto :fail
git status --short
echo.

git diff --cached --quiet
if not errorlevel 1 goto :push
echo [5/6] Commit ...
git commit -m "%MSG%" >> "%LOG%" 2>&1
if errorlevel 1 goto :fail
echo       ok
echo.

rem ---------------------------------------------------------- Push
:push
echo [6/6] Hochladen ...
echo       Beim ersten Mal oeffnet sich das GitHub-Login im Browser.
git push -u origin main
if errorlevel 1 goto :pushfail
echo.

rem ---------------------------------------------------------- Release
git rev-parse "%TAG%" >nul 2>&1
if not errorlevel 1 goto :fertig
git tag -a "%TAG%" -m "%MSG% %TAG%" >nul 2>&1
git push origin "%TAG%"
if errorlevel 1 echo       [i] Tag konnte nicht gepusht werden.

where gh >nul 2>&1
if errorlevel 1 goto :kein_gh
gh release create "%TAG%" --title "%MSG% %TAG%" --generate-notes
goto :fertig

:kein_gh
echo       [i] GitHub CLI nicht installiert - der Tag ist gesetzt, das
echo           Release kannst du auf der Repo-Seite daraus erzeugen.

:fertig
echo.
echo ============================================================
echo   Fertig:  https://github.com/xmrius/dubstage
echo ============================================================
goto :ende

rem ---------------------------------------------------------- Fehler
:zulang
echo [!] Der Ordnerpfad ist zu lang fuer Git ^(%LEN% Zeichen^).
echo.
echo     Windows kann Pfade nur bis 260 Zeichen. Git legt in .git
echo     tief verschachtelte Dateien an und scheitert deshalb hier.
echo.
echo     So geht es:
echo       1. Neuen Ordner anlegen, z.B.  F:\dubstage
echo       2. ALLE Dateien aus diesem Ordner dorthin kopieren
echo       3. "Push to GitHub.bat" dort starten
echo.
echo     Das ist ohnehin der bessere Ort - dieser Ordner hier ist
echo     der Zwischenspeicher der App und kann geleert werden.
goto :ende

:laenge
rem Zeichen zaehlen, ohne externe Hilfsmittel
setlocal enabledelayedexpansion
set "S=%~1"
set "N=0"
:zaehl
if defined S set "S=!S:~1!" & set /a N+=1 & goto :zaehl
endlocal & set "LEN=%N%"
exit /b 0

:nogit
echo [!] Git ist nicht installiert.
echo     https://git-scm.com/download/win
goto :ende

:nowrite
echo [!] In diesem Ordner darf nicht geschrieben werden:
echo     %CD%
echo     Kopiere die Dateien in einen normalen Ordner, z.B. F:\DubForge,
echo     und starte das Skript dort erneut.
goto :ende

:noinit
echo [!] "git init" hat kein Repository angelegt.
echo     Haeufigste Ursachen: fehlende Schreibrechte oder ein Virenscanner.
echo     Details stehen in push_log.txt
goto :ende

:fetchfail
echo [!] Das Repo war nicht erreichbar.
echo     Internet pruefen, oder ob %REPO% wirklich existiert.
echo     Details stehen in push_log.txt
goto :ende

:pushfail
echo.
echo [!] Push fehlgeschlagen - meist fehlt die Anmeldung.
echo       a^) Skript nochmal starten, dann kommt das Browser-Login
echo       b^) GitHub CLI:  winget install GitHub.cli   dann   gh auth login
goto :ende

:fail
echo [!] Ein Git-Befehl ist fehlgeschlagen. Details in push_log.txt

:ende
echo.
echo (Protokoll: push_log.txt)
pause
