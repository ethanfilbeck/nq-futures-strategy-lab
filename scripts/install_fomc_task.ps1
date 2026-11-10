# Creates a Windows scheduled task that runs the H8 forward PAPER tracker automatically.
#   Run once, from the repo folder, in a normal (not admin) PowerShell:   .\scripts\install_fomc_task.ps1
#   Remove it later with:   Unregister-ScheduledTask -TaskName "NQ bot - FOMC paper" -Confirm:$false
#
# What the task does:
#   * Every weekday at 12:40 PM (your PC's local time) and whenever you log on, it runs
#       py cli.py fomc-paper --if-due
#     which exits immediately unless today is a Fed entry day (or a paper trade is already open, e.g. after a
#     reboot - then it resumes it).
#   * It can wake the PC from sleep, and the tracker keeps the PC awake while a trade is open.
#   * Output is appended to logs\fomc_paper\task.log.
# PAPER ONLY: the tracker refuses live ports and non-paper accounts. TWS must be running and logged into Paper.

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
New-Item -ItemType Directory -Force "$repo\logs\fomc_paper" | Out-Null

$py = (Get-Command py.exe -ErrorAction Stop).Source
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"`"$py`" cli.py fomc-paper --if-due >> logs\fomc_paper\task.log 2>&1`"" `
    -WorkingDirectory $repo

# 12:40 PM local = 13:40 ET in Central time (20 minutes before the 14:00 ET entry). If your PC is set to Eastern
# time, change -At to 1:40PM.
$daily = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 12:40PM
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 30) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Runs only while you're logged in (no password stored), because TWS also needs your logged-in session.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "NQ bot - FOMC paper" -Action $action -Trigger @($daily, $logon) `
    -Settings $settings -Principal $principal -Force `
    -Description "Forward PAPER tracking of H8 (pre-FOMC drift) on the IB paper account. See docs/FOMC_PAPER.md." | Out-Null

Write-Host "Installed scheduled task 'NQ bot - FOMC paper'."
Write-Host "Test it now (it should say 'no FOMC paper trade due today'):"
Write-Host "  Start-ScheduledTask -TaskName 'NQ bot - FOMC paper'; Start-Sleep 20; Get-Content logs\fomc_paper\task.log -Tail 5"
