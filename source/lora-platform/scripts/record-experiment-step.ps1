param(
    [Parameter(Mandatory=$true)][string]$Step,
    [Parameter(Mandatory=$true)][string]$Action,
    [Parameter(Mandatory=$true)][string]$Result,
    [Parameter(Mandatory=$true)][string]$Screenshot,
    [ValidateSet('passed','failed','baseline','running')][string]$Status='passed',
    [string]$Note=''
)
$experimentRoot = 'E:\LoRA-Manzhou'
$shotPath = (Resolve-Path -LiteralPath $Screenshot -ErrorAction Stop).Path
$expectedRoot = Join-Path $experimentRoot 'reports\screenshots'
if (-not $shotPath.StartsWith($expectedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '截图必须保存在本实验 reports/screenshots 目录' }
$stamp = Get-Date -Format o
$record = [ordered]@{time=$stamp;step=$Step;action=$Action;result=$Result;screenshot=$shotPath;status=$Status;note=$Note}
$record | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $experimentRoot 'logs\experiment.jsonl') -Encoding utf8
$relativeShot = 'screenshots/' + [IO.Path]::GetFileName($shotPath)
$section = "`n## 步骤 $Step ：$Action`n`n时间：$stamp  `n状态：$Status  `n结果：$Result  `n备注：$Note`n`n![$Action]($relativeShot)`n"
Add-Content -LiteralPath (Join-Path $experimentRoot 'reports\experiment-record.md') -Value $section -Encoding utf8
Add-Content -LiteralPath 'D:\LoRA\logs\changes.log' -Value "$stamp | experiment-$Step | $Action | $Status | $Result | 截图：$shotPath | $Note" -Encoding utf8
