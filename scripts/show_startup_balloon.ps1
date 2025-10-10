# Show Startup Balloon Notification
# Displays Windows balloon notification with Claude Family context summary
# Auto-disappears after 10 seconds

param(
    [string]$ContextFile = "$PSScriptRoot\..\logs\startup_context_claude-desktop-001_*.txt"
)

# Find the most recent startup context file
$LatestContext = Get-ChildItem -Path (Split-Path $ContextFile) -Filter (Split-Path $ContextFile -Leaf) |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $LatestContext) {
    Write-Host "No startup context file found"
    exit 1
}

# Read first few lines of context
$ContextLines = Get-Content $LatestContext.FullName -Head 15 | Out-String

# Create notification
Add-Type -AssemblyName System.Windows.Forms

$Notification = New-Object System.Windows.Forms.NotifyIcon
$Notification.Icon = [System.Drawing.SystemIcons]::Information
$Notification.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$Notification.BalloonTipTitle = "Claude Family - Context Loaded ✅"
$Notification.BalloonTipText = @"
🤖 Identity: claude-desktop-001
📚 Knowledge: Loaded
📋 Sessions: Ready

Context restored successfully!
Click for full details.
"@

$Notification.Visible = $true
$Notification.ShowBalloonTip(10000)  # 10 seconds

# Keep script running for balloon to display
Start-Sleep -Seconds 10

# Cleanup
$Notification.Dispose()

Write-Host "Balloon notification shown successfully"
