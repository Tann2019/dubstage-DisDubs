<#
  build.ps1 - baut dist\DubForge-DisDubs-Setup-<Version>.exe
  build.ps1 - builds dist\DubForge-DisDubs-Setup-<version>.exe

  Schritte / steps:
    1. eigenstaendiges Python (python-build-standalone, mit tkinter) laden,
       Pruefsumme kontrollieren und nach build\runtime entpacken
    2. Grundpakete aus requirements.txt hineininstallieren
    3. pruefen, dass alles importierbar ist
    4. installer\DubStage.iss mit Inno Setup 6.3+ uebersetzen

  Voraussetzung: Windows 10/11 x64 und Inno Setup 6.3 oder neuer
  (winget install JRSoftware.InnoSetup). Aufruf aus dem Projektordner:

      powershell -ExecutionPolicy Bypass -File installer\build.ps1

  Signieren (optional): Liegt ein Code-Signing-Zertifikat als PFX vor,
  vorher setzen - dann werden Setup.exe und Uninstaller signiert:

      $env:CODESIGN_PFX_BASE64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx"))
      $env:CODESIGN_PASSWORD   = "..."

  In GitHub Actions kommen beide aus den gleichnamigen Repository-Secrets.
#>
[CmdletBinding()]
param(
    # Standard: VERSION aus updater.py
    [string]$Version = "",
    # Nur build\runtime vorbereiten, kein Setup.exe
    [switch]$SkipCompile
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"     # Invoke-WebRequest sonst quaelend langsam

$Root = Split-Path -Parent $PSScriptRoot
$Build = Join-Path $Root "build"
$Runtime = Join-Path $Build "runtime"

# Python 3.12 von python-build-standalone: relocatable, bringt tkinter mit -
# anders als das "embeddable" Paket von python.org.
$PyUrl = "https://github.com/astral-sh/python-build-standalone/releases/download/20260901/" +
         "cpython-3.12.14%2B20260901-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
$PySha = "7c45c9622400d578709a9b2cddbe8124cc21d382409d9f13406d706d28e31b14"

function Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }

if (-not $Version) {
    $m = Select-String -Path (Join-Path $Root "updater.py") -Pattern '^VERSION\s*=\s*"([^"]+)"'
    if (-not $m) { throw "VERSION in updater.py nicht gefunden." }
    $Version = $m.Matches[0].Groups[1].Value
}
Step "DubForge DisDubs $Version"

# ------------------------------------------------------------------ Python
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$archive = Join-Path $Build "python.tar.gz"
$ok = (Test-Path $archive) -and ((Get-FileHash $archive -Algorithm SHA256).Hash -eq $PySha)
if (-not $ok) {
    Step "Python laden"
    Invoke-WebRequest -Uri $PyUrl -OutFile $archive -UseBasicParsing
    $hash = (Get-FileHash $archive -Algorithm SHA256).Hash
    if ($hash -ne $PySha) { throw "Pruefsumme passt nicht: $hash" }
}

Step "Python entpacken"
if (Test-Path $Runtime) { Remove-Item $Runtime -Recurse -Force }
$unpack = Join-Path $Build "unpack"
if (Test-Path $unpack) { Remove-Item $unpack -Recurse -Force }
New-Item -ItemType Directory -Force -Path $unpack | Out-Null
# Ausdruecklich das tar von Windows: ein GNU-tar aus Git for Windows, das im
# PATH davor liegen kann, haelt "C:" fuer einen entfernten Rechner.
& "$env:SystemRoot\System32\tar.exe" -xzf $archive -C $unpack
if ($LASTEXITCODE -ne 0) { throw "tar ist fehlgeschlagen." }
Move-Item (Join-Path $unpack "python") $Runtime
Remove-Item $unpack -Recurse -Force

$py = Join-Path $Runtime "python.exe"

Step "Pakete installieren"
& $py -m pip install --disable-pip-version-check --no-warn-script-location `
    --progress-bar off -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install ist fehlgeschlagen." }

Step "Pruefen"
& $py -c @"
import tkinter, numpy, PIL.ImageTk, sounddevice, yt_dlp
print('Tcl/Tk', tkinter.Tcl().eval('info patchlevel'))
print('numpy', numpy.__version__, '| yt-dlp', yt_dlp.version.__version__)
"@
if ($LASTEXITCODE -ne 0) { throw "Das mitgelieferte Python ist unvollstaendig." }

# Beide Apps muessen sich mit genau diesem Python laden lassen.
Push-Location $Root
try {
    & $py -c "import runpy; [runpy.run_path(p, run_name='check') for p in ('DubForge.pyw', 'DubStage.pyw')]; print('Apps ok')"
    if ($LASTEXITCODE -ne 0) { throw "Die Apps lassen sich nicht laden." }
} finally {
    Pop-Location
}

# pip-Starter in Scripts\ enthalten den absoluten Pfad dieses Build-Ordners
# und liefen nach der Installation ins Leere. Die App ruft pip immer ueber
# "python -m pip" auf, die Starter braucht niemand.
Get-ChildItem (Join-Path $Runtime "Scripts") -Filter *.exe -ErrorAction SilentlyContinue |
    Remove-Item -Force

if ($SkipCompile) {
    Step "Fertig (ohne Setup.exe): $Runtime"
    return
}

# ------------------------------------------------------------ Inno Setup
$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) {
    throw "Inno Setup 6 nicht gefunden. Installieren mit: winget install JRSoftware.InnoSetup"
}

$isccArgs = @("/DAppVersion=$Version")
$pfx = $null
if ($env:CODESIGN_PFX_BASE64) {
    $signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName | Select-Object -Last 1
    if (-not $signtool) { throw "signtool.exe nicht gefunden (Windows SDK installieren)." }
    $pfx = Join-Path $Build "codesign.pfx"
    [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:CODESIGN_PFX_BASE64))
    # $q und $f ersetzt Inno Setup selbst: Anfuehrungszeichen und Zieldatei.
    $cmd = '$q' + $signtool.FullName + '$q sign /f $q' + $pfx + '$q /p $q' + $env:CODESIGN_PASSWORD +
           '$q /fd sha256 /tr http://timestamp.digicert.com /td sha256 /d $qDubForge DisDubs Setup$q $f'
    $isccArgs += @("/DSign", "/Ssigntool=$cmd")
    Step "Signieren eingeschaltet ($($signtool.FullName))"
}

Step "Setup.exe bauen ($iscc)"
try {
    & $iscc @isccArgs (Join-Path $PSScriptRoot "DubStage.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup ist fehlgeschlagen." }
} finally {
    if ($pfx -and (Test-Path $pfx)) { Remove-Item $pfx -Force }
}

$out = Join-Path $Root "dist\DubForge-DisDubs-Setup-$Version.exe"
Step ("Fertig: {0} ({1:N0} MB)" -f $out, ((Get-Item $out).Length / 1MB))
