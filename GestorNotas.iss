[Setup]
AppName=Notaly
AppVersion=1.0
AppPublisher=Ignacio Olmedo
DefaultDirName={autopf}\Notaly
DefaultGroupName=Notaly
OutputDir=Output
OutputBaseFilename=Instalar_Notaly
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupIconFile=app_icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Notaly.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Notaly"; Filename: "{app}\Notaly.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Notaly"; Filename: "{app}\Notaly.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Notaly.exe"; Description: "{cm:LaunchProgram,Notaly}"; Flags: nowait postinstall skipifsilent
