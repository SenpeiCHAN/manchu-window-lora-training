# 备份范围

## 需要备份

- LoRA 训练代码、前后端代码、Docker Compose、Dockerfile 和脚本
- `D:\LoRA\data\models`
- `E:\LoRA-Manzhou\datasets`
- `E:\LoRA-Manzhou\runs`
- `E:\LoRA-Manzhou\reports` 和训练输出
- LoRA SQLite 数据库
- paperburner PostgreSQL 数据库
- xiaozhi/pgvector PostgreSQL 数据库

## 不进入公开 Git 历史

- `.env` 和真实密钥
- 密码文件、API Key、密码哈希
- Docker 构建缓存（可重建，当前约 22.69 GiB）
- `node_modules`、npm 缓存、临时缓存和容器日志

大文件按小于 2 GiB 的分卷归档，上传后记录 SHA-256 和原始路径。只有确认远端文件可下载、哈希一致后，才执行本地清理。
