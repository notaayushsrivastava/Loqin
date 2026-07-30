[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.0.0
AppPublisher=Aayush Srivastava
AppPublisherURL=https://github.com/notaayushsrivastava
AppSupportURL=https://github.com/notaayushsrivastava/loqin
DefaultDirName={autopf}\Loqin
DefaultGroupName=Loqin
AllowNoIcons=yes
OutputBaseFilename=Install_Loqin
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; --- UNINSTALLER SETTINGS ---
Uninstallable=yes
UninstallDisplayIcon={app}\Loqin.exe
UninstallDisplayName=Loqin
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch Loqin automatically on Windows startup"; GroupDescription: "Startup Settings:"

[Files]
Source: "dist\Loqin.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "loqin_logo_small.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Loqin"; Filename: "{app}\Loqin.exe"
Name: "{group}\{cm:UninstallProgram,Loqin}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Loqin"; Filename: "{app}\Loqin.exe"; Tasks: desktopicon

[Registry]
; Adds Windows auto-start registry key (automatically removed on uninstall via 'uninsdeletevalue')
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Loqin"; ValueData: """{app}\Loqin.exe"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Loqin.exe"; Description: "{cm:LaunchProgram,Loqin}"; Flags: nowait postinstall skipifsilent

; --- PASCAL SCRIPTING FOR UNINSTALL CLEANUP ---
[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
begin
  // Clean up user AppData folder during uninstallation
  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{userappdata}\Loqin');
    if DirExists(ConfigDir) then
      DelTree(ConfigDir, True, True, True);
  end;
end;