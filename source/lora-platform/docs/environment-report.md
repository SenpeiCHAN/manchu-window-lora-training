# LoRA 平台环境报告

更新日期：2026-10-05（Asia/Shanghai）

## 已验证

- Windows 11 专业版。
- NVIDIA GeForce RTX 4060 Laptop GPU，显存 8188 MiB。
- NVIDIA 驱动 591.74，`nvidia-smi` 显示 CUDA Version 13.1。
- Docker Desktop 4.93.0、Docker Engine/CLI 29.8.1、Compose v5.5.1 已启动并可用。
- WSL 2 已安装，Docker context 为 `desktop-linux`。
- Docker Server 返回正常，Linux engine 使用 WSL2，默认运行时为 `runc`，已发现 NVIDIA runtime。
- `docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu22.04 nvidia-smi` 已通过，容器成功识别 RTX 4060 Laptop GPU。
- GPU 测试显示驱动 591.74、CUDA Version 13.1、显存 8188 MiB。
- React/Vite 前端依赖已在 `frontend` 目录安装。
- `npm run build` 已通过，生成 Vite production bundle。
- Python backend 通过 `compileall` 语法检查。
- Hugging Face 资源候选已核对：SD1.5 与 WD14 ConvNeXtV2 仓库可用；下载脚本已加入 worker 镜像。
- `nvidia/cuda:12.8.1-base-ubuntu22.04` GPU 验证镜像已拉取并运行成功。
- `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` 镜像标签已核对；平台 worker 仍需在 Compose 构建时拉取。
- Docker Desktop WSL2 数据盘已从 C 盘迁移到 D 盘，当前实际位置为 `D:\docker\DockerDesktopWSL\DockerDesktopWSL\disk\docker_data.vhdx`（约 20.8GB）。按用户确认，Docker Desktop 公共数据保留在 `D:\docker`；LoRA 项目数据通过 Compose 从 `D:\LoRA` 挂载到容器。
- sd-scripts v0.12.0 commit `690ea7f96c23182352ec63def76d431c6120bd2f` 已装入 worker。
- 真实 WD14 测试已通过：1 张测试图使用 `CUDAExecutionProvider` 完成 ONNX 推理并生成 caption。
- SD1.5 checkpoint 已下载到 `D:\LoRA\data\models\sd15\v1-5-pruned-emaonly.safetensors`，大小 4,265,146,304 bytes。
- 独立 ComfyUI Stable Diffusion 服务已构建并运行在 `http://localhost:8188`，容器内识别 RTX 4060 Laptop GPU；共享模型与 LoRA 目录已生效。
- 真实 CUDA LoRA 短训已完成：1 张带 WD14 标签的图片、`max_train_steps=2`、FP16、`networks.lora`，生成 `data/runs/smoke/smoke_lora.safetensors` 及两份 step checkpoint。
- 训练产物已用 safetensors 读取校验（792 个 tensor keys），ComfyUI 已发现共享 LoRA 文件。

## 已解决的问题

此前 Docker Desktop 4.72.0 的后端曾因 Inference manager socket 无法访问而启动失败。按日志完成 WSL、Docker 服务和 Docker Desktop 重启后，当前已升级/运行 Docker Desktop 4.93.0，Docker Server 与 GPU 透传均已恢复。

此前关键错误为：

```text
starting services: initializing Inference manager:
listening on unix://<HOME>\AppData\Local\Docker\run\dockerInference:
remove <HOME>\AppData\Local\Docker\run\dockerInference:
The file cannot be accessed by the system.
```

该错误当前不再复现。之前尚未执行的 Compose 构建、容器内 CUDA 检查和模型任务现在可以继续。

## 尚未完成的验证

- 将真实训练和推理任务接入 API/worker 的作业队列，并由网页提交；
- 使用生成的 LoRA 完成一次 ComfyUI 基础模型 / LoRA 图像对比；
- 完善前端数据集导入、标签编辑、训练参数提交和任务事件展示；
- 在低磁盘空间场景增加模型清理和下载前检查。

已经关闭 Docker Desktop 的可选 Docker AI 开关，并保留了本次恢复记录；没有执行 Factory Reset。

## 已完成的恢复步骤

1. 在项目目录执行 `docker compose build`，再执行 `docker compose up -d`；核心服务和独立 SD 服务均已启动。
2. 已检查 `docker compose ps`、`http://localhost:8080` 和 `http://localhost:8188`。
3. 已在 worker 容器中完成 PyTorch CUDA 张量检查：

   ```powershell
   docker run --rm --gpus all pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print((torch.ones(4, device='cuda') @ torch.ones(4, device='cuda')).item())"
   ```

4. 已在 worker 容器内准备 SD1.5 checkpoint 和 WD14 资源；下载和清理过程记录在 `logs/changes.log`。

   ```powershell
   docker compose run --rm worker python /app/scripts/prepare_models.py --model wd14 --revision <已核对的提交 SHA>
   docker compose run --rm worker python /app/scripts/prepare_models.py --model sd15 --revision <已核对的提交 SHA>
   ```

5. 已用 1 张图片验证 WD14，并完成 2 步真实 SD1.5 LoRA 短训；正式训练仍需由平台队列和网页参数驱动。

## 2026-10-05 前端端到端复验

- 在浏览器 LoRA 面板的「推理测试」页面直接提交 job_cee9a7330337，任务使用 SD1.5、mvp_queue_real-step00000001.safetensors、512x512、20 steps、seed 42。
- 真实 ComfyUI 队列成功输出基础模型图与 LoRA 对比图：/data/outputs/lora-platform/job_cee9a7330337/。
- 重启后 http://localhost:8188/system_stats 返回 HTTP 200；四个 Docker 服务均处于运行状态。


## Google 文档交付

- 报告链接：https://docs.google.com/document/d/18YjbxWhGs9q1ud6y6gQ7B-6sZljn7p01EHywXaF7CYo
- 已包含原理、配置流程、前端完整操作路径、真实 MVP 结果、三张推理/样本图片和验收表。

