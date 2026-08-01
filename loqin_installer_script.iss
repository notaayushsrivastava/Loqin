[Setup]
AppId={{A2B3C4D5-1234-5678-90AB-CDEF12345678}
AppName=Loqin
AppVersion=1.1.2
AppPublisher=Aayush Srivastava
AppCopyright=Copyright (C) 2026 Aayush Srivastava. All rights reserved.
AppPublisherURL=https://github.com/notaayushsrivastava
AppSupportURL=https://github.com/notaayushsrivastava/loqin
DefaultDirName={autopf}\Loqin
DefaultGroupName=Loqin
AllowNoIcons=yes
OutputBaseFilename=Install_Loqin
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; --- FORCE WELCOME PAGE TO SHOW ---
DisableWelcomePage=no

; --- CONTROL PANEL / UNINSTALLER REGISTRY SETTINGS ---
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName=Loqin
UninstallDisplayIcon={app}\Loqin.exe

; --- BRANDING & LOGOS ---
SetupIconFile=assets/loqin_icon.ico
WizardImageFile=assets/wizard_banner.bmp
WizardSmallImageFile=assets/wizard_logo.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; --- CUSTOM WELCOME PAGE TEXT ---
[Messages]
WelcomeLabel1=Welcome to the Loqin Setup Wizard
WelcomeLabel2=This wizard will guide you through the installation of Loqin.%n%nLoqin is a background utility designed to automatically monitor and authenticate your captive portal network connections without manual intervention.%n%nCopyright (C) 2026 Aayush Srivastava. All rights reserved.%n%nClick Next to continue, or Cancel to exit Setup.

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
; Adds Windows auto-start registry key (automatically removed on uninstall via 'uninsdeletevalue')
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Loqin"; ValueData: """{app}\Loqin.exe"""; Tasks: autostart; Flags: uninsdeletevalue

; Disables the Windows automatic captive portal browser popup
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet"; ValueType: dword; ValueName: "EnableActiveProbing"; ValueData: 0; Flags: createvalueifdoesntexist

[Run]
Filename: "{app}\Loqin.exe"; Description: "{cm:LaunchProgram,Loqin}"; Flags: nowait postinstall skipifsilent

; --- PASCAL SCRIPTING FOR CUSTOM UI, PROCESS MANAGEMENT & CONFIG GENERATION ---
[Code]
var
  UserCredentialsPage: TInputQueryWizardPage;
  ShowPasswordCheckBox: TCheckBox;

procedure CustomizeHorizontalBanner();
var
  BannerHeight: Integer;
begin
  // Increase overall wizard window height slightly to prevent any vertical cramping
  WizardForm.ClientHeight := WizardForm.ClientHeight + 35;
  WizardForm.ClientWidth := WizardForm.ClientWidth + 20;

  // Dynamically calculate banner height with a slightly expanded proportion
  BannerHeight := (WizardForm.WelcomePage.Width * 420) div 1000;

  // --- WELCOME PAGE FORMATTING ---
  WizardForm.WizardBitmapImage.SetBounds(0, 0, WizardForm.WelcomePage.Width, BannerHeight);
  WizardForm.WizardBitmapImage.Stretch := True;

  WizardForm.WelcomeLabel1.SetBounds(20, BannerHeight + 18, WizardForm.WelcomePage.Width - 40, 50);
  WizardForm.WelcomeLabel2.SetBounds(
    20, 
    BannerHeight + 75, 
    WizardForm.WelcomePage.Width - 40, 
    WizardForm.WelcomePage.Height - (BannerHeight + 75)
  );

  // --- FINISHED PAGE FORMATTING ---
  WizardForm.WizardBitmapImage2.SetBounds(0, 0, WizardForm.FinishedPage.Width, BannerHeight);
  WizardForm.WizardBitmapImage2.Stretch := True;

  WizardForm.FinishedHeadingLabel.SetBounds(20, BannerHeight + 18, WizardForm.FinishedPage.Width - 40, 50);
  WizardForm.FinishedLabel.SetBounds(
    20, 
    BannerHeight + 75, 
    WizardForm.FinishedPage.Width - 40, 
    WizardForm.FinishedLabel.Height - (BannerHeight + 75)
  );
end;

// Terminate running Loqin instance before starting setup
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im Loqin.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// Safely force Registration Number to uppercase as the user types
procedure RegNoEditOnChange(Sender: TObject);
var
  LEdit: TEdit;
  SelStart: Integer;
begin
  if Sender is TEdit then
  begin
    LEdit := Sender as TEdit;
    SelStart := LEdit.SelStart;
    LEdit.Text := Uppercase(LEdit.Text);
    LEdit.SelStart := SelStart;
  end;
end;

// Toggle Password Masking
procedure ShowPasswordOnClick(Sender: TObject);
begin
  if ShowPasswordCheckBox.Checked then
    UserCredentialsPage.Edits[1].Password := False
  else
    UserCredentialsPage.Edits[1].Password := True;
end;

procedure InitializeWizard();
begin
  // Apply symmetrical banner layout and expand window height
  CustomizeHorizontalBanner();

  // Custom copyright watermark footer
  WizardForm.BeveledLabel.Caption := ' Loqin v1.1.0 • © 2026 Aayush Srivastava';
  WizardForm.BeveledLabel.Visible := True;

  // Credentials input page setup
  UserCredentialsPage := CreateInputQueryPage(
    wpSelectDir,
    'Hostel Network Credentials',
    'Enter your Login Information',
    'Please enter your Registration Number and Password. Loqin will use these details to automatically authenticate your connection.'
  );

  UserCredentialsPage.Add('Registration Number / Username:', False);
  UserCredentialsPage.Add('Password:', True);

  // Attach safe uppercase handler
  UserCredentialsPage.Edits[0].OnChange := @RegNoEditOnChange;

  // Setup Show Password Checkbox with extra vertical spacing
  ShowPasswordCheckBox := TCheckBox.Create(UserCredentialsPage);
  ShowPasswordCheckBox.Parent := UserCredentialsPage.Surface;
  ShowPasswordCheckBox.Caption := 'Show Password';
  ShowPasswordCheckBox.Left := UserCredentialsPage.Edits[1].Left;
  ShowPasswordCheckBox.Top := UserCredentialsPage.Edits[1].Top + UserCredentialsPage.Edits[1].Height + 12;
  ShowPasswordCheckBox.Width := UserCredentialsPage.Edits[1].Width;
  ShowPasswordCheckBox.OnClick := @ShowPasswordOnClick;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = UserCredentialsPage.ID then
  begin
    if (Trim(UserCredentialsPage.Values[0]) = '') or (Trim(UserCredentialsPage.Values[1]) = '') then
    begin
      MsgBox('Registration Number and Password cannot be empty.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath, ConfigDir, JsonContent, Username, Password: String;
begin
  if CurStep = ssPostInstall then
  begin
    Username := Uppercase(Trim(UserCredentialsPage.Values[0]));
    Password := UserCredentialsPage.Values[1];

    ConfigDir := ExpandConstant('{userappdata}\Loqin');
    if not DirExists(ConfigDir) then
      ForceDirectories(ConfigDir);

    ConfigPath := ConfigDir + '\Loqin_config.json';

    StringChangeEx(Username, '\', '\\', True);
    StringChangeEx(Username, '"', '\"', True);
    StringChangeEx(Password, '\', '\\', True);
    StringChangeEx(Password, '"', '\"', True);

    JsonContent := '{' + #13#10 +
                   '  "username": "' + Username + '",' + #13#10 +
                   '  "password": "' + Password + '",' + #13#10 +
                   '  "interval": 10,' + #13#10 +
                   '  "auto_connect": true' + #13#10 +
                   '}';

    SaveStringToFile(ConfigPath, JsonContent, False);
  end;
end;

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