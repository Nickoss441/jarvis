param(
    [int]$JarvisPort = 8080,
    [int]$OllamaPort = 11434,
    [string]$JarvisHost = "127.0.0.1",
    [string]$OllamaHost = "127.0.0.1"
)

function Get-ListeningConnection {
    param(
        [string]$LocalHost,
        [int]$Port
    )

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq $LocalHost -or $_.LocalAddress -eq "0.0.0.0" -or $_.LocalAddress -eq "::" } |
        Select-Object -First 1

    return $conn
}

function Write-StatusLine {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    if ($Ok) {
        Write-Host "[OK]   $Name - $Detail" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] $Name - $Detail" -ForegroundColor Red
    }
}

$results = @()

$ollamaProcs = Get-Process -Name ollama -ErrorAction SilentlyContinue
$ollamaConn = Get-ListeningConnection -LocalHost $OllamaHost -Port $OllamaPort
$ollamaOk = ($null -ne $ollamaProcs) -and ($null -ne $ollamaConn)
$ollamaDetail = if ($ollamaOk) {
    "PID $($ollamaConn.OwningProcess) listening on $OllamaHost`:$OllamaPort"
}
elseif ($null -eq $ollamaProcs) {
    "process not running"
}
else {
    "process exists but port $OllamaPort is not listening"
}
$results += [pscustomobject]@{ Name = "Ollama"; Ok = $ollamaOk; Detail = $ollamaDetail }

$jarvisConn = Get-ListeningConnection -LocalHost $JarvisHost -Port $JarvisPort
$jarvisProc = if ($jarvisConn) { Get-CimInstance Win32_Process -Filter "ProcessId = $($jarvisConn.OwningProcess)" -ErrorAction SilentlyContinue } else { $null }
$jarvisOk = $null -ne $jarvisConn
$jarvisDetail = if ($jarvisOk) {
    if ($jarvisProc) {
        "PID $($jarvisConn.OwningProcess) listening on $JarvisHost`:$JarvisPort ($($jarvisProc.Name))"
    }
    else {
        "PID $($jarvisConn.OwningProcess) listening on $JarvisHost`:$JarvisPort"
    }
}
else {
    "not listening on $JarvisHost`:$JarvisPort"
}
$results += [pscustomobject]@{ Name = "Jarvis API port"; Ok = $jarvisOk; Detail = $jarvisDetail }

$healthOk = $false
$healthDetail = "health endpoint not checked (API not listening)"
if ($jarvisOk) {
    try {
        $resp = Invoke-RestMethod -Method Get -Uri "http://$JarvisHost`:$JarvisPort/health" -TimeoutSec 4
        if ($resp -and $resp.status) {
            $status = [string]$resp.status
            $healthOk = $status -eq "ok" -or $status -eq "degraded"
            $healthDetail = "status=$status"
        }
        else {
            $healthDetail = "no status field in response"
        }
    }
    catch {
        $healthDetail = "request failed: $($_.Exception.Message)"
    }
}
$results += [pscustomobject]@{ Name = "Jarvis /health"; Ok = $healthOk; Detail = $healthDetail }

Write-Host "Jarvis runtime health check" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
Write-Host ""

foreach ($r in $results) {
    Write-StatusLine -Name $r.Name -Ok $r.Ok -Detail $r.Detail
}

$failed = ($results | Where-Object { -not $_.Ok }).Count
Write-Host ""
if ($failed -eq 0) {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
}

Write-Host "$failed check(s) failed." -ForegroundColor Red
exit 1
