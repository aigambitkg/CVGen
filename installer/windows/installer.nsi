; CVGen Windows Installer Script (NSIS)
; Creates a one-click Windows installer: CVGen-Setup-1.0.0.exe

!include "MUI2.nsh"
!include "FileFunc.nsh"

; General
Name "CVGen"
OutFile "..\..\CVGen-Setup-1.0.0.exe"
InstallDir "$LOCALAPPDATA\CVGen"
RequestExecutionLevel user

; UI
!define MUI_ICON "..\..\desktop\resources\icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "CVGen — Quantum Computing for Every Device"
!define MUI_WELCOMEPAGE_TEXT "This will install CVGen on your computer.$\r$\n$\r$\nNo admin rights required. No Python needed.$\r$\nEverything is included.$\r$\n$\r$\nClick Install to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\CVGen.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CVGen now"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "German"

Section "Install"
    SetOutPath "$INSTDIR"

    ; Copy all files from PyInstaller output
    File /r "..\..\dist\CVGen\*.*"

    ; Create desktop shortcut
    CreateShortCut "$DESKTOP\CVGen.lnk" "$INSTDIR\CVGen.exe" "" "$INSTDIR\CVGen.exe" 0

    ; Create start menu
    CreateDirectory "$SMPROGRAMS\CVGen"
    CreateShortCut "$SMPROGRAMS\CVGen\CVGen.lnk" "$INSTDIR\CVGen.exe"
    CreateShortCut "$SMPROGRAMS\CVGen\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry for Add/Remove Programs
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "DisplayName" "CVGen"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "DisplayIcon" "$INSTDIR\CVGen.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "Publisher" "AI-Gambit"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "DisplayVersion" "1.0.0"

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen" "EstimatedSize" "$0"
SectionEnd

Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\CVGen.lnk"
    RMDir /r "$SMPROGRAMS\CVGen"

    ; Remove registry
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CVGen"
SectionEnd
