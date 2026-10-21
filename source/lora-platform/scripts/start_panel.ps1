param([ValidateSet('Panel', 'SD')][string]$Mode = 'Panel', [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$logPath = Join-Path $projectRoot 'logs/launcher.log'
$changeLog = Join-Path $projectRoot 'logs/changes.log'
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'logs') -Force | Out-Null
function Log([string]$Message) {
    $entry = '{0:yyyy-MM-dd HH:mm:ss zzz} | launcher | {1}' -f (Get-Date), $Message
    Add-Content -LiteralPath $logPath -Value $entry -Encoding utf8
    Add-Content -LiteralPath $changeLog -Value $entry -Encoding utf8
}
function Invoke-Docker([string[]]$DockerArguments, [switch]$Quiet) {
    $stdoutPath = Join-Path $projectRoot 'logs/launcher-docker.out.log'
    $stderrPath = Join-Path $projectRoot 'logs/launcher-docker.err.log'
    $process = Start-Process -FilePath 'docker.exe' -ArgumentList $DockerArguments -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (!$Quiet) {
        Get-Content -LiteralPath $stdoutPath, $stderrPath | Add-Content -LiteralPath $logPath -Encoding utf8
    }
    return $process.ExitCode
}
try {
    Log "Start $Mode"
    if ((Invoke-Docker @('info') -Quiet) -ne 0) {
        Log 'Starting Docker Desktop'
        Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
    }
    $deadline = (Get-Date).AddMinutes(3)
    do {
        if ((Invoke-Docker @('info') -Quiet) -eq 0) { break }
        if ((Get-Date) -gt $deadline) { throw 'Docker 启动超时，请查看 Docker Desktop。' }
        Start-Sleep -Seconds 2
    } while ($true)
    if ($Mode -eq 'SD') {
        $dockerResult = Invoke-Docker @('compose', '--profile', 'sd', 'up', '-d', '--no-build', 'stable-diffusion')
        $url = 'http://localhost:8188/'
        $probe = 'http://localhost:8188/system_stats'
    } else {
        $dockerResult = Invoke-Docker @('compose', '--profile', 'sd', 'up', '-d', '--no-build')
        $url = 'http://localhost:8080/'
        $probe = 'http://localhost:8080/api/health'
    }
    if ($dockerResult -ne 0) { throw '项目容器启动失败。' }
    $deadline = (Get-Date).AddMinutes(2)
    do {
        try { $null = Invoke-WebRequest -Uri $probe -UseBasicParsing -TimeoutSec 5; break }
        catch { if ((Get-Date) -gt $deadline) { throw '页面服务启动超时。' }; Start-Sleep -Seconds 2 }
    } while ($true)
    Log "Ready $url"
    if (!$NoBrowser) { Start-Process $url }
} catch {
    Log "Failed: $($_.Exception.Message)"
    if (!$NoBrowser) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("$($_.Exception.Message)`n详细日志：$logPath", 'LoRA 启动失败') | Out-Null
    }
    exit 1
}

