# Check what's locking the folder
$folder = "C:\Projects\claude-family-manager-v2"

# Try using handle.exe if available, otherwise just list processes
Write-Host "Checking for processes that might lock: $folder"
Write-Host ""

# Check for common culprits
$suspects = @("devenv", "Code", "node", "claude", "dotnet", "msbuild", "git")
foreach ($proc in $suspects) {
    $found = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "Found: $proc (PID: $($found.Id -join ', '))"
    }
}

Write-Host ""
Write-Host "Try closing VS, VS Code, or any terminals in that folder."
