; MemoMe Windows Installer — Inno Setup 6 script
; Download Inno Setup from: https://jrsoftware.org/isinfo.php
;
; To build: open this file in Inno Setup Compiler → Compile
; Output: installer/MemoMe-v3.0-windows-setup.exe

#define MyAppName      "MemoMe"
#define MyAppVersion   "3.0"
#define MyAppPublisher "MemoMe"
#define MyAppURL       "https://github.com/YOUR_USERNAME/memome"
#define MyAppExeName   "MemoMe.exe"
#define MyAppID        "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
AppId={{#MyAppID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; UI
WizardStyle=modern
WizardSizePercent=120
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Require Windows 10 or later
MinVersion=10.0.17763
; Output
OutputDir=installer
OutputBaseFilename=MemoMe-v{#MyAppVersion}-windows-setup
; Privileges
PrivilegesRequired=lowest           ; install per-user, no UAC prompt
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon";    Description: "Start MemoMe when Windows starts";  GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Copy the entire PyInstaller output folder
Source: "dist\MemoMe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Startup entry (optional)
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Launch MemoMe after install
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill the process before uninstalling
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillMemoMe"

[Code]
{ Check that Ollama is installed — warn if not, but don't block install }
function OllamaInstalled(): Boolean;
var
  OllamaPath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Ollama', 'OllamaPath', OllamaPath)
         or FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'))
         or FileExists('C:\Program Files\Ollama\ollama.exe');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not OllamaInstalled() then
    begin
      MsgBox(
        'MemoMe is installed!' + #13#10 + #13#10 +
        'Before you start recording, you need Ollama for AI translation:' + #13#10 + #13#10 +
        '  1. Download Ollama from  https://ollama.com' + #13#10 +
        '  2. Install it (it runs as a background service)' + #13#10 +
        '  3. Open a terminal and run:  ollama pull qwen3.5:9b' + #13#10 + #13#10 +
        'MemoMe will show a "Ready" badge once Ollama is connected.',
        mbInformation, MB_OK
      );
    end;
  end;
end;
