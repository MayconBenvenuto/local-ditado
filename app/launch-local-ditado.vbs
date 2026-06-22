' Local Ditado launcher.
' Starts the desktop app only if it is not already running, so clicking the
' desktop shortcut while the app sits in the tray does NOT spawn a second
' instance (and a second 1.5 GB sidecar). If already running, it does nothing.
'
' The path to the built executable is filled in by the setup step; if you move
' the build, update EXE_PATH below.

Option Explicit

Const EXE_NAME = "local-ditado-app.exe"
' Absolute path to the release build produced by `npm run build`.
Dim EXE_PATH
EXE_PATH = "C:\Users\benve\OneDrive\Documentos\scripts\projetos freelas\local-ditado\app\src-tauri\target\release\local-ditado-app.exe"

Dim shell, fso
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

If Not fso.FileExists(EXE_PATH) Then
    MsgBox "Local Ditado nao encontrado em:" & vbCrLf & EXE_PATH & vbCrLf & _
           "Recompile o app (npm run build) ou ajuste o atalho.", _
           vbExclamation, "Local Ditado"
    WScript.Quit 1
End If

' Is the process already running?
Dim wmi, procs, running
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery( _
    "SELECT ProcessId FROM Win32_Process WHERE Name = '" & EXE_NAME & "'")
running = (procs.Count > 0)

If running Then
    ' Already running (likely minimized to tray). Do nothing — use the tray
    ' icon's "Abrir" to bring the window back.
    WScript.Quit 0
End If

' Not running: start it (0 = hidden console wrapper; the app shows its own window).
shell.Run """" & EXE_PATH & """", 1, False
WScript.Quit 0
