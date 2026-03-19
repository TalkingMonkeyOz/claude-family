# Update Desktop Shortcut for Claude Code Console
# Points to the correct launcher batch file

$WshShell = New-Object -ComObject WScript.Shell

# Try to find Desktop folder
$DesktopPath = [Environment]::GetFolderPath("Desktop")

if ([string]::IsNullOrEmpty($DesktopPath) -or -not (Test-Path $DesktopPath)) {
    # Try alternative Desktop location
    $DesktopPath = "$env:USERPROFILE\Desktop"
}

if ([string]::IsNullOrEmpty($DesktopPath) -or -not (Test-Path $DesktopPath)) {
    # Try OneDrive Desktop
    $DesktopPath = "$env:USERPROFILE\OneDrive\Desktop"
}

if (-not (Test-Path $DesktopPath)) {
    Write-Host "Error: Could not find Desktop folder"
    exit 1
}

Write-Host "Updating shortcut at: $DesktopPath"

$ShortcutPath = Join-Path $DesktopPath "Claude Code Console.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\Launch-Claude-Code-Console.bat"
$Shortcut.Description = "Claude Code Console v2.0.13 - Terminal & CLI Specialist"
$Shortcut.WorkingDirectory = "$env:USERPROFILE"
$Shortcut.IconLocation = "C:\WINDOWS\System32\cmd.exe,0"
$Shortcut.Save()

Write-Host "Desktop shortcut updated successfully!"
Write-Host "Location: $ShortcutPath"
Write-Host "Target: Launch-Claude-Code-Console.bat"
