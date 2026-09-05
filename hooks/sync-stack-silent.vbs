' Silent launcher for sync-stack.ps1 -- runs the bridge without a console window.
' Used by the Windows scheduled task "ClaudeStackBridge" (logon + every 10 min).
' Keep this file ASCII-only.
Option Explicit
Dim sh, ps1, rc
Set sh = CreateObject("WScript.Shell")
ps1 = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\.claude\hooks\sync-stack.ps1"
rc = sh.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """", 0, True)
WScript.Quit rc
