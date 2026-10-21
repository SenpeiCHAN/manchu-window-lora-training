# Docker 服务与端口

| 容器 | 镜像 | 端口映射 | 持久化内容 |
| --- | --- | --- | --- |
| `lora-web` | `lora-platform-web:latest` | `127.0.0.1:8080->80` | 无本地卷 |
| `lora-api` | `lora-platform-api:latest` | 无 | `D:\LoRA\data`, `D:\LoRA\data\state`, `E:\LoRA-Manzhou` |
| `lora-gpu-worker` | `lora-platform-worker:latest` | 无 | LoRA 数据、缓存、训练运行目录 |
| `lora-stable-diffusion` | `lora-platform-stable-diffusion:latest` | `127.0.0.1:8188->8188` | 模型、输入、输出、ComfyUI 用户目录 |
| `paperburner-app` | `paper-burner-x-app:latest` | `127.0.0.1:3300->3000` | 上传卷和项目源码挂载 |
| `paperburner-db` | `postgres:16-alpine` | `0.0.0.0:5433->5432` | `paper-burner-x_postgres_data` |
| `xiaozhi-mcphub` | `huangjunsen/xiaozhi-mcphub:latest` | `0.0.0.0:3000->3000` | `xiaozhi-mcphub-main_appdata` |
| `pgvector` | `pgvector/pgvector:pg16` | `127.0.0.1:5432->5432` | `xiaozhi-mcphub-main_pgdata` |

恢复时应先创建数据库服务，再启动应用服务；端口映射保持不变。
