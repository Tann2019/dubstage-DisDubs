@echo off
setlocal
cd /d "%~dp0"

rem ===================================================== Sprache / language
rem  Was im Werkzeug gewaehlt wurde gilt, sonst die Sprache von Windows.
rem  Alles Weitere laeuft dann nur noch in dieser einen Sprache.
rem  The language picked in the tool wins, otherwise the Windows one.
rem  Everything below then speaks that one language only.
set "L=en"
set "LOC="
for /f "tokens=2,*" %%a in ('reg query "HKCU\Control Panel\International" /v LocaleName 2^>nul') do set "LOC=%%b"
if /i "%LOC:~0,2%"=="de" set "L=de"
if exist "dubforge_settings.json" call :fromjson "dubforge_settings.json"
if exist "dubstage_settings.json" call :fromjson "dubstage_settings.json"
rem Von den Startern uebergeben / handed over by the launchers
if /i "%~1"=="de" set "L=de"
if /i "%~1"=="en" set "L=en"

if "%L%"=="de" title DubForge und DubStage - Einrichtung
if not "%L%"=="de" title DubForge and DubStage - Setup

rem  Texte, die spaeter in Klammer-Bloecken gebraucht werden, muessen hier
rem  oben stehen: in einem Block wird %VAR% beim Einlesen ersetzt, nicht
rem  beim Ausfuehren.  /  Strings used inside parenthesised blocks have to be
rem  set out here - inside a block %VAR% is expanded when the block is read.
set "M_FAIL=       Fehlgeschlagen: "
set "M_DONE=       ffmpeg installiert."
set "M_LNK=       DubForge und DubStage liegen auf dem Desktop."
set "M_NOPE=       Ging nicht: "
if not "%L%"=="de" set "M_FAIL=       Failed: "
if not "%L%"=="de" set "M_DONE=       ffmpeg installed."
if not "%L%"=="de" set "M_LNK=       DubForge and DubStage are on the desktop now."
if not "%L%"=="de" set "M_NOPE=       Did not work: "

echo ============================================================
call :say "  DubForge und DubStage - Einrichtung" "  DubForge and DubStage - Setup"
call :say "  Das dauert beim ersten Mal ein paar Minuten." "  The first run takes a few minutes."
echo ============================================================
echo.

rem ---------------------------------------------------------- Python finden
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

rem Der Microsoft-Store-Platzhalter heisst auch "python", oeffnet aber nur
rem den Store. Erst pruefen, ob der Interpreter wirklich antwortet.
rem The Microsoft Store stub is also called "python" but only opens the
rem Store - check that the interpreter actually answers.
if defined PY (
  %PY% -c "import sys" >nul 2>&1 || set "PY="
)

if not defined PY (
  call :say "[!] Python wurde nicht gefunden." "[!] Python was not found."
  echo.
  call :say "    Ich versuche es ueber winget zu installieren ..." "    Trying to install it via winget ..."
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  echo.
  call :say "    Bitte dieses Fenster schliessen und Setup.bat NEU starten." "    Please close this window and run Setup.bat AGAIN."
  pause
  exit /b 1
)

call :say "[1/4] Python:" "[1/4] Python:"
%PY% -c "import sys;print('      ',sys.version)"
%PY% -c "import sys;sys.exit(0 if sys.version_info[:2]>=(3,9) else 1)" || (
  call :say "[!] Python 3.9 oder neuer wird gebraucht. Bitte aktualisieren." "[!] Python 3.9 or newer is required. Please update."
  pause & exit /b 1
)
echo.

rem ---------------------------------------------------------- Pakete
call :say "[2/4] Python-Pakete installieren (numpy, yt-dlp, pillow, sounddevice) ..." "[2/4] Installing the Python packages (numpy, yt-dlp, pillow, sounddevice) ..."
%PY% -m pip install --upgrade pip --quiet
%PY% -m pip install --upgrade numpy yt-dlp pillow sounddevice || (
  call :say "[!] Installation fehlgeschlagen. Internet pruefen." "[!] Installation failed. Check the internet connection."
  pause & exit /b 1
)
call :say "      ok" "      ok"
call :say "      (pillow und sounddevice werden fuer DubStage gebraucht)" "      (pillow and sounddevice are needed for DubStage)"
echo.

call :say "[3/4] Demucs fuer die Stimmen-Trennung ..." "[3/4] Demucs for the vocal separation ..."
call :say "      Achtung: laedt PyTorch, das sind mehrere hundert MB bis ~2 GB." "      Careful: this pulls in PyTorch, several hundred MB up to ~2 GB."
call :ask "       Jetzt installieren? [J/N] " "       Install it now? [Y/N] "
if errorlevel 3 (
  call :say "      uebersprungen - die Werkzeuge laufen dann ohne Stimmen-Trennung." "      skipped - the tools then work without vocal separation."
) else (
  %PY% -m pip install --upgrade demucs soundfile
  if errorlevel 1 (
    call :say "[!] Demucs konnte nicht installiert werden." "[!] Demucs could not be installed."
    call :say "    Die Werkzeuge funktionieren trotzdem, nur ohne Vocal-Trennung." "    The tools work anyway, just without vocal separation."
  ) else (
    call :say "      ok" "      ok"
  )
)
echo.

rem ---------------------------------------------------------- ffmpeg
call :say "[4/4] ffmpeg pruefen ..." "[4/4] Checking ffmpeg ..."
set "FFOK="
if exist "tools\ffmpeg.exe" set "FFOK=1"
if not defined FFOK ( where ffmpeg >nul 2>&1 && set "FFOK=system" )

