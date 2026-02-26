param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RuntimeDir = Join-Path $RepoRoot '.runtime'
$ProcessFile = Join-Path $RuntimeDir 'processes.json'

if (-not (Test-Path $ProcessFile)) {
    Write-Host '[stop-all] No process state file found. Nothing to stop.'
    exit 0
}

$stateRaw = Get-Content $ProcessFile -Raw
if (-not $stateRaw) {
    Remove-Item $ProcessFile -Force -ErrorAction SilentlyContinue
    Write-Host '[stop-all] Empty process state file removed.'
    exit 0
}

$state = $stateRaw | ConvertFrom-Json
$processes = @($state.processes)

if (-not $processes.Count) {
    Remove-Item $ProcessFile -Force -ErrorAction SilentlyContinue
    Write-Host '[stop-all] No tracked processes. State file removed.'
    exit 0
}

foreach ($proc in $processes) {
    $procId = [int]$proc.pid
    $name = [string]$proc.name
    try {
        $running = Get-Process -Id $procId -ErrorAction Stop
        if ($Force) {
            Stop-Process -Id $procId -Force -ErrorAction Stop
        }
        else {
            Stop-Process -Id $procId -ErrorAction Stop
        }
        Write-Host "[stop-all] Stopped $name (PID=$procId)"
    }
    catch {
        Write-Host "[stop-all] Process already stopped or not found: $name (PID=$procId)"
    }
}

Remove-Item $ProcessFile -Force -ErrorAction SilentlyContinue
Write-Host '[stop-all] Done.'
