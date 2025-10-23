# PostgreSQL Backup Script for Claude Family
# Backs up ai_company_foundation database to OneDrive

param(
    [string]$BackupDir = "C:\Users\johnd\OneDrive\Documents\Backups\PostgreSQL",
    [int]$KeepBackups = 10
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

# Set PostgreSQL password (from environment or prompt)
$env:PGPASSWORD = "password"  # TODO: Use Windows Credential Manager or .pgpass file

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
