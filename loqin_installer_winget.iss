[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.7.0
AppPublisher=Aayush Srivastava
AppCopyright=Copyright (C) 2026 Aayush Srivastava. All rights reserved.
AppPublisherURL=https://github.com/notaayushsrivastava
AppSupportURL=https://github.com/notaayushsrivastava/loqin
DefaultDirName={autopf}\Loqin
DefaultGroupName=Loqin
AllowNoIcons=yes
OutputBaseFilename=Install_Loqin_WinGet
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
LicenseFile=eula.txt
DisableWelcomePage=no
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName=Loqin
UninstallDisplayIcon={app}\Loqin.exe
SetupIconFile=assets/loqin_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch Loqin automatically on Windows startup"; GroupDescription: "Startup Settings:"

[Files]
Source: "dist\Loqin.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\loqin_logo_small.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Loqin"; Filename: "{app}\Loqin.exe"; AppUserModelID: "Loqin"
Name: "{group}\{cm:UninstallProgram,Loqin}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Loqin"; Filename: "{app}\Loqin.exe"; Tasks: desktopicon; AppUserModelID: "Loqin"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Loqin"; ValueData: """{app}\Loqin.exe"""; Tasks: autostart; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet"; ValueType: dword; ValueName: "EnableActiveProbing"; ValueData: 0

[Run]
Filename: "{app}\Loqin.exe"; Description: "{cm:LaunchProgram,Loqin}"; Flags: nowait postinstall skipifsilent

[Code]
// Terminate running Loqin instance before starting setup to prevent file-lock errors
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im Loqin.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// Restore Active Probing and clear AppData on uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Exec('taskkill.exe', '/f /im Loqin.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    RegWriteDWordValue(
      HKEY_LOCAL_MACHINE,
      'SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet',
      'EnableActiveProbing',
      1
    );
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{userappdata}\Loqin');
    if DirExists(ConfigDir) then
      DelTree(ConfigDir, True, True, True);
  end;
end;