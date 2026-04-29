param(
    [int]$JarvisPort = 8080,
    [int]$OllamaPort = 11434,
    [string]$JarvisHost = "127.0.0.1",
    [string]$OllamaHost = "127.0.0.1",
    [int]$StartupTimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

function Get-ListeningConnection {
    param(
        [string]$LocalHost,
        [int]$Port
    )

    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq $LocalHost -or $_.LocalAddress -eq "0.0.0.0" -or $_.LocalAddress -eq "::" } |
        Select-Object -First 1
}

function Wait-ForPort {
    param(
        [string]$LocalHost,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $conn = Get-ListeningConnection -LocalHost $LocalHost -Port $Port
        if ($conn) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    return $false
}

function Ensure-Ollama {
    param(
        [string]$LocalHost,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $existing = Get-ListeningConnection -LocalHost $LocalHost -Port $Port
    if ($existing) {
        Write-Host "Ollama already listening on $LocalHost`:$Port (PID $($existing.OwningProcess))." -ForegroundColor Green
        return $true
    }

    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaCmd) {
        Write-Host "Ollama CLI not found in PATH. Install Ollama or add it to PATH." -ForegroundColor Red
        return $false
    }

    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Hidden | Out-Null

    if (Wait-ForPort -LocalHost $LocalHost -Port $Port -TimeoutSeconds $TimeoutSeconds) {
        $up = Get-ListeningConnection -LocalHost $LocalHost -Port $Port
        Write-Host "Ollama started (PID $($up.OwningProcess))." -ForegroundColor Green
        return $true
    }

    Write-Host "Ollama did not start listening on $LocalHost`:$Port within timeout." -ForegroundColor Red
    return $false
}

function Ensure-Jarvis {
    param(
        [string]$LocalHost,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $existing = Get-ListeningConnection -LocalHost $LocalHost -Port $Port
    if ($existing) {
        Write-Host "Jarvis API already listening on $LocalHost`:$Port (PID $($existing.OwningProcess))." -ForegroundColor Green
        return $true
    }

    $repoRoot = Split-Path -Parent $PSScriptRoot
    $venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"
    $pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

    Write-Host "Starting Jarvis API..." -ForegroundColor Yellow
    Start-Process -FilePath $pythonExe -ArgumentList "-m", "jarvis", "approvals-api" -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null

    if (Wait-ForPort -LocalHost $LocalHost -Port $Port -TimeoutSeconds $TimeoutSeconds) {
        $up = Get-ListeningConnection -LocalHost $LocalHost -Port $Port
        Write-Host "Jarvis API started (PID $($up.OwningProcess))." -ForegroundColor Green
        return $true
    }

    Write-Host "Jarvis API did not start listening on $LocalHost`:$Port within timeout." -ForegroundColor Red
    return $false
}

Write-Host "Ensuring runtime services are up..." -ForegroundColor Cyan

$okOllama = Ensure-Ollama -LocalHost $OllamaHost -Port $OllamaPort -TimeoutSeconds $StartupTimeoutSeconds
$okJarvis = Ensure-Jarvis -LocalHost $JarvisHost -Port $JarvisPort -TimeoutSeconds $StartupTimeoutSeconds

$healthScript = Join-Path $PSScriptRoot "health-check.ps1"
if (Test-Path $healthScript) {
    Write-Host ""
    Write-Host "Running health-check..." -ForegroundColor Cyan
    & $healthScript -JarvisPort $JarvisPort -OllamaPort $OllamaPort -JarvisHost $JarvisHost -OllamaHost $OllamaHost
    exit $LASTEXITCODE
}

if ($okOllama -and $okJarvis) {
    Write-Host "All services are up." -ForegroundColor Green
    exit 0
}

Write-Host "One or more services failed to start." -ForegroundColor Red
exit 1
