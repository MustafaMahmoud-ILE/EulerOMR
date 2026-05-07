; Euler OMR Inno Setup Script
; This script generates a professional Windows Installer for Euler OMR.

#define AppName "Euler OMR"
#define AppVersion "1.1.5"
#define AppPublisher "Mustafa Mahmoud"
#define AppURL "https://github.com/MustafaMahmoud-ILE/EulerOMR"
#define AppExeName "EulerOMR.exe"
#define AppIconName "app.ico"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{9F2E7D1A-8B3C-4D2E-A1B2-C3D4E5F6A7B8}
AppName={#AppName}
AppVersion={#AppVersion}
;AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=EulerOMR_Setup_v{#AppVersion}
SetupIconFile=..\assets\icons\{#AppIconName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes

[Registry]
Root: HKA; Subkey: "Software\Classes\.eomrp"; ValueType: string; ValueName: ""; ValueData: "{#AppName}.Project"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.eomrp\OpenWithProgids"; ValueType: string; ValueName: "{#AppName}.Project"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#AppName}.Project"; ValueType: string; ValueName: ""; ValueData: "{#AppName} Project File"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#AppName}.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#AppName}.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

Root: HKA; Subkey: "Software\Classes\.eomrt"; ValueType: string; ValueName: ""; ValueData: "{#AppName}.Template"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.eomrt\OpenWithProgids"; ValueType: string; ValueName: "{#AppName}.Template"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#AppName}.Template"; ValueType: string; ValueName: ""; ValueData: "{#AppName} Template File"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#AppName}.Template\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#AppName}.Template\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\EulerOMR\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\EulerOMR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icons\{#AppIconName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icons\{#AppIconName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
