#define AppName "Viabilidad espermática"
#define AppVersion "1.0.0"
#define AppExeName "ViabilidadEspermatica.exe"

[Setup]
AppId={{A8D901A4-6BE6-4AF8-83A6-9D204B0E264C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Aplicación de evaluación espermática
DefaultDirName={localappdata}\Programs\ViabilidadEspermatica
DefaultGroupName=Viabilidad espermática
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=Output
OutputBaseFilename=Instalador_ViabilidadEspermatica
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos adicionales:"; Flags: unchecked

[Files]
Source: "dist\ViabilidadEspermatica\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Viabilidad espermática"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Viabilidad espermática"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; Flags: postinstall nowait skipifsilent
