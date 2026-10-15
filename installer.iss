[Setup]
AppName=AltunLink
AppVersion=1.0.0
AppPublisher=Altun
DefaultDirName={autopf}\AltunLink
DefaultGroupName=AltunLink
OutputDir=Output
OutputBaseFilename=AltunLink-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\AltunLink.exe
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"

[Files]
Source: "dist\AltunLink.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AltunLink"; Filename: "{app}\AltunLink.exe"
Name: "{autodesktop}\AltunLink"; Filename: "{app}\AltunLink.exe"; Tasks: desktopicon

[Run]
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""AltunLink"" dir=in action=allow program=""{app}\AltunLink.exe"" profile=private"; Flags: runhidden
Filename: "{app}\AltunLink.exe"; Description: "AltunLink'i başlat"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""AltunLink"""; Flags: runhidden
