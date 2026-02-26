param(
    [switch]$PrepareOnly,
    [switch]$SkipInstall,
    [switch]$SkipWebBuild,
    [switch]$RebuildWeb
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Launcher = Join-Path $RepoRoot 'start_all.py'

$args = @()
if ($PrepareOnly) { $args += '--prepare-only' }
if ($SkipInstall) { $args += '--skip-install' }
if ($SkipWebBuild) { $args += '--skip-web-build' }
if ($RebuildWeb) { $args += '--rebuild-web' }

python $Launcher @args
