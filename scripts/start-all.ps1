param(
    [switch]$PrepareOnly,
    [switch]$SkipInstall,
    [switch]$NoNewWindow
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RuntimeDir = Join-Path $RepoRoot '.runtime'
$ProcessFile = Join-Path $RuntimeDir 'processes.json'

$ApiDir = Join-Path $RepoRoot 'services/api'
$WebDir = Join-Path $RepoRoot 'apps/web'
$SidecarDir = Join-Path $RepoRoot 'services/gptk-sidecar'
$WorkerScript = Join-Path $RepoRoot 'workers/python/worker.py'
$VenvPython = Join-Path $ApiDir '.venv/Scripts/python.exe'

function Invoke-StopScriptIfExists {
    if (Test-Path $ProcessFile) {
        Write-Host '[start-all] Existing process file found. Stopping previous stack first...'
        & (Join-Path $PSScriptRoot 'stop-all.ps1') | Out-Null
    }
}

function Ensure-Venv {
    if (-not (Test-Path $VenvPython)) {
        Write-Host '[start-all] Creating python venv in services/api/.venv'
        Push-Location $ApiDir
        try {
            python -m venv .venv
        }
        finally {
            Pop-Location
        }
    }
}

function Ensure-PythonDeps {
    $canImport = $false
    try {
        & $VenvPython -c "import fastapi,uvicorn,sqlalchemy,pydantic,requests" *> $null
        if ($LASTEXITCODE -eq 0) {
            $canImport = $true
        }
    }
    catch {
        $canImport = $false
    }

    if (-not $canImport) {
        Write-Host '[start-all] Installing python dependencies for API'
        Push-Location $ApiDir
        try {
            & $VenvPython -m pip install --upgrade pip
            & $VenvPython -m pip install -e .
        }
        finally {
            Pop-Location
        }
    }
}

function Ensure-NpmDeps {
    param(
        [Parameter(Mandatory = $true)] [string]$ProjectDir,
        [Parameter(Mandatory = $true)] [string]$Label
    )

    $nodeModules = Join-Path $ProjectDir 'node_modules'
    if (-not (Test-Path $nodeModules)) {
        Write-Host "[start-all] Installing npm deps for $Label"
        Push-Location $ProjectDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
}

function Start-ServiceProcess {
    param(
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Command
    )

    $psArgs = @(
        '-NoExit',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        $Command
    )

    if ($NoNewWindow) {
        $proc = Start-Process -FilePath 'powershell' -ArgumentList $psArgs -PassThru -WindowStyle Hidden
    }
    else {
        $proc = Start-Process -FilePath 'powershell' -ArgumentList $psArgs -PassThru
    }

    Write-Host "[start-all] Started $Name (PID=$($proc.Id))"

    return [pscustomobject]@{
        name = $Name
        pid = $proc.Id
        command = $Command
        started_at = (Get-Date).ToString('o')
    }
}

function Wait-HttpHealthy {
    param(
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host "[start-all] $Name is up ($Url)"
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds 600
        }
    }

    Write-Host "[start-all] WARNING: $Name did not become healthy within $TimeoutSeconds seconds ($Url)"
    return $false
}

Write-Host '[start-all] Preparing environment...'

if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

Invoke-StopScriptIfExists
Ensure-Venv

if (-not $SkipInstall) {
    Ensure-PythonDeps
    Ensure-NpmDeps -ProjectDir $WebDir -Label 'web'
    Ensure-NpmDeps -ProjectDir $SidecarDir -Label 'gptk-sidecar'
}

if ($PrepareOnly) {
    Write-Host '[start-all] Preparation completed. No service started because -PrepareOnly was set.'
    exit 0
}

Write-Host '[start-all] Starting services...'

$apiCmd = "Set-Location '$ApiDir'; & '$VenvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$workerCmd = "Set-Location '$ApiDir'; & '$VenvPython' '$WorkerScript'"
$sidecarCmd = "Set-Location '$SidecarDir'; npm run dev"
$webCmd = "Set-Location '$WebDir'; npm run dev -- --host 127.0.0.1 --port 5173"

$processes = @()
$processes += Start-ServiceProcess -Name 'api' -Command $apiCmd
$processes += Start-ServiceProcess -Name 'worker' -Command $workerCmd
$processes += Start-ServiceProcess -Name 'gptk-sidecar' -Command $sidecarCmd
$processes += Start-ServiceProcess -Name 'web' -Command $webCmd

$state = [pscustomobject]@{
    repo_root = $RepoRoot
    started_at = (Get-Date).ToString('o')
    processes = $processes
}

$state | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ProcessFile

Wait-HttpHealthy -Name 'api' -Url 'http://127.0.0.1:8000/health' -TimeoutSeconds 35 | Out-Null
Wait-HttpHealthy -Name 'gptk-sidecar' -Url 'http://127.0.0.1:8787/health' -TimeoutSeconds 20 | Out-Null
Wait-HttpHealthy -Name 'web' -Url 'http://127.0.0.1:5173' -TimeoutSeconds 30 | Out-Null

Write-Host ''
Write-Host '[start-all] All services started.'
Write-Host '  API:     http://127.0.0.1:8000'
Write-Host '  Web:     http://127.0.0.1:5173'
Write-Host '  Sidecar: http://127.0.0.1:8787/health'
Write-Host "[start-all] Process state file: $ProcessFile"
