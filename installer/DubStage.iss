; ============================================================================
;  DubStage.iss - Windows-Installer fuer DubForge und DubStage
;  DubStage.iss - Windows installer for DubForge and DubStage
;
;  Baut Setup.exe mit Inno Setup 6.3+. Nicht direkt aufrufen, sondern ueber
;  installer\build.ps1 - das legt vorher das mitgelieferte Python in
;  build\runtime an und uebergibt die Version.
;
;  Was die Installation macht:
;    - installiert pro Benutzer nach %LOCALAPPDATA%\Programs\DubStage,
;      ohne Adminrechte. Der Ordner bleibt beschreibbar - packs/, dubs/,
;      Einstellungen und der eingebaute Updater brauchen das.
;    - bringt ein eigenes Python mit allen Grundpaketen mit (runtime\),
;      ein vorhandenes Python wird weder gebraucht noch angefasst.
;    - laedt ffmpeg nach tools\ (Fortschrittsanzeige, zwei Quellen).
;    - installiert auf Wunsch Demucs und die Spracherkennung per pip.
;    - legt Startmenue- und optional Desktop-Verknuepfungen mit eigenem
;      Symbol an.
; ============================================================================

#if VER < EncodeVer(6,3,0)
  #error Inno Setup 6.3 oder neuer wird gebraucht / Inno Setup 6.3+ required
#endif

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName      "DubStage"
#define AppPublisher "xmrius"
#define AppURL       "https://github.com/xmrius/dubstage"
#define Root         ".."
#define Runtime      "..\build\runtime"

