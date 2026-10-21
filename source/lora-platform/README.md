# LoRA 本地工作台

项目目录：`D:\LoRA`。日常使用双击桌面 **启动 LoRA 面板**，访问 <http://localhost:8080/>。

## 从哪里开始

| 内容 | 文档 |
| --- | --- |
| 日常启动、独立 SD、日志位置 | [启动说明](docs/desktop-launcher.md) |
| 2026-10-08 架构整理、主题、SSH、验收 | [最新整理报告](docs/architecture-and-ui-20261008.md) |
| 项目原理、训练方案与路径 | [技术方案](docs/technical-plan.md) |
| 模型准备 | [模型说明](docs/huggingface-models.md) |

## 目录职责

| 目录或文件 | 职责 |
| --- | --- |
| `compose.yaml` | 默认生产运行：静态前端、API、GPU worker、可选 SD |
| `compose.dev.yaml` | 开发覆盖配置；不会被桌面启动器使用 |
| `compose.prod.yaml`、`compose.real.yaml` | 保留兼容旧命令；生产与真实执行已是默认配置 |
| `docker/` | 镜像构建与网页代理配置 |
| `frontend/src/` | 现有七页；公共接口在 lib，SSH 和目录弹窗在 components，主题在 theme.ts |
| `frontend/public/fonts/` | 本地阿里巴巴普惠体 2.0 字体与来源清单 |
| `backend/api/` | 本地 API；remote.py 是独立 SSH 扩展边界 |
| `backend/worker/` | 真实 GPU 任务执行 |
| `backend/shared/` | 共享数据与配置处理 |
| `data/models/` | 基础模型与打标模型 |
| `data/datasets/` | 图片与标签 |
| `data/runs/` | 训练输出、任务配置与日志 |
| `data/outputs/` | 推理结果 |
| `data/state/` | 数据库及 SSH 非敏感连接配置 |
| `data/cache/` | Hugging Face / Torch 项目缓存 |
| `data/dev/` | 开发模式依赖，日常运行不需要 |
| `data/backups/` | 数据恢复备份 |
| `stable-diffusion/` | 独立 ComfyUI 用户配置与输入 |
| `scripts/` | 桌面启动、模型准备、字体获取与迁移验证工具 |
| `logs/` | 每一步变更记录、构建与验证证据 |
| `docs/` | 说明与验收截图 |

Docker 全局镜像磁盘沿用 Docker Desktop 的 `D:\docker` 配置。项目的源码、数据、缓存、配置和结果集中在 `D:\LoRA`。镜像本身由 Docker 引擎统一管理。

## 维护者操作

以下命令仅用于维护，日常使用桌面入口即可。

```powershell
# 构建并运行日常版本
docker compose build web api
docker compose --profile sd up -d --no-build

# SD 可独立于工作台运行
docker compose --profile sd up -d --no-build stable-diffusion

# 开发模式，使用独立开发镜像标签
docker compose -f compose.yaml -f compose.dev.yaml up -d --build web api

# 恢复日常模式
docker compose --profile sd up -d --no-build
```

开发模式使用同一组容器，不与生产模式并行运行。生产前端修改后需要重新构建 web；仅刷新浏览器不会部署源码。
