# OCI ARM Instance Retry Script
# Retries launching a VM.Standard.A1.Flex instance every 60 seconds until capacity is available

$CompartmentId = "ocid1.tenancy.oc1..aaaaaaaaq66c2kxwcqcb747nghth75fsoxbqwsoqv3i2l3ovorxgjcfvwqea"
$AvailabilityDomain = "AFcd:AP-MELBOURNE-1-AD-1"
$SubnetId = "ocid1.subnet.oc1.ap-melbourne-1.aaaaaaaayy3qb77k5wj5cv4l6mztxwtblh2qsenpu3hb6p4dljahnxjhnc2a"
$ImageId = "ocid1.image.oc1.ap-melbourne-1.aaaaaaaae5qwh6tn4nhgkb6nm32tzbieqnv773k5diy2g66lbf62agscisoq"
$Shape = "VM.Standard.A1.Flex"
$DisplayName = "ubuntu-arm-server"
$Ocpus = 4
$MemoryGB = 24
$BootVolumeSizeGB = 200
$RetryIntervalSeconds = 60
$CliTimeoutSeconds = 120

# Generate SSH key pair if not present
$SshKeyPath = "$env:USERPROFILE\.ssh\oci_arm_key"
if (-not (Test-Path "$SshKeyPath.pub")) {
    Write-Host "[*] Generating SSH key pair at $SshKeyPath" -ForegroundColor Cyan
    ssh-keygen -t ed25519 -f $SshKeyPath -N '""' -C "oci-arm-instance"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] SSH key generation failed." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  OCI ARM Instance Retry Launcher" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Shape:    $Shape ($Ocpus OCPU, ${MemoryGB}GB RAM)" -ForegroundColor White
Write-Host "Image:    Ubuntu 24.04 Minimal aarch64" -ForegroundColor White
Write-Host "Boot:     ${BootVolumeSizeGB}GB" -ForegroundColor White
Write-Host "AD:       $AvailabilityDomain" -ForegroundColor White
Write-Host "SSH Key:  $SshKeyPath" -ForegroundColor White
Write-Host "Retry:    Every ${RetryIntervalSeconds}s (CLI timeout: ${CliTimeoutSeconds}s)" -ForegroundColor White
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

# Write shape config to temp file (avoids PowerShell JSON escaping issues with OCI CLI)
$ShapeConfigFile = [System.IO.Path]::GetTempFileName()
"{`"ocpus`":$Ocpus,`"memoryInGBs`":$MemoryGB}" | Set-Content -Path $ShapeConfigFile -NoNewline

# Temp files for capturing OCI CLI output
$StdoutFile = [System.IO.Path]::GetTempFileName()
$StderrFile = [System.IO.Path]::GetTempFileName()

$attempt = 0

