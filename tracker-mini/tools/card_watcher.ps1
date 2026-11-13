# card_watcher.ps1 - notices when the Tracker Mini's SD card is plugged in (USB
# storage mode) and adds new firmware builds to its /Firmware folder.
#
# What it does, every 20 seconds:
#   1. Every 5 minutes, reads tracker-mini/out/CARD_MANIFEST from the GitHub
#      branch. Each line is "<sha256>  <file name>". Files listed there are
#      downloaded into the staging folder and checked against their sha256.
#   2. Looks for a removable volume labelled TRACKER_M that has a \Firmware folder.
#      When it appears or disappears, that is written to the log.
#   3. While the card is present, copies staged TrackerMini*.ptf files that are
#      NOT already in \Firmware, then reads each copy back and compares hashes.
#
# It never deletes, renames or overwrites anything on the card, and it never
# flashes: picking a firmware on the Mini is still done by hand.
#
# Start:  powershell -ExecutionPolicy Bypass -File card_watcher.ps1
# Stop:   close its window, or  Stop-Process -Id (Get-Content <staging>\watcher.pid)
# Log:    <staging>\watcher.log
param(
    [string]$Branch = 'ccr-83e1daf0-dfmcn1',
    [string]$Stage = 'G:\TRACKER_MINI_CLAUDE_STAGING',
    [string]$Label = 'TRACKER_M',
    [int]$PollSeconds = 20
)

$raw = "https://raw.githubusercontent.com/Jordan-Edwards/Jordan-Edwards.github.io/$Branch/tracker-mini/out"
New-Item -ItemType Directory -Force $Stage | Out-Null
$log = Join-Path $Stage 'watcher.log'
$PID | Set-Content (Join-Path $Stage 'watcher.pid')

function Write-Log([string]$message) {
    "$(Get-Date -Format s)  $message" | Add-Content -Path $log
}

function Get-Sha([string]$path) {
    (Get-FileHash -Path $path -Algorithm SHA256).Hash.ToLower()
}

Write-Log "watcher started (pid $PID, branch $Branch)"
$lastFetch = [datetime]::MinValue
$cardSeen = $false

while ($true) {
    try {
        if (((Get-Date) - $lastFetch).TotalMinutes -ge 5) {
            $lastFetch = Get-Date
            $manifest = (Invoke-WebRequest -UseBasicParsing "$raw/CARD_MANIFEST").Content
            foreach ($line in ($manifest -split "`n")) {
                if ($line.Trim() -notmatch '^([0-9a-f]{64})\s+(TrackerMini[A-Za-z0-9_.\-]{1,24}\.ptf)$') { continue }
                $hash = $Matches[1]; $name = $Matches[2]
                $staged = Join-Path $Stage $name
                if ((Test-Path $staged) -and ((Get-Sha $staged) -eq $hash)) { continue }
                $part = "$staged.part"
                Invoke-WebRequest -UseBasicParsing "$raw/$name" -OutFile $part
                if ((Get-Sha $part) -eq $hash) {
                    Move-Item -Force $part $staged
                    Write-Log "staged $name"
                } else {
                    Remove-Item -Force $part
                    Write-Log "download of $name did not match its sha256; not staged"
                }
            }
        }

        $volume = Get-Volume | Where-Object {
            $_.DriveLetter -and $_.DriveType -eq 'Removable' -and $_.FileSystemLabel -eq $Label
        } | Select-Object -First 1
        $firmware = if ($volume) { "$($volume.DriveLetter):\Firmware" } else { $null }

        if ($firmware -and (Test-Path $firmware)) {
            if (-not $cardSeen) {
                $cardSeen = $true
                $names = (Get-ChildItem $firmware -Filter '*.ptf' | Sort-Object Name | ForEach-Object Name) -join ', '
                Write-Log "Tracker card plugged in at $($volume.DriveLetter): - firmware files: $names"
            }
            foreach ($file in Get-ChildItem $Stage -Filter 'TrackerMini*.ptf') {
                $target = Join-Path $firmware $file.Name
                if (Test-Path $target) { continue }
                Copy-Item -Path $file.FullName -Destination $target
                if ((Get-Sha $target) -eq (Get-Sha $file.FullName)) {
                    Write-Log "copied $($file.Name) to the card and verified it"
                } else {
                    Write-Log "copy of $($file.Name) on the card does NOT match; left as is, check by hand"
                }
            }
        } elseif ($cardSeen) {
            $cardSeen = $false
            Write-Log 'Tracker card unplugged'
        }
    } catch {
        Write-Log "error: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $PollSeconds
}
