# 从零启动 LoRA 面板

## 第一次使用

1. 确认 Docker Desktop 已安装。
2. 双击桌面上的 **启动 LoRA 面板**。
3. 等待 Docker 容器启动完成，浏览器会自动打开：`http://localhost:8080/`。

启动脚本会自动完成：

- 检查 Docker 引擎；
- 必要时尝试启动 Docker Desktop；
- 启动 LoRA API、前端、GPU worker 和独立 Stable Diffusion 服务；
- 等待 API 健康就绪；
- 自动打开浏览器。

启动过程在后台执行，不需要输入 PowerShell 命令。Docker 启动最多等待 3 分钟，面板就绪最多等待 2 分钟；失败会弹出日志位置。

## 独立使用 Stable Diffusion

双击 `D:\LoRA\scripts\start_sd.bat`，仅启动 SD 服务并打开 `http://localhost:8188/`。它使用统一模型目录，可独立于 LoRA 面板使用。

## 手动启动

在 PowerShell 中执行：

```powershell
cd D:\LoRA
docker compose up -d
docker compose --profile sd up -d stable-diffusion
Start-Process http://localhost:8080/
```

## 停止服务

```powershell
cd D:\LoRA
docker compose --profile sd down
```

变更日志：`D:\LoRA\logs\changes.log`。启动详细日志：`D:\LoRA\logs\launcher.log`。默认配置为生产版本，前端源码修改后需在 Docker 中重新构建网页镜像。

桌面快捷方式位置：C:\Users\Administrator\Desktop\启动 LoRA 面板.lnk
