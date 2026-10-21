# LoRA 训练平台技术方案

> 更新日期：2026-10-08  
> 项目目录：`D:\LoRA`  
> Compose 项目名称：`lora-platform`  
> 当前阶段：真实 MVP 已验证。2026-10-08 完成 Linear 双主题、字体嵌入、SSH 连接扩展、默认生产启动和项目存储迁移。最新架构及验收详见 [整理报告](architecture-and-ui-20261008.md)。

## 1. 目标与范围

以 ChatGPT / Codex 辅助完成一个中文、单机使用的 LoRA 训练平台。平台需要覆盖以下完整流程：

**导入图片 → 自动打标与人工修订 → 配置训练参数 → CUDA 训练与过程监控 → 保存 LoRA → 对比推理结果。**

| 作业要求 | 平台实现 | 验收结果 |
| --- | --- | --- |
| 数据集管理 | 图片导入、预览、质量检查、标签关联、数据集版本 | 能在网页中准备并选定一份训练数据集 |
| 图片数据打标 | 调用 WD14 ONNX 模型，生成同名 TXT，支持人工修订 | 图片与标签一一对应，修改结果可以保存 |
| 参数可视化配置 | 中文表单、预设、参数解释、校验和配置导出 | 用户通过表单提交训练，无需手写命令 |
| 训练与过程可视化 | 任务状态、训练步数、损失曲线、日志、产物 | 能查看真实训练进度并找到生成的 LoRA |
| 复用 sd-scripts | 固定版本的训练后端，通过适配层调用 | 实际训练由 `train_network.py` 完成 |
| SD + LoRA 推理测试 | 相同基础模型、提示词和随机种子的对比生成 | 能加载新 LoRA，并展示无 LoRA / 有 LoRA 的结果 |

首版围绕 **Stable Diffusion 1.5、单张 NVIDIA 显卡、一个 GPU 任务执行器** 实现。前端、API、依赖安装、构建、打标、训练、推理及项目测试均在 Docker 中运行。

Windows 提供 NVIDIA 驱动、WSL2 和 Docker Desktop；浏览器用于访问网页，`D:\LoRA` 用于保存源码与持久文件。宿主机不承担项目的 Python、Node 或模型运行环境。ChatGPT 用于需求梳理、开发和排错，平台首版不需要调用 ChatGPT API。

截图里的 Trae、API Key 和具体命令属于参考开发方法。实际实现以本方案、固定版本代码及容器验证结果为准。

## 2. 已检查的本机条件

以下为规划阶段的检查结果，执行配置前需要重新检查动态指标。

| 项目 | 检查结果 | 对方案的影响 |
| --- | --- | --- |
| 操作系统 | Windows 11 专业版 | 使用 Docker Desktop 的 WSL2 Linux 后端 |
| 显卡 | NVIDIA GeForce RTX 4060 Laptop GPU | 单卡 CUDA 训练 |
| 显存 | 8188 MiB，约 8GB | 512 分辨率、batch 1 起步；GPU 任务串行 |
| NVIDIA 驱动 | 591.74 | 先使用现有驱动验证容器计算 |
| nvidia-smi 显示的 CUDA Version | 13.1 | 表示驱动支持上限；容器运行时可选择兼容的 CUDA 12.8 |
| 系统内存 | 约 16GB；检查时空闲约 2.6GB | 建立内存检查；减少加载进程和数据读取并发 |
| Docker | 客户端已安装，当前 context 为 `desktop-linux` | 无需重新安装 Docker 客户端 |
| Docker 引擎 | 检查时未启动 | 第一个实施步骤是启动并确认引擎可用 |
| WSL | 已安装；docker-desktop 为 WSL2 | 继续验证 GPU 透传 |
| 项目目录 | 检查时为空 | 从新的项目结构开始 |
| D 盘空间 | 检查时剩余约 54.3GB | 下载前检查空间，限制模型副本、缓存与训练 state 数量 |

