# 独立 Stable Diffusion

本目录保存独立 Stable Diffusion 容器的用户配置和输入文件。应用本体运行在 Docker 镜像中，使用 ComfyUI；基础模型和 LoRA 产物通过 `D:\LoRA\data` 共享。

启动：

```powershell
docker compose --profile sd build stable-diffusion
docker compose --profile sd up -d stable-diffusion
```

打开 `http://localhost:8188`。停止：

```powershell
docker compose --profile sd stop stable-diffusion
```

## 让网页训练任务执行真实 CUDA

默认 worker 保持演示模式，便于先检查页面和队列。确认数据集与模型路径后，可用真实执行覆盖文件启动：

```powershell
docker compose -f compose.yaml -f compose.real.yaml up -d worker
```

真实模式下，网页训练页提交的任务会由 `/opt/sd-scripts/train_network.py` 在 RTX 4060 上执行；输出仍写入 `D:\LoRA\data\runs`。完成验证后如需恢复演示模式，重新执行 `docker compose up -d worker` 即可。

Stable Diffusion 服务可以独立启动和停止，不依赖 API 或训练 worker。它读取 `/data/models/sd15` 作为基础模型，并把 `/data/runs` 中的 LoRA 产物映射到 ComfyUI 的 LoRA 目录。
