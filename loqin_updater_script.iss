[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.7.0
AppPublisher=Aayush Srivastava
AppCopyright=Copyright (C) 2026 Aayush Srivastava. All rights reserved.
DefaultDirName={autopf}\Loqin
DefaultGroupName=Loqin
OutputBaseFilename=Install_Loqin_Update
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; --- EULA CONFIGURATION ---
LicenseFile=eula.txt

; --- BRANDING & LOGOS ---
SetupIconFile=assets/loqin_icon.ico
WizardImageFile=assets/wizard_banner.bmp
WizardSmallImageFile=assets/wizard_logo.bmp

; Disable unnecessary wizard pages for silent/quick updates
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=no

; Keep uninstaller registry entry unified
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

[Code]
var
  DownloadPage: TDownloadWizardPage;
  LicenseLink: TNewStaticText;

// Triggered when the user clicks the custom GPLv3 link
procedure LicenseLinkClick(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://github.com/notaayushsrivastava/Loqin/blob/master/LICENSE', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure InitializeWizard;
begin
  // Custom copyright watermark footer
  WizardForm.BeveledLabel.Caption := ' | Loqin v1.7.0 • © 2026 Aayush Srivastava';
  WizardForm.BeveledLabel.Visible := True;

  // Create the clickable GPLv3 License link
  LicenseLink := TNewStaticText.Create(WizardForm);
  LicenseLink.Parent := WizardForm;
  LicenseLink.Caption := 'View GPLv3 License';
  LicenseLink.Cursor := crHand;
  LicenseLink.Font.Color := clBlue;
  LicenseLink.Font.Style := [fsUnderline];
  LicenseLink.Left := 20;
  // Align it vertically with the Cancel/Next buttons at the bottom
  LicenseLink.Top := WizardForm.CancelButton.Top + 6;
  LicenseLink.OnClick := @LicenseLinkClick;

  // Shift the BeveledLabel over so it sits next to the new link
  WizardForm.BeveledLabel.Left := LicenseLink.Left + LicenseLink.Width + 5; 
  WizardForm.BeveledLabel.Top := LicenseLink.Top;

  // Initialize the native Inno Setup download page
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);

  // Customize the standard completion page so the updater ends with a clear hand-off.
  WizardForm.FinishedHeadingLabel.Caption := 'Loqin has been installed successfully!';
  WizardForm.FinishedLabel.Caption :=
    'The update has been successfully installed.' + #13#10 + #13#10 +
    'Please run Loqin normally now from your Start Menu or desktop shortcut.'
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // 1. Terminate running Loqin instance before replacing files
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