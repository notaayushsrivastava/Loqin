[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.1.2
AppPublisher=Aayush Srivastava
AppCopyright=Copyright (C) 2026 Aayush Srivastava. All rights reserved.
DefaultDirName={autopf}\Loqin
DefaultGroupName=Loqin
OutputBaseFilename=Install_Loqin_Update
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; --- BRANDING & LOGOS ---
SetupIconFile=assets/loqin_icon.ico
WizardImageFile=assets/wizard_banner.bmp
WizardSmallImageFile=assets/wizard_logo.bmp

; Disable unnecessary wizard pages for silent/quick updates
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes

; Keep uninstaller registry entry unified
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName=Loqin
UninstallDisplayIcon={app}\Loqin.exe

[Files]
; Overwrites the core executable with the updated build
Source: "dist\Loqin.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\loqin_logo_small.png"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Auto-relaunch Loqin quietly after installation completes
Filename: "{app}\Loqin.exe"; Description: "{cm:LaunchProgram,Loqin}"; Flags: nowait postinstall skipifsilent

[Code]
// Terminate running Loqin instance before replacing files
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im Loqin.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;