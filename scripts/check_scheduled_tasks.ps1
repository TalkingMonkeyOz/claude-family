# Check for Claude Family related scheduled tasks
$tasks = Get-ScheduledTask | Where-Object {
    $_.TaskName -match 'claude|postgres|backup|audit|family'
}

if ($tasks) {
    Write-Host "Found scheduled tasks:" -ForegroundColor Green
    $tasks | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize
} else {
    Write-Host "No Claude Family related scheduled tasks found" -ForegroundColor Yellow
}

Write-Host "`nAll scheduled tasks (first 20):" -ForegroundColor Cyan
Get-ScheduledTask | Select-Object TaskName, State -First 20 | Format-Table -AutoSize
