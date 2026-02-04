#define MyAppName "PDF Merger"
#define MyAppExeName "pdf-merger.exe"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "charettep"
#define MyAppURL ""
#define MyAppId "{F4B1E63B-0A4F-4D4A-8E8D-9E7F63B52C3A}"
#define MyAppSetupBaseName "pdf-merger-setup"
; Allow overriding the EXE path from the command line:
; iscc /DMyAppExePath="C:\path\to\pdf-merger.exe" installer.iss
#ifndef MyAppExePath
  #define MyAppExePath "dist\\pdf-merger.exe"
#endif

[Setup]
AppId={{#MyAppId}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename={#MyAppSetupBaseName}
WizardStyle=modern

[Files]
Source: "{#MyAppExePath}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
