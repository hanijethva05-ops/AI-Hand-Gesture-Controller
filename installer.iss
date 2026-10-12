 
#define MyAppName "AI Hand Gesture Controller"
#define MyAppVersion "1.0.0"
#define MyAppExeName "AIHandGestureController.exe"

[Setup]
AppId={{D1897F14-537B-4D5A-8B0A-ACDF92FE1B21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\AI Hand Gesture Controller
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=AIHandGestureController.ico
OutputDir=installer_output
OutputBaseFilename=AIHandGestureController_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\AIHandGestureController\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AI Hand Gesture Controller"; Filename: "{app}\AIHandGestureController.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\AI Hand Gesture Controller"; Filename: "{app}\AIHandGestureController.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AIHandGestureController.exe"; Description: "Launch AI Hand Gesture Controller"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
