# Setup Windows Task Scheduler for Claude Family Automation
# Creates scheduled tasks for startup and backups

# Requires admin privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[XX] This script requires administrator privileges"
    Write-Host "[>>] Right-click PowerShell and 'Run as Administrator'"
    exit 1
}

$projectRoot = "C:\Projects\claude-family"

Write-Host ""
Write-Host "================================================================"
Write-Host "Claude Family - Windows Task Scheduler Setup"
Write-Host "================================================================"
Write-Host ""

# Task 1: Silent Startup at Boot
Write-Host "[1] Setting up: Claude Family Silent Startup (at boot)"
Write-Host ""

$taskName1 = "Claude Family Startup"
$taskExists1 = Get-ScheduledTask -TaskName $taskName1 -ErrorAction SilentlyContinue

if ($taskExists1) {
    Write-Host "    [!!] Task already exists: $taskName1"
    $response = Read-Host "    Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Unregister-ScheduledTask -TaskName $taskName1 -Confirm:$false
        Write-Host "    [--] Deleted existing task"
    } else {
        Write-Host "    [--] Skipping..."
        $taskExists1 = $null
    }
}

if (-not $taskExists1) {
    $action1 = New-ScheduledTaskAction `
        -Execute "$projectRoot\STARTUP_SILENT.bat" `
        -WorkingDirectory $projectRoot

    $trigger1 = New-ScheduledTaskTrigger -AtLogOn

    $settings1 = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    $principal1 = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $taskName1 `
        -Action $action1 `
        -Trigger $trigger1 `
        -Settings $settings1 `
        -Principal $principal1 `
        -Description "Syncs Claude Family PostgreSQL data to MCP memory at Windows startup" | Out-Null

    Write-Host "    [OK] Created: $taskName1"
    Write-Host "    [OK] Trigger: At user logon"
    Write-Host "    [OK] Action: Run STARTUP_SILENT.bat"
}

Write-Host ""

# Task 2: PostgreSQL Backup (Weekly)
Write-Host "[2] Setting up: PostgreSQL Backup (weekly)"
Write-Host ""

$taskName2 = "Claude Family - PostgreSQL Backup"
$taskExists2 = Get-ScheduledTask -TaskName $taskName2 -ErrorAction SilentlyContinue

if ($taskExists2) {
    Write-Host "    [!!] Task already exists: $taskName2"
    $response = Read-Host "    Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false
        Write-Host "    [--] Deleted existing task"
    } else {
        Write-Host "    [--] Skipping..."
        $taskExists2 = $null
    }
}

if (-not $taskExists2) {
    $action2 = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$projectRoot\scripts\backup_postgres.ps1`"" `
        -WorkingDirectory "$projectRoot\scripts"

    # Weekly on Sunday at 2 AM
    $trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2am

    $settings2 = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)

    $principal2 = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $taskName2 `
        -Action $action2 `
        -Trigger $trigger2 `
        -Settings $settings2 `
        -Principal $principal2 `
        -Description "Weekly backup of ai_company_foundation PostgreSQL database to OneDrive" | Out-Null

    Write-Host "    [OK] Created: $taskName2"
    Write-Host "    [OK] Trigger: Every Sunday at 2:00 AM"
    Write-Host "    [OK] Action: PowerShell backup_postgres.ps1"
    Write-Host "    [OK] Backup location: OneDrive\Documents\Backups\PostgreSQL"
}

Write-Host ""

# Task 3: Monthly Documentation Audit
Write-Host "[3] Setting up: Documentation Audit (monthly)"
Write-Host ""

$taskName3 = "Claude Family - Documentation Audit"
$taskExists3 = Get-ScheduledTask -TaskName $taskName3 -ErrorAction SilentlyContinue

if ($taskExists3) {
    Write-Host "    [!!] Task already exists: $taskName3"
    $response = Read-Host "    Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Unregister-ScheduledTask -TaskName $taskName3 -Confirm:$false
        Write-Host "    [--] Deleted existing task"
    } else {
        Write-Host "    [--] Skipping..."
        $taskExists3 = $null
    }
}

if (-not $taskExists3) {
    $action3 = New-ScheduledTaskAction `
        -Execute "python.exe" `
        -Argument "`"$projectRoot\scripts\audit_docs.py`"" `
        -WorkingDirectory $projectRoot

    # Monthly on the 1st at 9 AM
    $trigger3 = New-ScheduledTaskTrigger -Daily -At 9am
    # TODO: Change to monthly trigger when testing complete

    $settings3 = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

    $principal3 = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $taskName3 `
        -Action $action3 `
        -Trigger $trigger3 `
        -Settings $settings3 `
        -Principal $principal3 `
        -Description "Monthly audit of Claude Family documentation health" | Out-Null

    Write-Host "    [OK] Created: $taskName3"
    Write-Host "    [OK] Trigger: Daily at 9:00 AM (change to monthly after testing)"
    Write-Host "    [OK] Action: python audit_docs.py"
}

Write-Host ""
Write-Host "================================================================"
Write-Host "Setup Complete!"
Write-Host "================================================================"
Write-Host ""
Write-Host "Created Tasks:"
Write-Host "  1. $taskName1 (at logon)"
Write-Host "  2. $taskName2 (weekly, Sunday 2 AM)"
Write-Host "  3. $taskName3 (monthly, 1st @ 9 AM)"
Write-Host ""
Write-Host "To view tasks: Task Scheduler -> Task Scheduler Library"
Write-Host "To test backup now: powershell -File scripts\backup_postgres.ps1"
Write-Host ""