try {
    while ($true) {
        $attempt++
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "[$timestamp] Attempt #$attempt ..." -ForegroundColor Cyan -NoNewline

        # Use cmd /c with timeout to avoid hangs from OCI CLI endpoint issues
        $cliCmd = "oci compute instance launch --compartment-id $CompartmentId --availability-domain `"$AvailabilityDomain`" --subnet-id $SubnetId --image-id $ImageId --shape $Shape --shape-config file://$ShapeConfigFile --boot-volume-size-in-gbs $BootVolumeSizeGB --display-name $DisplayName --ssh-authorized-keys-file `"$SshKeyPath.pub`" --assign-public-ip true"

        # Clear previous output files
        "" | Set-Content $StdoutFile -NoNewline
        "" | Set-Content $StderrFile -NoNewline

        $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $cliCmd >$StdoutFile 2>$StderrFile" -NoNewWindow -PassThru
        $exited = $process.WaitForExit($CliTimeoutSeconds * 1000)

        if (-not $exited) {
            $process | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host " CLI timed out (${CliTimeoutSeconds}s). Retrying..." -ForegroundColor Yellow
            Start-Sleep -Seconds $RetryIntervalSeconds
            continue
        }

        $stdout = if (Test-Path $StdoutFile) { Get-Content $StdoutFile -Raw } else { "" }
        $stderr = if (Test-Path $StderrFile) { Get-Content $StderrFile -Raw } else { "" }

        if ($process.ExitCode -eq 0 -and $stdout) {
            Write-Host " LAUNCHED!" -ForegroundColor Green
            Write-Host ""

            # Parse instance ID from response
            try {
                $instanceData = $stdout | ConvertFrom-Json
                $instanceId = $instanceData.data.id
                $instanceState = $instanceData.data.'lifecycle-state'
                Write-Host "Instance ID: $instanceId" -ForegroundColor Cyan
                Write-Host "State:       $instanceState" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "Waiting for RUNNING state..." -ForegroundColor Cyan

                $maxWait = 300
                $waited = 0
                while ($waited -lt $maxWait) {
                    Start-Sleep -Seconds 15
                    $waited += 15
                    cmd /c "oci compute instance get --instance-id $instanceId --output json >$StdoutFile 2>$StderrFile"
                    $statusJson = Get-Content $StdoutFile -Raw | ConvertFrom-Json
                    $state = $statusJson.data.'lifecycle-state'
                    Write-Host "  [${waited}s] State: $state" -ForegroundColor Cyan
                    if ($state -eq "RUNNING") { break }
                    if ($state -eq "TERMINATED" -or $state -eq "TERMINATING") {
                        Write-Host "  Instance terminated unexpectedly." -ForegroundColor Red
                        break
                    }
                }

                if ($state -eq "RUNNING") {
                    # Get public IP
                    $publicIp = $null
                    cmd /c "oci compute vnic-attachment list --compartment-id $CompartmentId --instance-id $instanceId --output json >$StdoutFile 2>$StderrFile"
                    $vnics = Get-Content $StdoutFile -Raw | ConvertFrom-Json
                    $vnicId = $vnics.data[0].'vnic-id'

                    if ($vnicId) {
                        cmd /c "oci network vnic get --vnic-id $vnicId --output json >$StdoutFile 2>$StderrFile"
                        $vnicData = Get-Content $StdoutFile -Raw | ConvertFrom-Json
                        $publicIp = $vnicData.data.'public-ip'
                    }

                    Write-Host ""
                    Write-Host "=====================================" -ForegroundColor Green
                    Write-Host "  SUCCESS! Instance is RUNNING!" -ForegroundColor Green
                    Write-Host "=====================================" -ForegroundColor Green
                    Write-Host "  Instance: $instanceId" -ForegroundColor Green
                    if ($publicIp) {
                        Write-Host "  IP:       $publicIp" -ForegroundColor Green
                        Write-Host "  Connect:  ssh -i $SshKeyPath ubuntu@$publicIp" -ForegroundColor Green
                    }
                    Write-Host "  SSH Key:  $SshKeyPath" -ForegroundColor Green
                    Write-Host "=====================================" -ForegroundColor Green
                    break
                }
            } catch {
                Write-Host "Launch accepted but parsing failed: $_" -ForegroundColor Yellow
                Write-Host "Check OCI console." -ForegroundColor Yellow
                break
            }
        } else {
            # Check error type
            if ($stderr -match "Out of host capacity" -or $stderr -match "InternalError") {
                Write-Host " Out of capacity. Waiting ${RetryIntervalSeconds}s..." -ForegroundColor Yellow
            } elseif ($stderr -match "LimitExceeded" -or $stderr -match "TooManyRequests") {
                Write-Host " Rate limited. Waiting ${RetryIntervalSeconds}s..." -ForegroundColor Yellow
            } else {
                Write-Host " Error:" -ForegroundColor Red
                Write-Host $stderr -ForegroundColor Red
                Write-Host "Retrying in ${RetryIntervalSeconds}s..." -ForegroundColor Yellow
            }

            Start-Sleep -Seconds $RetryIntervalSeconds
        }
    }
} finally {
    # Cleanup temp files
    Remove-Item $ShapeConfigFile -ErrorAction SilentlyContinue
    Remove-Item $StdoutFile -ErrorAction SilentlyContinue
    Remove-Item $StderrFile -ErrorAction SilentlyContinue
}
