# 满洲窗 LoRA 训练

本项目整理自 Docker Desktop 中的满洲窗 LoRA 训练环境。

## 内容

- `docker/`：Docker 服务、镜像、端口和卷清单
- `databases/`：脱敏后的数据库导出；密码、API Key、请求头和 `.env` 不公开
- `docs/`：备份、恢复和大文件分卷说明
- 大模型、数据集、训练运行结果：作为分卷归档上传到外部网盘，并在这里保存校验信息和恢复顺序

## 端口映射

| 服务 | 主机端口 | 容器端口 |
| --- | ---: | ---: |
| lora-web | 8080 | 80 |
| stable-diffusion | 8188 | 8188 |
| paperburner-app | 3300 | 3000 |
| paperburner-db | 5433 | 5432 |
| xiaozhi-mcphub | 3000 | 3000 |
| pgvector | 5432 | 5432 |

## 安全说明

公开仓库不包含真实 `.env`、密码、API Key、密码哈希或数据库连接密钥。需要本地恢复时，请根据 `.env.example` 手动填写凭据。
