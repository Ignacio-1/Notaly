[Setup]
AppName=Gestor Educativo Profesional
AppVersion=1.0
AppPublisher=Ignacio Olmedo
DefaultDirName={autopf}\Gestor Educativo Profesional
DefaultGroupName=Gestor Educativo Profesional
OutputDir=Output
OutputBaseFilename=Instalar_Promediador
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupIconFile=app_icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\GestorNotasEducativo.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Gestor Educativo Profesional"; Filename: "{app}\GestorNotasEducativo.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Gestor Educativo Profesional"; Filename: "{app}\GestorNotasEducativo.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\GestorNotasEducativo.exe"; Description: "{cm:LaunchProgram,Gestor Educativo Profesional}"; Flags: nowait postinstall skipifsilent