Docker Desktop 在 Windows 上的 NVIDIA GPU 透传使用 WSL2 后端，实施时必须在容器内实际验证。[Docker 官方 GPU 文档](https://docs.docker.com/desktop/features/gpu/)

WSL 使用 Windows NVIDIA 驱动提供的 CUDA 接口；按 NVIDIA 文档配置，避免在 WSL 内安装另一套 Linux 显示驱动。[NVIDIA WSL 指南](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

## 3. 技术栈与版本策略

### 3.1 技术选型

| 部分 | 选择 | 选择原因 |
| --- | --- | --- |
| 前端 | React + TypeScript + Vite | 适合本地训练工作台，组件与接口边界清楚 |
| UI | CSS 主题变量 + Lucide 图标 | Linear 风格、双主题、本地阿里巴巴普惠体 2.0 |
| 过程显示 | 原生进度条与真实日志 | 步数、状态、训练日志及产物；专用损失曲线仍是后续扩展 |
| 页面与服务端数据 | React 状态 + 公共 fetch 接口 | 七页导航、轮询和任务提交；设置值未变化时保留编辑输入 |
| API | FastAPI + Pydantic | 参数校验、文件操作、任务接口和 SSE 事件 |
| 数据记录 | Python sqlite3 + SQLite WAL | 单 API、单 worker 本机任务管理 |
| GPU 执行器 | Python 任务执行器 + 独立任务子进程 | 统一调度打标、训练和推理，结束后释放模型 |
| 打标 | sd-scripts WD14 脚本 + ONNX Runtime GPU | 对接作业提供的 WD14 模型资源 |
| 训练 | kohya-ss/sd-scripts `train_network.py` | 复用成熟 LoRA 后端 |
| 首版推理 | 同一版本 sd-scripts 的 `gen_img.py` | 复用训练依赖，减少另一套推理环境占用 |
| 对外入口 | Nginx | 提供网页，并转发 `/api` 和事件流 |
| 编排 | Docker Compose | 统一构建、启动、命名、挂载和 GPU 配置 |

首版 API 保持 CPU 服务，所有模型计算交给 GPU 执行器。通过网页提交任务后，API 将任务写入持久队列；执行器逐个领取任务。当前单机规模使用 SQLite 即可。

若后续需要独立 Diffusers 推理或多人并发，再新增隔离的推理环境或调整队列与数据库；首版先完成上述六项功能。

### 3.2 候选版本基线

| 项目 | 候选基线 | 验证与锁定方式 |
| --- | --- | --- |
| GPU 容器 Python | 3.10 | 对齐 sd-scripts 当前发布版 CI，构建时记录补丁版本 |
| API Python | 3.11 | API 单独构建，不引入训练依赖 |
| CUDA / cuDNN | CUDA 12.8 / cuDNN 9 | 选择匹配的 NVIDIA Linux 运行镜像，验证后记录 digest |
| PyTorch | `torch==2.8.0`，cu128 | 显式安装并通过 constraints 防止隐式升级 |
| torchvision | `torchvision==0.23.0` | 与 PyTorch 版本对应 |
| sd-scripts | `v0.12.0` | 实施时解析并记录完整 commit SHA |
| 训练依赖 | 按该 release 的 requirements | 验证后冻结完整依赖；未锁定的间接依赖也要记录 |
| ONNX Runtime GPU | CUDA 12 / cuDNN 9 对应版本 | 对照官方兼容表选定具体版本，并执行真实打标验证 |
| 前端 Node | 22，满足所选 Vite 的最低补丁版本 | 实施时确认兼容要求并固定镜像 digest |
| 前端及 API 包 | 首次构建时解析兼容版本 | 提交前端 lockfile 与 API 锁定依赖 |

PyTorch 官方提供 torch 2.8.0、torchvision 0.23.0 和 cu128 的组合；sd-scripts v0.12.0 的 CI 覆盖 Python 3.10 与 PyTorch 2.8.0。这些资料支持候选方案，实际导入、训练及显存占用仍需验证。[PyTorch 版本表](https://pytorch.org/get-started/previous-versions/)、[sd-scripts CI](https://github.com/kohya-ss/sd-scripts/blob/v0.12.0/.github/workflows/tests.yml)

不从截图逐项手改 requirements。先固定 PyTorch，再按所选 release 安装，检查依赖冲突、CUDA 加载和短训练，最后冻结完整环境。[sd-scripts 固定版本依赖](https://github.com/kohya-ss/sd-scripts/blob/v0.12.0/requirements.txt)

ONNX Runtime 的不同版本对应不同 CUDA/cuDNN 组合；不能仅使用未锁定的最新版包。[ONNX Runtime CUDA 兼容表](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)

## 4. 容器、镜像与访问地址

### 4.1 核心服务与独立 SD

| Compose 服务 | 容器名称 | 镜像命名 | 职责 |
| --- | --- | --- | --- |
| `web` | `lora-web` | `lora-platform-web` | 默认 Nginx 静态前端；显式开发模式使用 Vite |
| `api` | `lora-api` | `lora-platform-api` | 数据集、标签、模型、任务、事件、SSH 配置和查询 |
| `worker` | `lora-gpu-worker` | `lora-platform-worker` | WD14 与 sd-scripts CUDA 训练、串行调度推理 |
| `stable-diffusion` | `lora-stable-diffusion` | `lora-platform-stable-diffusion` | 独立 ComfyUI 推理，SD profile，使用本机 GPU |

统一命名：

- Compose 项目：`lora-platform`。
- 容器网络：`lora-platform_default`。
- 状态目录：`D:\LoRA\data\state`。
- 缓存目录：`D:\LoRA\data\cache`。
- 开发依赖目录：`D:\LoRA\data\dev\node_modules`；默认生产容器无 Node 依赖挂载。
- 网页入口：`http://localhost:8080`，默认仅绑定 `127.0.0.1`。

开发模式与交付模式通过 Compose override 文件切换，不同时启动两个同名 web 容器。开发时由 Vite 转发 `/api`；交付时由 Nginx 转发。API 的内部地址为 `http://api:8000`，worker 无需对外端口。

Node 依赖安装、类型检查和网页构建在 web 容器内执行；API 与 worker 测试在对应容器内执行。如需要 Playwright，使用专用测试镜像连接同一容器网络。

### 4.2 GPU 与资源约束

Compose 的 worker 服务声明 NVIDIA GPU，数量为 1，并配置 `capabilities: [gpu]`。API 和 web 不分配 GPU。[Docker Compose GPU 配置](https://docs.docker.com/compose/how-tos/gpu-support/)

worker 只启动一个实例，使用 `init: true` 管理子进程，并按运行情况配置共享内存。训练、打标、推理统一串行，不允许推理模型常驻占用训练显存。

实施时检查 Docker 镜像磁盘所在盘的空间，而不只检查 D 盘。WSL 内存与 CPU 配额结合当前宿主占用再设定；首轮训练使用数据读取进程 0，避免多进程额外内存占用。

## 5. 目录结构、挂载与路径配置

### 5.1 计划建立的项目结构

```text
D:\LoRA\
├─ compose.yaml
├─ compose.dev.yaml
├─ .env.example
├─ frontend\
├─ backend\
│  ├─ api\
│  ├─ worker\
│  └─ shared\
├─ docker\
│  ├─ web.Dockerfile
│  ├─ api.Dockerfile
│  ├─ worker.Dockerfile
│  └─ nginx.conf
├─ configs\
│  ├─ presets\
│  └─ dependency-locks\
├─ data\
│  ├─ models\
│  │  ├─ sd15\
│  │  └─ wd14\
│  ├─ datasets\
│  ├─ runs\
│  ├─ outputs\
│  ├─ cache\
│  └─ backups\
├─ tests\
└─ docs\
   ├─ technical-plan.md
   ├─ environment-report.md
   └─ acceptance-report.md
```

此目录树是当前实现的目标结构，源码、Docker 配置、模型准备脚本和报告已经建立；模型文件与真实训练产物仍按后续验证阶段下载和生成。

### 5.2 路径映射

| 宿主路径或卷 | 容器路径 | 使用规则 |
| --- | --- | --- |
| `D:\LoRA\frontend` | `/app/frontend` | 仅开发时挂载源码，依赖挂载 data/dev/node_modules |
| `D:\LoRA\backend` | `/app/backend` | 开发时挂载源码，交付时复制到镜像 |
| `D:\LoRA\data\models` | `/data/models` | 基础模型、tokenizer、配置、WD14 资源 |
| `D:\LoRA\data\datasets` | `/data/datasets` | 图片、同名 TXT、不可变训练版本 |
| `D:\LoRA\data\runs` | `/data/runs` | 任务配置、日志、TensorBoard、LoRA、训练 state |
| `D:\LoRA\data\outputs` | `/data/outputs` | 推理结果图与生成参数 |
| `D:\LoRA\data\cache` | `/cache` | 下载与运行缓存；控制重复存储 |
| `D:\LoRA\data\backups` | `/backups` | 数据库快照和必要配置备份 |
| `D:\LoRA\data\state` | `/state` | SQLite 数据库、WAL、SHM、SSH 非敏感配置；API 与 worker 共享 |
| worker 镜像内部 | `/opt/sd-scripts` | 固定 commit 的上游代码 |
| worker 镜像内部 | `/opt/conda` | PyTorch CUDA 基础镜像的 Python 运行环境 |

根据用户统一放在 LoRA 目录的要求，数据库现改为本机 Docker Desktop 的目录挂载。迁移使用 SQLite backup 接口，完整性检查通过；API 轮询与 worker 写入期间，真实训练、推理再次通过。限当前本机单 API、单 worker 使用，不迁至网络共享盘；原始状态恢复备份位于 `data/backups/state-before-20261008.db`。

### 5.3 统一配置与路径安全

计划在 `.env.example` 中定义：

```dotenv
COMPOSE_PROJECT_NAME=lora-platform
LORA_HOST_ROOT=D:/LoRA
LORA_DATA_ROOT=/data
LORA_MODELS_DIR=/data/models
LORA_DATASETS_DIR=/data/datasets
LORA_RUNS_DIR=/data/runs
LORA_OUTPUTS_DIR=/data/outputs
LORA_STATE_DB=/state/lora.db
SD_SCRIPTS_DIR=/opt/sd-scripts
HF_HOME=/cache/huggingface
TORCH_HOME=/cache/torch
TZ=Asia/Shanghai
```

宿主路径用于 Compose 挂载，进入容器后的程序只使用 Linux 路径。前端提交数据集和模型 ID；由后端解析已登记路径，防止 Windows 路径被传入训练命令。

API 对路径进行规范化和目录边界检查；ZIP 导入限制文件数量与大小，拒绝越界路径。模型权重优先使用 `.safetensors`。训练参数通过白名单和结构化配置传递，子进程以参数数组启动，不拼接用户提供的 shell 命令。

## 6. 数据、模型与任务设计

### 6.1 核心记录

| 记录 | 主要内容 |
| --- | --- |
| Dataset | 名称、图片数量、路径、当前版本、质量检查结果 |
| DatasetVersion | 图片和标签清单、hash、创建时间、审核状态 |
| Model | SD1.5 / WD14 / LoRA 类型、本地路径、来源、revision、hash |
| TrainingConfig | 数据集版本、基础模型、参数、输出策略 |
| Job | 类型、状态、配置快照、执行器标识、开始与结束时间 |
| JobEvent | 单调事件 ID、任务 ID、状态与日志事件 |
| Artifact | LoRA、训练 state、配置、曲线数据和推理图的关联 |

每次训练固定数据集版本、标签和参数快照。提交后的标签修改不改变该训练任务；下一次训练使用新的数据集版本。

基础模型优先使用作业提供的 `sd15-hf-offline` 资源，WD14 优先使用作业对应的模型目录。缺少资源时，在容器内从模型发布者渠道下载，并记录具体 revision 与文件 hash。资源来源、可用文件和下载许可在实施时确认，不将其他权重静默替换成所要求的模型。

单个 `.safetensors` 文件不一定覆盖离线推理所需的 tokenizer 与配置。资源登记阶段要验证训练与推理各自需要的全部文件；下载完成后进行离线可用性检查。

### 6.2 任务队列和生命周期

任务状态：

```text
queued → validating → running → succeeded / failed
queued → cancelled
running → cancelling → cancelled
validating / running → interrupted（执行器重启或失联）
```

队列由 SQLite 持久保存，worker 在短事务中原子领取任务，并记录执行器实例和心跳。单 worker 保证任意时刻只有一个模型任务占用 GPU。

每个任务使用独立子进程组。取消时先请求正常退出，超过宽限期才结束整个进程组；确认子进程退出后才能领取下一任务。任务停止不承诺保存当前步数，只展示已经实际写出的检查点。

API 重启不应中断仍正常运行的 worker。worker 重启后核对所属任务，将已经失去执行进程的任务标记为 interrupted，保留待执行队列，不自动重复跑中断训练。

提供任务提交幂等标识，防止重复点击产生重复训练。状态错误、资源不足、CUDA 不可用等情况均返回可操作的中文原因；训练无法使用 GPU 时直接失败，不静默切换 CPU。

只有已保存完整训练 state 时才提供断点恢复。单独的 LoRA 权重可作为继续微调的起点，不能宣称已恢复优化器和随机状态。

### 6.3 首版接口范围

| 接口组 | 计划接口与用途 |
| --- | --- |
| 环境 | `GET /api/health`；`GET /api/system`，返回服务、worker、GPU与存储状态 |
| 数据集 | `/api/datasets`，创建、列表、导入、查询图片与版本 |
| 标签 | `/api/datasets/{id}/images/{image_id}/caption`，读取与保存 |
| 模型 | `/api/models`，登记、校验、查询和关联产物 |
| 训练配置 | `/api/training-configs`，预设、校验与保存 |
| 任务 | `POST /api/jobs`；`GET /api/jobs/{id}`；`POST /api/jobs/{id}/cancel` |
| 事件流 | `GET /api/jobs/{id}/events`，SSE 推送状态、进度与日志 |
| 产物 | `/api/artifacts`，查询与下载已完成文件 |

SSE 事件使用可恢复的事件 ID。浏览器重连后补取状态与事件；损失曲线从持久指标读取，刷新页面不会丢失历史。开发与交付代理均关闭 SSE 响应缓冲，并配置适当超时。

## 7. 打标、训练和推理方法

### 7.1 数据集与 WD14

1. 导入图片，检查损坏文件、重复图片、尺寸、方向和缺失标签。
2. 保留原图，通过分桶或明确的预处理配置建立训练版本。
3. 在 worker 内调用固定版本的 `finetune/tag_images_by_wd14_tagger.py`，使用 ONNX 模式。
4. 优先对接截图中的 `SmilingWolf/wd-v1-4-convnext-tagger-v2` 资源；登记实际模型路径和标签表。
5. 从 batch 1、阈值 0.35 起步，将参数保留在打标任务快照中。
6. 自动标签先提供预览；用户可以修改、去除不需要的标签和添加触发词。
7. 保存图片同名 `.txt`，已有人工标签默认保留；批量覆盖作为明确操作提供。

GPU 打标验收必须创建真实 ONNX session 并运行图片，不能仅检查环境列出的 CUDA provider。记录实际 provider 与结果，避免误把 CPU 打标报告为 GPU 打标。[WD14 脚本](https://github.com/kohya-ss/sd-scripts/blob/v0.12.0/finetune/tag_images_by_wd14_tagger.py)

### 7.2 RTX 4060 Laptop 起步训练配置

以下为待测的保守起点，不代表已经测得的显存保证。

| 参数 | 首轮设置 | 说明 |
| --- | --- | --- |
| 基础模型 | SD1.5 | 与作业资源和后续推理一致 |
| 分辨率 | 512 × 512 | 分桶后另测峰值显存 |
| batch size | 1 | 控制显存 |
| gradient accumulation | 1 | 需要增大有效 batch 时再调整 |
| mixed precision | fp16 | 首轮采用成熟配置 |
| LoRA module | `networks.lora` | 标准 LoRA |
| rank / alpha | 16 / 16 | 可在短训后调整 |
| 训练范围 | 首轮仅 UNet | 先减少显存与调参变量 |
| learning rate | `1e-4` | 作为可调整起点 |
| optimizer | AdamW8bit | bitsandbytes CUDA 导入与运算必须先通过 |
| gradient checkpointing | 开启 | 减少训练显存 |
| latent cache | 开启；优先磁盘缓存 | 使用缓存时校验增强配置的兼容性 |
| attention | PyTorch SDPA | 首轮减少额外 attention 依赖 |
| data loader workers | 0 | 降低本机内存压力 |
| 训练内采样 | 首轮关闭 | 训练结束后独立执行推理 |
| 短训规模 | 4–8 张图、20–50 步 | 验证链路、loss 和模型文件 |

正式训练步数根据图片数量、重复次数和对比结果确定，界面提供可调预设。短训用来验证链路；训练效果必须另通过实际图像对比评估，不能由 loss 或文件生成推断。

优先使用结构化 TOML 数据集与训练配置，避免用户必须按文件夹名手动编码重复次数。配置中明确 repeats、batch、gradient accumulation 和 steps；步数与 epoch 换算仅作为估算，最终以训练器读取的数据和步数为准。

启用 latent cache 时校验随机裁切、颜色增强等选项的兼容性；不将 SDXL 专用的缓存选项直接用于 SD1.5。[LoRA 训练指南](https://github.com/kohya-ss/sd-scripts/blob/v0.12.0/docs/train_network.md)

### 7.3 训练适配层与真实可视化

平台将经过校验的配置写入 `/data/runs/{job_id}/`，调用固定版本训练脚本，并保存完整 stdout/stderr 与退出码。上游代码保持固定，应用适配层负责路径、参数和任务管理。

启用 TensorBoard 日志，增量读取 event 文件作为曲线数据。具体 scalar 名称以固定版本实际输出为准，例如当前损失、平均损失和 UNet 学习率；不依赖抓取终端进度条来生成损失曲线。

worker 区分加载模型、缓存 latent、训练、保存等阶段，推送当前步数、总步数、已用时间与估计剩余时间。GPU 指标独立采集；某项指标在 WSL 不可用时显示未知，不填写虚构值。

单个任务目录计划如下：

```text
/data/runs/{job_id}/
├─ job.json
├─ dataset.toml
├─ training.toml
├─ environment.json
├─ manifest.json
├─ logs/
├─ tensorboard/
├─ checkpoints/
├─ state/
└─ artifacts/
```

成功状态同时要求：训练进程正常退出、目标文件实际存在、权重结构能读取。产物记录基础模型、数据集版本、配置和环境，供后续推理选择。

### 7.4 SD + LoRA 推理

首版通过适配层调用同一版本的 `gen_img.py`，复用训练依赖。基础模型与训练所用权重保持一致，逐任务加载，任务结束退出子进程。[sd-scripts 图像生成文档](https://github.com/kohya-ss/sd-scripts/blob/v0.12.0/docs/gen_img_README.md)

界面提供：基础模型、LoRA、LoRA 强度、正向与负向提示词、seed、采样器、步数、CFG、输出尺寸。首轮使用 512 分辨率、单张生成。

对比任务使用相同提示词、seed、采样器、步数和 CFG，分别生成基础模型与加载 LoRA 的结果。保存图片与实际生成参数，并展示模型加载是否成功。对照结果用于效果判断，不承诺不同环境逐像素一致。

## 8. 前端页面与交互

采用中文桌面工作台：左侧导航，顶部项目与 GPU 状态，中间主要操作区。浅色中性背景，蓝色主操作，统一间距和 SVG 图标；状态同时包含文字，避免只依赖颜色。

| 页面 | 核心内容 | 关键交互 |
| --- | --- | --- |
| 总览 | GPU、当前任务、数据集和最近产物 | 明确提示下一步操作 |
| 数据集 | 缩略图、筛选、质量问题、标签编辑 | 分页或虚拟列表；编辑状态可见；批量打标在详情内发起 |
| 训练配置 | 模型与数据、基础参数、输出、高级参数 | 常用参数先展示；高级项折叠；每项有中文说明与即时错误 |
| 任务中心 | 排队、运行、失败、成功与历史任务 | 提交后立即显示排队；取消后显示停止中 |
| 任务详情 | 训练阶段、步数、损失、日志、产物 | 刷新后恢复；日志可展开；失败提供具体原因 |
| 推理测试 | 提示词、参数、生成图和历史 | 支持固定 seed 的基础模型 / LoRA 对比 |
| 模型与设置 | 模型登记、存储路径、环境检查 | 同时显示宿主和容器路径，便于定位文件 |

表单保留草稿；启动训练前展示数据集版本、模型和参数摘要。路径字段优先通过已登记资源选择，减少手输路径错误。训练进行时，图片浏览和标签编辑仍可使用；新模型任务显示排队。

采用可见标签、键盘焦点、正常文本对比度和清晰错误反馈。大图按需加载，缩略图分页；曲线数据按训练步数聚合。较小屏幕允许导航收起和表单分组，避免整体页面横向溢出。

在前端实施阶段于容器内生成并保存设计规则，后续组件遵循同一套颜色、间距、表单和任务状态规范。

## 9. 实施顺序与阶段交付

| 阶段 | 任务与方法 | 阶段交付 | 通过条件 |
| --- | --- | --- | --- |
| P0：初始化 | 建立源码、Docker、配置、数据与文档结构；记录资源来源 | 项目骨架、命名和配置约定 | 路径明确，真实资源缺口有记录 |
| P1：Docker / CUDA | 启动引擎，构建最小 GPU 环境，检查依赖、显卡和 CUDA 张量运算 | Compose、Dockerfile、环境报告和锁定依赖 | 容器内真实 CUDA 运算成功，依赖无冲突 |
| P2：模型与手工链路 | 容器内准备模型，完成少量打标、短训练、LoRA 推理 | 模型清单、标签、LoRA、测试图与日志 | 新 LoRA 可加载，loss 有限，推理图有效 |
| P3：后端 | 数据集、模型、配置、队列、取消、事件、文件查询 | API、worker、数据记录和任务适配层 | 串行 GPU 任务可执行、取消和恢复查看 |
| P4：前端 | 按页面设计接入真实 API，实现完整流程 | 可用中文工作台 | 网页完成导入至训练产物查看 |
| P5：推理与集成 | 接入网页推理，处理排队、重连、中断和错误 | 基础模型 / LoRA 对比流程 | 固定条件下生成并保存对比图 |
| P6：验收交付 | 容器测试、重建验证、文档和可复现演示 | 用户说明、环境报告、验收报告 | 六项作业要求都有实际证据 |

P2 是后端与前端开发的关键前置验证。先证明这台机器能在容器内完成训练和推理，再封装平台功能；每个阶段通过后更新环境与验收记录。

## 10. 验证方式与交付标准

### 10.1 环境和模型计算

- Docker 引擎和 Linux 容器正常运行。
- worker 内 `torch.cuda.is_available()` 为 true，设备为本机 RTX 4060 Laptop。
- 在 CUDA 上执行真实张量运算并同步完成，不只检查显卡名称。
- WD14 运行一张真实图片，并确认实际使用 CUDA provider。
- 短训练生成可读 LoRA，日志中损失为有限值。
- 同一运行环境成功加载该 LoRA 并生成有效图片。
- 记录实际峰值显存，必要时调整预设，保留调整原因。

### 10.2 业务和界面

- 导入、预览、标签修订、参数校验和提交训练能在网页完成。
- 提交打标、训练和推理时，GPU 串行执行，API 和页面保持响应。
- 浏览器刷新或 SSE 重连后能恢复任务状态和曲线。
- 取消任务后无残留计算子进程，下一个任务可以运行。
- worker 重启后，中断任务有正确标识，排队任务和历史产物保留。
- 容器重建后，数据集、模型、数据库与结果文件仍可读取。
- 缺失模型、无效路径、空间不足和 CUDA 不可用有明确错误信息。
- 使用实际产物完成一次基础模型与 LoRA 的对比演示。

### 10.3 项目测试

对参数校验、路径边界、任务原子领取、取消与中断处理、真实脚本适配进行必要后端测试；前端完成类型检查、构建及主要流程验证。测试均在 Docker 内运行。GPU 验收需要真实模型与真实数据，模拟任务不能替代最终验收。

### 10.4 最终文件

- `compose.yaml`、开发 override、Dockerfile 与启动配置。
- 前端、API、worker 源码及依赖锁定文件。
- 示例配置、低显存预设和模型资源清单。
- 环境报告：实际版本、镜像 digest、上游 commit、路径和 GPU 验证。
- 验收报告：运行结果、截图、实际产物位置和剩余限制。
- 用户说明：启动、导入、打标、训练、推理、备份和排错。

大模型文件、训练图片及 CUDA 镜像按配置获取或挂载，不混入源码压缩包。数据库命名卷提供备份入口；清理训练文件时保留用户选定的产物和恢复所需 state，不自动清理其他项目的 Docker 数据。

## 11. 当前状态与下一步

### 已完成

- 明确截图中六项功能与参考开发操作的区别。
- 检查本机 GPU、Docker、WSL、内存和 D 盘空间。
- 确定三服务、单 GPU 串行执行、统一路径和持久化方案。
- 形成训练环境候选基线、前端方案、接口边界和分阶段验收。
- 建立 React/Vite 中文工作台、FastAPI API、SQLite WAL 状态和单 GPU worker。
- 建立 Docker Compose、开发/交付镜像、路径挂载、模型准备脚本和环境报告。
- 前端 production 构建通过，Python 源码语法检查通过。
- Docker Desktop WSL2 数据盘确认位于 `D:\docker`，项目源码、模型、数据集、训练产物和 SD 配置均位于 `D:\LoRA`。
- worker 容器已完成 RTX 4060 CUDA 张量运算，WD14 已用 `CUDAExecutionProvider` 实际打标。
- SD1.5 checkpoint、独立 ComfyUI 服务和共享 LoRA 目录已配置；ComfyUI 可发现基础模型与训练产物。
- 已完成 2 步真实 FP16 LoRA 短训并校验 safetensors 结构。

### 尚待实施验证

- 将真实打标、训练和推理接入 API/worker 的持久化任务队列。
- 用生成的 LoRA 完成同 seed 的基础模型 / LoRA 图像对比并保存输出。
- 完成网页端数据集导入、标签修改、训练提交、事件流和产物查看。
- 补充取消/重启恢复、磁盘空间检查和正式训练显存预设。

后续从 **P3/P4 → P5** 继续：把已经验证的真实脚本链路接入作业队列和网页，再完成固定 seed 的基础模型 / LoRA 对比。正式训练步数与显存预设需根据实际数据集另行确认。

## 满洲窗专用存储例外（2026-10-08 用户指定）

新实验根目录为 E:\LoRA-Manzhou。Docker 挂载 /data/manzhou 对应该根目录；/data/runs/manzhou 对应其 runs；/data/outputs/lora-platform/manzhou 对应其 outputs。此为同一 E 盘目录的别名，不能复制成 D 盘的第二套数据。图片、标签、训练副本、潜变量、任务日志、LoRA 与推理图片须写到 E 盘。平台源码、共享 SQLite 索引、既有共享模型及 Docker 全局磁盘保留原位置。

每一步保存真实截图，并在 E:\LoRA-Manzhou\reports\experiment-record.md 与 logs/experiment.jsonl 记录时间、输入、操作、结果和截图路径。全局 changes.log 同步记录。历史步骤补拍必须注明，不得伪称原始执行截图；失败与重试照常保留，凭据不得截图或写日志。
