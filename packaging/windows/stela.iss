; Inno Setup installer script for Stela
; Build output (stela.exe and assets) should be staged under dist/windows

#define MyAppName "Stela"
#define MyAppPublisher "Flet"
#define MyAppExeName "stela.exe"
#ifndef AppSourceDir
	#define AppSourceDir "dist\\windows"
#endif

[Setup]
AppId={{B3F3A37F-3F4E-4609-8D6F-A0E0FC31D3D1}
AppName={#MyAppName}
AppVersion=0.1.0
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=stela-setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
ChangesAssociations=yes

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Registry]
Root: HKCU; Subkey: "Software\Classes\Stela.Document"; ValueType: string; ValueName: ""; ValueData: "Stela Document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Stela.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "Stela.Document"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\.epub\OpenWithProgids"; ValueType: string; ValueName: "Stela.Document"; ValueData: ""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