if "%FFOK%"=="1"      call :say "      ffmpeg liegt schon in tools\. ok" "      ffmpeg is already in tools\. ok"
if "%FFOK%"=="system" call :say "      System-ffmpeg gefunden. ok" "      Found ffmpeg on the system. ok"

if not defined FFOK (
  call :say "      Kein ffmpeg da - ich lade einen herunter (~100 MB)." "      No ffmpeg here - downloading one (~100 MB)."
  if not exist tools mkdir tools
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$urls=@('https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip','https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip');" ^
    "foreach($u in $urls){ try{" ^
    "  Write-Host ('       -> '+$u);" ^
    "  $z=Join-Path $env:TEMP 'dubforge_ffmpeg.zip';" ^
    "  Invoke-WebRequest -Uri $u -OutFile $z -UseBasicParsing;" ^
    "  $x=Join-Path $env:TEMP 'dubforge_ffmpeg_x'; if(Test-Path $x){Remove-Item $x -Recurse -Force};" ^
    "  Expand-Archive -Path $z -DestinationPath $x -Force;" ^
    "  $exe=Get-ChildItem -Path $x -Recurse -Filter ffmpeg.exe | Select-Object -First 1;" ^
    "  if(-not $exe){continue};" ^
    "  Get-ChildItem -Path $exe.Directory -Filter *.exe | Copy-Item -Destination 'tools' -Force;" ^
    "  Remove-Item $z,$x -Recurse -Force -ErrorAction SilentlyContinue;" ^
    "  Write-Host '%M_DONE%'; exit 0" ^
    "} catch { Write-Host ('%M_FAIL%'+$_.Exception.Message) } };" ^
    "exit 1"
  if exist "tools\ffmpeg.exe" set "FFOK=1"
)

echo.
if defined FFOK (
  rem Merker, damit die Starter nicht jedes Mal neu einrichten wollen.
  rem Marker so the launchers do not set up again on every start.
  if not exist tools mkdir tools
  >"tools\.setup-done" echo %L%

  call :say "[+] Verknuepfungen auf dem Desktop?" "[+] Shortcuts on the desktop?"
  call :ask "       Anlegen? [J/N] " "       Create them? [Y/N] "
  if errorlevel 3 (
    call :say "       uebersprungen" "       skipped"
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "try{ $d=[Environment]::GetFolderPath('Desktop');" ^
      "$w=New-Object -ComObject WScript.Shell;" ^
      "foreach($n in 'DubForge','DubStage'){" ^
      "  $s=$w.CreateShortcut((Join-Path $d ($n+'.lnk')));" ^
      "  $s.TargetPath=(Join-Path '%~dp0' ('Start '+$n+'.bat'));" ^
      "  $s.WorkingDirectory=('%~dp0'.TrimEnd('\'));" ^
      "  $s.Description=$n; $s.Save() };" ^
      "Write-Host '%M_LNK%'" ^
      "} catch { Write-Host ('%M_NOPE%'+$_.Exception.Message) }"
  )
  echo.
)

if not defined FFOK (
  call :say "[!] Es konnte kein ffmpeg eingerichtet werden. Ohne ffmpeg" "[!] No ffmpeg could be set up. Without ffmpeg neither"
  call :say "    laeuft weder DubForge noch DubStage." "    DubForge nor DubStage will run."
  echo.
  call :say "    Manueller Weg:" "    By hand:"
  call :say "      1. https://www.gyan.dev/ffmpeg/builds/  ->  'release full' herunterladen" "      1. https://www.gyan.dev/ffmpeg/builds/  ->  download 'release full'"
  call :say "      2. entpacken, aus dem bin-Ordner ffmpeg.exe, ffprobe.exe, ffplay.exe" "      2. extract it; from the bin folder take ffmpeg.exe, ffprobe.exe, ffplay.exe"
  call :say "      3. in den Ordner 'tools' neben dieser Setup.bat legen" "      3. put them into the 'tools' folder next to this Setup.bat"
  echo.
) else (
  echo ============================================================
  call :say "  Fertig." "  Done."
  call :say "    Packs bauen : 'Start DubForge.bat'" "    Build packs : 'Start DubForge.bat'"
  call :say "    Einsprechen : 'Start DubStage.bat'" "    Record      : 'Start DubStage.bat'"
  echo ============================================================
)
echo.
pause
exit /b 0

rem ===================================================== Helfer / helpers

rem Eine Zeile, in der gewaehlten Sprache. / One line, in the chosen language.
:say
if "%L%"=="de" echo(%~1
if not "%L%"=="de" echo(%~2
goto :eof

rem Eine Frage, in der gewaehlten Sprache. Die Antwort steht danach in
rem errorlevel (1=J, 2=Y, 3=N).  /  One question, in the chosen language;
rem the answer is left in errorlevel (1=J, 2=Y, 3=N).
:ask
if not "%L%"=="de" goto :ask_en
choice /c JYN /n /m "%~1"
goto :eof
:ask_en
choice /c JYN /n /m "%~2"
goto :eof

rem Sprache aus den Einstellungen des Werkzeugs lesen.
rem Read the language from the tool's own settings.
:fromjson
findstr /i /c:"\"lang\": \"de\"" %1 >nul 2>&1 && set "L=de"
findstr /i /c:"\"lang\": \"en\"" %1 >nul 2>&1 && set "L=en"
goto :eof
