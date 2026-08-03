[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.4.3
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

; Disable unnecessary wizard pages for silent/quick updates[cite: 5]
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes

; Keep uninstaller registry entry unified[cite: 5]
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName=Loqin
UninstallDisplayIcon={app}\Loqin.exe

[Registry]
; Disables the Windows automatic captive portal browser popup by forcing the value to 0
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet"; ValueType: dword; ValueName: "EnableActiveProbing"; ValueData: 0

[Files]
; The 'external' flag tells Inno Setup to look for the file on the user's drive (in the {tmp} folder) 
; rather than expecting it to be bundled inside the installer during compilation.
Source: "{tmp}\Loqin.exe"; DestDir: "{app}"; Flags: external ignoreversion
Source: "assets\loqin_logo_small.png"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Auto-relaunch Loqin quietly after installation completes[cite: 5]
Filename: "{app}\Loqin.exe"; Description: "{cm:LaunchProgram,Loqin}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

procedure InitializeWizard;
begin
  // Initialize the native Inno Setup download page
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // 1. Terminate running Loqin instance before replacing files[cite: 5]
  Exec('taskkill.exe', '/f /im Loqin.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 2. Download the raw executable directly from GitHub to the {tmp} directory
  DownloadPage.Clear;
  DownloadPage.Add('https://github.com/notaayushsrivastava/Loqin/raw/refs/heads/master/dist/Loqin.exe', 'Loqin.exe', '');
  DownloadPage.Show;
  try
    try
      DownloadPage.Download; 
      Result := ''; // Return empty string to signal success to the installer
    except
      Result := 'Failed to download the update from GitHub: ' + GetExceptionMessage;
    end;
  finally
    DownloadPage.Hide;
  end;
end;