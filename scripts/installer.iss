; Build through build_installer.py; the desktop package supplies the single version.
#ifndef AppVersion
  #error AppVersion must be provided by build_installer.py
#endif
#ifndef SourceRoot
  #error SourceRoot must be provided by build_installer.py
#endif
#define AppExe "Mystery-" + AppVersion + ".exe"

[Setup]
AppId={code:GetApplicationId}
UsePreviousLanguage=no
AppName=Mystery
AppVersion={#AppVersion}
AppVerName=Mystery {#AppVersion}
AppPublisher=Mystery
DefaultDirName={localappdata}\Programs\Mystery
DefaultGroupName=Mystery
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
WizardStyle=modern dynamic
OutputDir={#SourceRoot}\output\release
OutputBaseFilename=Mystery-{#AppVersion}-setup
SetupIconFile={#SourceRoot}\.cache\desktop-build\Mystery.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName=Mystery {#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription=Mystery {#AppVersion} Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
SetupLogging=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
Type: files; Name: "{app}\Mystery-*.exe"

[Files]
Source: "{#SourceRoot}\output\release\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\output\release\使用说明.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\output\release\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\output\release\sources\Mystery-{#AppVersion}-source.zip"; DestDir: "{app}\sources"; Flags: ignoreversion
Source: "{#SourceRoot}\output\release\sources\pyswisseph-*.tar.gz"; DestDir: "{app}\sources"; Flags: ignoreversion
Source: "{#SourceRoot}\output\release\sources\source-manifest.json"; DestDir: "{app}\sources"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Mystery"; Filename: "{app}\{#AppExe}"; Check: not IsVerificationInstall
Name: "{autodesktop}\Mystery"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; Check: not IsVerificationInstall

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,Mystery}"; Flags: nowait postinstall skipifsilent

[Code]
function IsVerificationInstall: Boolean;
begin
  Result := ExpandConstant('{param:VERIFYINSTALL|0}') = '1';
end;

function GetApplicationId(Param: String): String;
begin
  Result := '{A596F34B-C8C2-42F4-870D-AFBE7432BFA5}';
  if IsVerificationInstall then
    Result := Result + '-Verification';
end;
