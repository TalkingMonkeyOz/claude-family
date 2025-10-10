# Update All Desktop Shortcuts to New C:\Projects Location

$WshShell = New-Object -ComObject WScript.Shell

# Find Desktop folder
$DesktopPath = [Environment]::GetFolderPath("Desktop")
if ([string]::IsNullOrEmpty($DesktopPath) -or -not (Test-Path $DesktopPath)) {
    $DesktopPath = "$env:USERPROFILE\Desktop"
}
if ([string]::IsNullOrEmpty($DesktopPath) -or -not (Test-Path $DesktopPath)) {
    $DesktopPath = "$env:USERPROFILE\OneDrive\Desktop"
}

Write-Host "Updating shortcuts at: $DesktopPath"

# Update Claude Family Startup shortcut
$Shortcut1 = $WshShell.CreateShortcut("$DesktopPath\Claude Family Startup.lnk")
$Shortcut1.TargetPath = "C:\Projects\claude-family\STARTUP.bat"
$Shortcut1.WorkingDirectory = "C:\Projects\claude-family"
$Shortcut1.Description = "Sync Claude Family memory from PostgreSQL to MCP"
$Shortcut1.Save()
Write-Host "✅ Updated: Claude Family Startup.lnk"

# Update Claude Code Console shortcut
$Shortcut2 = $WshShell.CreateShortcut("$DesktopPath\Claude Code Console.lnk")
$Shortcut2.TargetPath = "C:\Projects\claude-family\Launch-Claude-Code-Console.bat"
$Shortcut2.WorkingDirectory = "$env:USERPROFILE"
$Shortcut2.Description = "Claude Code Console v2.0.13 - Terminal & CLI Specialist"
$Shortcut2.IconLocation = "C:\WINDOWS\System32\cmd.exe,0"
$Shortcut2.Save()
Write-Host "✅ Updated: Claude Code Console.lnk"

Write-Host ""
Write-Host "All shortcuts updated to C:\Projects\claude-family\"
