# Setup Windows Task Scheduler for task_worker daemon
# Creates at-logon scheduled task for autonomous task execution
# F224 BT705 — Windows Task Scheduler setup + watchdog respawn

# Does not require admin privileges (runs as current user, no elevation)
# Idempotent: checks if task exists, updates if needed, creates if absent

$projectRoot = "C:\Projects\claude-family"
$projectName = "claude-family"

Write-Host ""
Write-Host "================================================================"
Write-Host "Claude Family - Task Worker Scheduler Setup"
Write-Host "================================================================"
Write-Host ""

Write-Host "[*] Setting up: Task Worker daemon (at-logon entry)"
Write-Host ""

$taskName = "ClaudeFamily-TaskWorker"

# Check if task already exists
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "    [!!] Task already exists: $taskName"
    Write-Host "    [--] Updating existing task (idempotent)..."

    # Get current task definition to check if it needs updating
    $currentAction = $taskExists.Actions[0]
    $expectedExe = "pythonw.exe"
    $expectedArgs = "$projectRoot\scripts\task_worker.py $projectName $projectRoot"

    $needsUpdate = $false
    if ($currentAction.Execute -ne $expectedExe) {
        $needsUpdate = $true
    }
    if ($currentAction.Arguments -ne $expectedArgs) {
        $needsUpdate = $true
    }

    if ($needsUpdate) {
        Write-Host "    [--] Detected changes, updating task..."
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null
        $taskExists = $null
    } else {
        Write-Host "    [OK] Task is current, no update needed"
        Write-Host ""
        Write-Host "Verification:"
        Write-Host "  Task Name: $taskName"
        Write-Host "  Trigger: At user logon"
        Write-Host "  Action: pythonw.exe $projectRoot\scripts\task_worker.py"
        Write-Host ""
        Write-Host "To remove: Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
        Write-Host ""
        exit 0
    }
}

# Create the task if it doesn't exist
if (-not $taskExists) {
    Write-Host "    [--] Creating new task..."
    Write-Host ""

    # Define the action: run pythonw.exe (headless Python) with script + args
    $action = New-ScheduledTaskAction `
        -Execute "pythonw.exe" `
        -Argument "$projectRoot\scripts\task_worker.py $projectName $projectRoot" `
        -WorkingDirectory $projectRoot

    # Trigger: at user logon
    $trigger = New-ScheduledTaskTrigger -AtLogOn

    # Settings: allow battery operation, restart on failure (3x with 5min interval), no time limit
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5) `
        -ExecutionTimeLimit ([System.TimeSpan]::Zero)  # PT0S = no limit

    # Principal: current user, interactive logon, limited privileges (no elevation)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    # Register the task — surface errors instead of swallowing with | Out-Null (FB420)
    try {
        $registered = Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description "F224 Local Task Queue worker daemon — auto-start at logon. SessionStart watchdog respawns if dead." `
            -ErrorAction Stop
    } catch {
        Write-Host ""
        Write-Host "    [FAIL] Register-ScheduledTask failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        if ($_.Exception.Message -match 'Access is denied|denied') {
            Write-Host "    Likely cause: this shell does not have rights to register a scheduled task." -ForegroundColor Yellow
            Write-Host "    This commonly happens when the script is invoked from Claude Code's sandboxed pwsh." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "    Fix: re-run from an interactive PowerShell window opened by you, e.g.:" -ForegroundColor Yellow
            Write-Host "      powershell -ExecutionPolicy Bypass -File `"$projectRoot\scripts\setup_task_worker_scheduler.ps1`"" -ForegroundColor Cyan
        }
        Write-Host ""
        exit 1
    }

    # Verify post-condition: task must actually exist now
    $verify = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $verify) {
        Write-Host ""
        Write-Host "    [FAIL] Register-ScheduledTask returned without error but task is not present." -ForegroundColor Red
        Write-Host "    Run: Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }

    Write-Host "    [OK] Created: $taskName"
    Write-Host "    [OK] Trigger: At user logon"
    Write-Host "    [OK] Action: pythonw.exe (headless)"
    Write-Host "    [OK] Arguments: $projectRoot\scripts\task_worker.py $projectName $projectRoot"
    Write-Host "    [OK] Restart policy: 3 attempts, 5-minute intervals"
    Write-Host "    [OK] Battery: Allowed (runs on battery, doesn't stop)"
    Write-Host "    [OK] Privilege: Limited (no elevation required)"
    Write-Host ""
}

Write-Host "================================================================"
Write-Host "Setup Complete!"
Write-Host "================================================================"
Write-Host ""

Write-Host "Task Details:"
Write-Host "  Name: $taskName"
Write-Host "  Trigger: At logon (auto-respawned if dead)"
Write-Host "  Runs as: Current user ($env:USERNAME)"
Write-Host "  Privilege level: Limited (no admin needed)"
Write-Host ""

Write-Host "Verification Commands:"
Write-Host "  Check task: Get-ScheduledTask -TaskName '$taskName'"
Write-Host "  View logs: Get-Content ~/.claude/logs/task-worker-claude-family.log"
Write-Host "  Check PID: Get-Content ~/.claude/task-worker-claude-family.pid"
Write-Host "  Health ping: curl http://127.0.0.1:9901/health  (adjust port if needed)"
Write-Host ""

Write-Host "Removal:"
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
Write-Host ""
