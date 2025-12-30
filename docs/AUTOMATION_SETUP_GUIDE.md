# Automation Setup Guide

**Created**: 2025-10-23
**Purpose**: Step-by-step guide to set up all automation

---

## Prerequisites

1. ✅ PostgreSQL 18 installed (C:\Program Files\PostgreSQL\18\)
2. ✅ Python 3.13+ with scripts working
3. ⏳ Administrator access for Windows Task Scheduler
4. ⏳ PostgreSQL password configured

---

## Step 1: Configure PostgreSQL Password

### Option A: Environment Variable (Recommended)

```powershell
# Set environment variable (current session)
$env:PGPASSWORD = "your_postgres_password"

# Set permanently (system-wide)
[System.Environment]::SetEnvironmentVariable("PGPASSWORD", "your_postgres_password", "User")
```

### Option B: .pgpass File (Unix-style)

Create `C:\Users\johnd\.pgpass` (or `%APPDATA%\postgresql\pgpass.conf` on Windows):
```
localhost:5432:ai_company_foundation:postgres:your_password
```

Set file permissions (PowerShell):
```powershell
icacls "$env:APPDATA\postgresql\pgpass.conf" /inheritance:r /grant:r "$env:USERNAME:(R)"
```

### Option C: Update Script Directly (Least Secure)

Edit `scripts/backup_postgres.ps1` line 46:
```powershell
$env:PGPASSWORD = "your_actual_password"
```

---

## Step 2: Test PostgreSQL Backup

```powershell
# Test backup manually
powershell -ExecutionPolicy Bypass -File C:\Projects\claude-family\scripts\backup_postgres.ps1

# Check backup created
ls C:\Users\johnd\OneDrive\Documents\Backups\PostgreSQL\
```

**Expected output:**
```
2025-10-23 20:58:10 - === PostgreSQL Backup Started ===
2025-10-23 20:58:10 - [>>] Using pg_dump: C:\Program Files\PostgreSQL\18\bin\pg_dump.exe
2025-10-23 20:58:15 - [OK] Backup completed successfully
2025-10-23 20:58:15 - [OK] Backup size: 12.45 MB
2025-10-23 20:58:15 - [OK] Only 1 backup(s) exist, no cleanup needed
2025-10-23 20:58:15 - === PostgreSQL Backup Completed ===

[OK] Backup saved to: C:\Users\johnd\OneDrive\Documents\Backups\PostgreSQL\ai_company_foundation_2025-10-23_205815.backup
```

---

## Step 3: Install Windows Task Scheduler Tasks

**Requires Administrator**

```powershell
# Right-click PowerShell → "Run as Administrator"
cd C:\Projects\claude-family
powershell -ExecutionPolicy Bypass -File scripts\setup_scheduled_tasks.ps1
```

**Creates 3 tasks:**

### Task 1: Claude Family Startup
- **Trigger**: At user logon
- **Action**: Runs STARTUP_SILENT.bat
- **Purpose**: Syncs PostgreSQL → MCP memory at Windows boot

### Task 2: PostgreSQL Backup
- **Trigger**: Every Sunday at 2:00 AM
- **Action**: Runs backup_postgres.ps1
- **Purpose**: Weekly database backups to OneDrive

### Task 3: Documentation Audit
- **Trigger**: Monthly on 1st at 9:00 AM
- **Action**: Runs audit_docs.py in claude-family
- **Purpose**: Monthly doc health check

---

## Step 4: Verify Tasks Installed

```powershell
# Check if tasks exist
Get-ScheduledTask | Where-Object {$_.TaskName -like '*Claude Family*'}
```

**Expected output:**
```
TaskName                    State
--------                    -----
Claude Family Startup       Ready
Claude Family - PostgreSQL Backup  Ready
Claude Family - Documentation Audit  Ready
```

---

## Step 5: Test Task Execution