[Setup]
; Nie aendern - daran erkennt Windows spaetere Versionen als Update.
AppId={{3917C80D-DCDB-4BF0-AD51-D2368007F5C4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
UninstallDisplayName=DubStage & DubForge
UninstallDisplayIcon={app}\assets\dubstage.ico

; Pro Benutzer, ohne UAC-Abfrage.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

OutputDir={#Root}\dist
OutputBaseFilename=DubStage-Setup-{#AppVersion}
SetupIconFile={#Root}\assets\dubstage.ico
WizardStyle=modern
WizardImageFile=wizard-large-164.bmp,wizard-large-246.bmp,wizard-large-328.bmp
WizardSmallImageFile=wizard-small-55.bmp,wizard-small-83.bmp,wizard-small-110.bmp
Compression=lzma2/max
SolidCompression=yes

; Laufende DubForge/DubStage vor dem Ueberschreiben schliessen.
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
ShowLanguageDialog=auto

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
de.TypeStandard=Standard
de.TypeFull=Alles (mit Stimmen-Trennung und Untertiteln)
de.TypeCustom=Benutzerdefiniert
de.CompMain=DubForge und DubStage
de.CompDemucs=Stimmen-Trennung mit Demucs (lädt PyTorch, bis ca. 2 GB)
de.CompAsr=Automatische Untertitel mit faster-whisper (Modell wird bei erster Nutzung geladen)
de.LaunchStage=DubStage starten
de.LaunchForge=DubForge starten
de.CommentForge=Dub-Packs aus Videos bauen
de.CommentStage=Szenen nachsprechen und mit eigener Stimme abspielen
de.FfmpegTitle=ffmpeg wird heruntergeladen
de.FfmpegDesc=DubForge und DubStage brauchen ffmpeg für Video und Ton (ca. 100–150 MB).
de.FfmpegFailed=ffmpeg konnte nicht heruntergeladen werden. Die Installation wird fortgesetzt.%n%nOhne ffmpeg laufen die Programme nicht. Setup später erneut ausführen oder ffmpeg.exe und ffprobe.exe von Hand nach "%1\tools" kopieren.
de.StatusFfmpeg=ffmpeg wird eingerichtet ...
de.StatusBase=Python-Pakete werden aktualisiert ...
de.StatusDemucs=Demucs wird installiert – das kann einige Minuten dauern ...
de.StatusAsr=Spracherkennung wird installiert ...
de.PartFailed=Einige Teile konnten nicht eingerichtet werden:%1%n%nDubForge und DubStage lassen sich trotzdem starten. Einzelheiten stehen im Setup-Protokoll:%n%2%n%nSetup später erneut ausführen, um es noch einmal zu versuchen.
de.AskDeleteData=Sollen auch deine Packs, Aufnahmen und Einstellungen gelöscht werden?%n%n%1%n%nMit "Nein" bleiben sie erhalten.

en.TypeStandard=Standard
en.TypeFull=Everything (with vocal separation and captions)
en.TypeCustom=Custom
en.CompMain=DubForge and DubStage
en.CompDemucs=Vocal separation with Demucs (downloads PyTorch, up to ~2 GB)
en.CompAsr=Automatic captions with faster-whisper (model downloads on first use)
en.LaunchStage=Start DubStage
en.LaunchForge=Start DubForge
en.CommentForge=Build dub packs from video
en.CommentStage=Dub scenes and play them back in your own voice
en.FfmpegTitle=Downloading ffmpeg
en.FfmpegDesc=DubForge and DubStage need ffmpeg for video and audio (about 100–150 MB).
en.FfmpegFailed=ffmpeg could not be downloaded. Setup will continue.%n%nThe programs do not run without ffmpeg. Run the setup again later, or copy ffmpeg.exe and ffprobe.exe into "%1\tools" by hand.
en.StatusFfmpeg=Setting up ffmpeg ...
en.StatusBase=Updating Python packages ...
en.StatusDemucs=Installing Demucs - this can take a few minutes ...
en.StatusAsr=Installing speech recognition ...
en.PartFailed=Some parts could not be set up:%1%n%nDubForge and DubStage will still start. Details are in the setup log:%n%2%n%nRun the setup again later to retry.
en.AskDeleteData=Also delete your packs, recordings and settings?%n%n%1%n%nChoose "No" to keep them.

[Types]
Name: "standard"; Description: "{cm:TypeStandard}"
Name: "full"; Description: "{cm:TypeFull}"
Name: "custom"; Description: "{cm:TypeCustom}"; Flags: iscustom

[Components]
Name: "main"; Description: "{cm:CompMain}"; Types: standard full custom; Flags: fixed
Name: "demucs"; Description: "{cm:CompDemucs}"; Types: full; ExtraDiskSpaceRequired: 2000000000
Name: "asr"; Description: "{cm:CompAsr}"; Types: full; ExtraDiskSpaceRequired: 400000000

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Root}\DubForge.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\DubStage.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\requirements*.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\README_EN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\LIESMICH.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "{#Runtime}\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DubForge"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubForge.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\dubforge.ico"; Comment: "{cm:CommentForge}"; AppUserModelID: "xmrius.DubStage.DubForge"
Name: "{autoprograms}\DubStage"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubStage.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\dubstage.ico"; Comment: "{cm:CommentStage}"; AppUserModelID: "xmrius.DubStage.DubStage"
Name: "{autodesktop}\DubForge"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubForge.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\dubforge.ico"; Comment: "{cm:CommentForge}"; AppUserModelID: "xmrius.DubStage.DubForge"; Tasks: desktopicon
Name: "{autodesktop}\DubStage"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubStage.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\dubstage.ico"; Comment: "{cm:CommentStage}"; AppUserModelID: "xmrius.DubStage.DubStage"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubStage.pyw"""; WorkingDir: "{app}"; Description: "{cm:LaunchStage}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\DubForge.pyw"""; WorkingDir: "{app}"; Description: "{cm:LaunchForge}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; Was nach der Installation dazukam: per pip nachinstallierte Pakete, ffmpeg,
; Dateien aus Updates der App selbst. packs\, dubs\ und die Einstellungen
; fragt CurUninstallStepChanged ab.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\*.py"
Type: files; Name: "{app}\*.pyw"
Type: files; Name: "{app}\*.md"
Type: files; Name: "{app}\*.txt"
Type: files; Name: "{app}\*.bat"

[Code]
const
  FfmpegUrl1 = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip';
  FfmpegUrl2 = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';
  PipArgs = '-m pip install --upgrade --disable-pip-version-check --no-warn-script-location --progress-bar off ';

var
  DownloadPage: TDownloadWizardPage;
  FfmpegZip: String;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing),
    SetupMessage(msgPreparingDesc), @OnDownloadProgress);
  DownloadPage.ShowBaseNameInsteadOfUrl := True;
end;

function PSQuote(const S: String): String;
var
  T: String;
begin
  T := S;
  StringChangeEx(T, '''', '''''', True);
  Result := '''' + T + '''';
end;

{ ------------------------------------------------------------ ffmpeg laden }

function TryDownload(const Url: String): Boolean;
begin
  DownloadPage.Clear;
  DownloadPage.Add(Url, 'ffmpeg.zip', '');
  try
    DownloadPage.Download;
    Result := True;
  except
    Log('ffmpeg: ' + Url + ' - ' + GetExceptionMessage);
    Result := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID <> wpReady then
    exit;
  FfmpegZip := '';
  { Bei einer Neuinstallation oder Reparatur ueber eine bestehende bleibt ein
    vorhandenes ffmpeg einfach liegen. }
  if FileExists(AddBackslash(WizardDirValue) + 'toolsfmpeg.exe') then
    exit;

  DownloadPage.SetText(CustomMessage('FfmpegTitle'), CustomMessage('FfmpegDesc'));
  DownloadPage.Show;
  try
    if TryDownload(FfmpegUrl1) then
      FfmpegZip := ExpandConstant('{tmp}fmpeg.zip')
    else if DownloadPage.AbortedByUser then
      Result := False
    else if TryDownload(FfmpegUrl2) then
      FfmpegZip := ExpandConstant('{tmp}fmpeg.zip')
    else if DownloadPage.AbortedByUser then
      Result := False
    else
      SuppressibleMsgBox(FmtMessage(CustomMessage('FfmpegFailed'), [WizardDirValue]),
        mbError, MB_OK, IDOK);
  finally
    DownloadPage.Hide;
  end;
end;

{ ------------------------------------------------------- nach dem Kopieren }

procedure ShowLine(const S: String; const Error, FirstLine: Boolean);
begin
  Log(S);
  if Trim(S) <> '' then
    WizardForm.FilenameLabel.Caption := Copy(Trim(S), 1, 110);
end;

function RunLogged(const Status, Filename, Params: String): Boolean;
var
  Code: Integer;
begin
  WizardForm.StatusLabel.Caption := Status;
  WizardForm.FilenameLabel.Caption := '';
  Log('> ' + Filename + ' ' + Params);
  Result := ExecAndLogOutput(Filename, Params, ExpandConstant('{app}'), SW_HIDE,
    ewWaitUntilTerminated, Code, @ShowLine) and (Code = 0);
  if not Result then
    Log('Fehlgeschlagen, Code ' + IntToStr(Code));
end;

function RunPip(const Status, Args: String): Boolean;
begin
  Result := RunLogged(Status, ExpandConstant('{app}
untime\python.exe'), PipArgs + Args);
end;

function InstallFfmpeg: Boolean;
var
  X, Tools, Cmd: String;
begin
  X := ExpandConstant('{tmp}fmpeg_x');
  Tools := ExpandConstant('{app}	ools');
  ForceDirectories(Tools);
  { ZipFile statt Expand-Archive: in Windows PowerShell 5.1 um ein
    Vielfaches schneller. Aus dem bin-Ordner kommen ffmpeg, ffprobe, ffplay. }
  Cmd := '-NoProfile -ExecutionPolicy Bypass -Command "' +
    '$ErrorActionPreference = ''Stop''; ' +
    'Add-Type -AssemblyName System.IO.Compression.FileSystem; ' +
    '[IO.Compression.ZipFile]::ExtractToDirectory(' + PSQuote(FfmpegZip) + ', ' + PSQuote(X) + '); ' +
    '$exe = Get-ChildItem -LiteralPath ' + PSQuote(X) + ' -Recurse -Filter ffmpeg.exe | Select-Object -First 1; ' +
    'Get-ChildItem -LiteralPath $exe.DirectoryName -Filter *.exe | Copy-Item -Destination ' + PSQuote(Tools) + ' -Force"';
  RunLogged(CustomMessage('StatusFfmpeg'), 'powershell.exe', Cmd);
  DelTree(X, True, True, True);
  DeleteFile(FfmpegZip);
  Result := FileExists(Tools + 'fmpeg.exe') and FileExists(Tools + 'fprobe.exe');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Failed: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  Failed := '';
  WizardForm.ProgressGauge.Style := npbstMarquee;
  try
    if FfmpegZip <> '' then
      if not InstallFfmpeg then
        Failed := Failed + #13#10 + '  - ffmpeg';

    { yt-dlp muss mit YouTube Schritt halten - frisch holen. Ohne Netz bleibt
      die mitgelieferte Fassung, das ist kein Fehler. }
    RunPip(CustomMessage('StatusBase'), '--retries 1 --timeout 20 yt-dlp');

    if WizardIsComponentSelected('demucs') then
      if not RunPip(CustomMessage('StatusDemucs'),
                    '-r "' + ExpandConstant('{app}
equirements-demucs.txt') + '"') then
        Failed := Failed + #13#10 + '  - Demucs';

    if WizardIsComponentSelected('asr') then
      if not RunPip(CustomMessage('StatusAsr'),
                    '-r "' + ExpandConstant('{app}
equirements-transcription.txt') + '"') then
        Failed := Failed + #13#10 + '  - faster-whisper';
  finally
    WizardForm.ProgressGauge.Style := npbstNormal;
    WizardForm.FilenameLabel.Caption := '';
  end;

  if Failed <> '' then
    { Eine Zeile, die mit "[" beginnt, haelt Inno fuer einen Abschnitt. }
    SuppressibleMsgBox(FmtMessage(CustomMessage('PartFailed'), [Failed, ExpandConstant('{log}')]),
      mbError, MB_OK, IDOK);
end;

{ ------------------------------------------------------------ Deinstallation }

function DirHasFiles(const Dir: String): Boolean;
var
  F: TFindRec;
begin
  Result := False;
  if FindFirst(AddBackslash(Dir) + '*', F) then
  try
    repeat
      if (F.Name <> '.') and (F.Name <> '..') then begin
        Result := True;
        break;
      end;
    until not FindNext(F);
  finally
    FindClose(F);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  App: String;
  Wipe: Boolean;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  App := ExpandConstant('{app}');
  if DirHasFiles(App + '\packs') or DirHasFiles(App + '\dubs') then
    Wipe := SuppressibleMsgBox(FmtMessage(CustomMessage('AskDeleteData'), [App]),
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES
  else
    Wipe := True;             { nichts Eigenes da - nur Einstellungen }
  if Wipe then begin
    DelTree(App + '\packs', True, True, True);
    DelTree(App + '\dubs', True, True, True);
    DeleteFile(App + '\dubforge_settings.json');
    DeleteFile(App + '\dubstage_settings.json');
  end;
  RemoveDir(App);
end;
