# 大文件恢复

## 模型归档

将 `manchu-window-models.tar.part001` 到最后一片按文件名顺序放到同一目录，再使用二进制拼接得到 `manchu-window-models.tar`。Windows PowerShell 可使用：

```powershell
$out = [IO.File]::Create('manchu-window-models.tar')
try {
  Get-ChildItem -File 'manchu-window-models.tar.part*' | Sort-Object Name | ForEach-Object {
    $in = [IO.File]::OpenRead($_.FullName)
    try { $in.CopyTo($out) } finally { $in.Dispose() }
  }
} finally { $out.Dispose() }
```

用 `docs/archive-parts-sha256.csv` 校验每一片；拼接后的整包 SHA-256 应为：

`fbaef0b26c77805bfb46457034af6a51149da6c476969260f8f7ec44bd12b6d8`

解包后，模型会恢复到 `data/models/`。

## 训练数据与数据库

- `manchu-window-training-assets.tar` 解包到 `E:\LoRA-Manzhou`，包含 `datasets/`、`runs/`、`reports/`。
- 数据库私密归档不进入公开仓库；公开仓库只保留脱敏结构和状态导出。

## 端口

恢复后保持 `docs/../docker/ports-and-services.md` 中记录的端口映射，不要重新分配端口。
