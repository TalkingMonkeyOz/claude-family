# Create Desktop Shortcut for Claude Code Console

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
    Write-Host "Error: Could not find Desktop folder. Tried:"
    Write-Host "  - [Environment]::GetFolderPath('Desktop')"
    Write-Host "  - $env:USERPROFILE\Desktop"
    Write-Host "  - $env:USERPROFILE\OneDrive\Desktop"
    exit 1
}

Write-Host "Creating shortcut at: $DesktopPath"

$ShortcutPath = Join-Path $DesktopPath "Claude Code Console.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "C:\Users\johnd\AppData\Local\AnthropicClaude\claude.exe"
$Shortcut.Description = "Claude Code Console - Terminal & CLI Specialist"
$Shortcut.WorkingDirectory = "$env:USERPROFILE"
$Shortcut.IconLocation = "C:\Users\johnd\AppData\Local\AnthropicClaude\app.ico"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully at: $ShortcutPath"