### Test Startup Task
```powershell
# Manually run startup task
Start-ScheduledTask -TaskName "Claude Family Startup"

# Check output
cat C:\Projects\claude-family\scripts\MCP_SYNC_INSTRUCTIONS.txt
```

### Test Backup Task
```powershell
# Manually run backup task
Start-ScheduledTask -TaskName "Claude Family - PostgreSQL Backup"

# Check backup created
ls C:\Users\johnd\OneDrive\Documents\Backups\PostgreSQL\ | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

### Test Documentation Audit Task
```powershell
# Manually run audit task (will fail if not in correct directory)
# Better to test from command line:
cd C:\Projects\claude-family
python scripts\audit_docs.py
```

---

## Step 6: Verify All Projects Initialized

```bash
# Check each project has .docs-manifest.json
ls C:/Projects/claude-family/.docs-manifest.json
ls C:/Projects/nimbus-user-loader/.docs-manifest.json
ls C:/Projects/ATO-tax-agent/.docs-manifest.json
ls C:/Projects/claude-pm/.docs-manifest.json

# Run audit on each
cd C:/Projects/claude-family && python scripts/audit_docs.py
cd C:/Projects/nimbus-user-loader && python ../claude-family/scripts/audit_docs.py
cd C:/Projects/ATO-tax-agent && python ../claude-family/scripts/audit_docs.py
cd C:/Projects/claude-pm && python ../claude-family/scripts/audit_docs.py
```

---

## Current Status (2025-10-23)

### ✅ Completed

**claude-family:**
- ✅ .docs-manifest.json created
- ✅ Git pre-commit hook installed
- ✅ 33 files tracked, 0 archive candidates
- ✅ CLAUDE.md: 95/250 lines

**nimbus-user-loader:**
- ✅ .docs-manifest.json created
- ✅ Git pre-commit hook installed
- ✅ 39 files tracked, 5 archive candidates (large files)
- ✅ CLAUDE.md: 196/250 lines

**ATO-tax-agent:**
- ✅ .docs-manifest.json created
- ⚠️ Not a git repo (hook not installed)
- ✅ 15 files tracked, 4 archive candidates
- ✅ CLAUDE.md: 80/250 lines

**claude-pm:**
- ✅ .docs-manifest.json created
- ✅ Git pre-commit hook installed
- ✅ 23 files tracked, 6 archive candidates
- ❌ CLAUDE.md: 301/250 lines (OVER LIMIT!)

### ⏳ Pending

- ⏳ PostgreSQL password configuration
- ⏳ Windows Task Scheduler installation (requires admin)
- ⏳ Test backup script execution
- ⏳ Fix claude-pm CLAUDE.md (trim 51 lines)

---

## Troubleshooting

### PowerShell Execution Policy Error

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### PostgreSQL Connection Failed

Check PostgreSQL is running:
```powershell
Get-Service -Name postgresql*
```

Start if stopped:
```powershell
Start-Service postgresql-x64-18
```

### Backup Directory Permission Denied

OneDrive may need to sync first. Check:
```powershell
Test-Path "C:\Users\johnd\OneDrive\Documents\"
```

### Task Scheduler Access Denied

Must run PowerShell as Administrator:
- Right-click PowerShell
- Select "Run as Administrator"

---

## Next Steps

1. Configure PostgreSQL password (choose method above)
2. Test backup script manually
3. Run setup_scheduled_tasks.ps1 as administrator
4. Verify all 3 tasks created
5. Test each task manually
6. Fix claude-pm CLAUDE.md (over limit)

---

## Maintenance

### Weekly
- Verify backup ran successfully (check logs)
- Review backup size/age

### Monthly
- Run documentation audits on all projects
- Archive large/old files as recommended
- Update manifest line counts

### Quarterly
- Review task execution history
- Verify OneDrive backup sync
- Test database restore procedure

---

**Last Updated**: 2025-10-23
**Status**: Ready for admin setup
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/AUTOMATION_SETUP_GUIDE.md
