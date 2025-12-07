# PostgreSQL Backup Script for Claude Family
# Backs up ai_company_foundation database to OneDrive

param(
    [string]$BackupDir = "C:\Users\johnd\OneDrive\Documents\Backups\PostgreSQL",
    [int]$KeepBackups = 3,  # Keep 3 weekly backups (~2-3 weeks)
    [int]$MinDaysBetweenBackups = 6  # Don't backup if last one is < 6 days old
)

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$backupFile = Join-Path $BackupDir "ai_company_foundation_$timestamp.backup"
$logFile = Join-Path $BackupDir "backup_log.txt"

# Ensure backup directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "[>>] Created backup directory: $BackupDir"
}

# Log function
function Write-Log {
    param($Message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

Write-Log "=== PostgreSQL Backup Started ==="

# Check if backup is needed (skip if recent backup exists)
$latestBackup = Get-ChildItem -Path $BackupDir -Filter "ai_company_foundation_*.backup" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latestBackup) {
    $daysSinceLastBackup = (New-TimeSpan -Start $latestBackup.LastWriteTime -End (Get-Date)).Days
    if ($daysSinceLastBackup -lt $MinDaysBetweenBackups) {
        Write-Log "[OK] Recent backup exists ($daysSinceLastBackup days old). Skipping."
        Write-Log "[OK] Last backup: $($latestBackup.Name)"
        Write-Host "[OK] Backup skipped - last backup is only $daysSinceLastBackup days old"
        exit 0
    }
    Write-Log "[>>] Last backup is $daysSinceLastBackup days old. Proceeding with new backup."
}

# Check if pg_dump is available
$pgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    # Try version 16
    $pgDump = "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
    if (-not (Test-Path $pgDump)) {
        # Try to find pg_dump in PATH
        $pgDump = (Get-Command pg_dump -ErrorAction SilentlyContinue).Source
        if (-not $pgDump) {
            Write-Log "[XX] pg_dump not found. Install PostgreSQL or add to PATH."
            exit 1
        }
    }
}

Write-Log "[>>] Using pg_dump: $pgDump"

# Set PostgreSQL password from User environment variable (if not already set)
if (-not $env:PGPASSWORD) {
    $env:PGPASSWORD = [System.Environment]::GetEnvironmentVariable('PGPASSWORD', 'User')
    if (-not $env:PGPASSWORD) {
        Write-Log "[XX] PGPASSWORD not set. Please configure it first."
        Write-Host "[XX] Run: [System.Environment]::SetEnvironmentVariable('PGPASSWORD', 'your_password', 'User')"
        exit 1
    }
}

# Run backup
Write-Log "[>>] Backing up database: ai_company_foundation"
Write-Log "[>>] Backup file: $backupFile"

try {
    & $pgDump `
        --host=localhost `
        --port=5432 `
        --username=postgres `
        --format=custom `
        --file=$backupFile `
        --verbose `
        ai_company_foundation 2>&1 | Out-String | Write-Log

    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Log "[OK] Backup completed successfully"
        Write-Log "[OK] Backup size: $([math]::Round($fileSize, 2)) MB"
    } else {
        Write-Log "[XX] Backup failed with exit code: $LASTEXITCODE"
        exit 1
    }
} catch {
    Write-Log "[XX] Backup failed: $_"
    exit 1
}

# Cleanup old backups
Write-Log "[>>] Cleaning up old backups (keeping last $KeepBackups)..."
$backups = Get-ChildItem -Path $BackupDir -Filter "ai_company_foundation_*.backup" |
    Sort-Object LastWriteTime -Descending

if ($backups.Count -gt $KeepBackups) {
    $toDelete = $backups | Select-Object -Skip $KeepBackups
    foreach ($file in $toDelete) {
        Write-Log "[--] Deleting old backup: $($file.Name)"
        Remove-Item $file.FullName -Force
    }
    Write-Log "[OK] Deleted $($toDelete.Count) old backup(s)"
} else {
    Write-Log "[OK] Only $($backups.Count) backup(s) exist, no cleanup needed"
}

Write-Log "=== PostgreSQL Backup Completed ==="
Write-Host ""
Write-Host "[OK] Backup saved to: $backupFile"
Write-Host "[OK] Log file: $logFile"
