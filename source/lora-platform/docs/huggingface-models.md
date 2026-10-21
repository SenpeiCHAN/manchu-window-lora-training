# Hugging Face 资源清单

首版固定在 Stable Diffusion 1.5 族，原因是 RTX 4060 Laptop 约 8GB 显存可以先用 512 分辨率完成短训和推理验证。SDXL 不作为第一条验收链路。

## 建议资源

| 资源 | Hugging Face 仓库 | 用途 | 计划路径 |
| --- | --- | --- | --- |
| SD 1.5 Diffusers | [stable-diffusion-v1-5/stable-diffusion-v1-5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) | 基础模型与离线推理 | `/data/models/sd15` |
| WD14 ConvNeXtV2 | [SmilingWolf/wd-v1-4-convnextv2-tagger-v2](https://huggingface.co/SmilingWolf/wd-v1-4-convnextv2-tagger-v2) | 图片自动打标 ONNX 模型 | `/data/models/wd14` |

实际下载由 [scripts/prepare_models.py](../scripts/prepare_models.py) 在 worker 容器内执行。生产环境必须把 `--revision` 从 `main` 改成已核对的 commit SHA，并将下载清单保存到 `/data/models/manifest.json`。

## 空间与许可检查

SD 1.5 仓库包含多个推理所需文件，下载前要用 `--allow-patterns` 和磁盘检查控制副本。当前 D 盘检查时约剩 54.3GB，下载完整模型前要确认 Docker Desktop 镜像磁盘仍有足够空间。

模型卡显示 SD 1.5 使用 CreativeML OpenRAIL-M 许可；下载、使用和交付模型时遵循仓库的模型卡和许可条款。WD14 仓库用于标签预测，使用前记录其模型卡和标签表版本。

## 下载与验证顺序

1. Docker GPU 容器启动后，先运行 `python scripts/prepare_models.py --model wd14 --revision <已核对 SHA>`，验证 ONNX CUDA provider 和一张真实图片。
2. 再下载 SD 1.5 到 `/data/models/sd15`，检查配置、tokenizer、VAE 和权重是否完整。
3. 先运行离线推理 smoke test，再运行 4–8 张图、20–50 步的短训练。
4. 将 manifest、实际 revision、文件 hash、CUDA 版本和显存峰值写入环境报告。

不要把 HF token 写入源码、Compose 文件、任务日志或前端。若模型仓库要求登录，应在 worker 容器运行时通过环境变量或 Docker secret 提供 token；公开仓库不需要 token。

## 当前状态

模型资源尚未下载。原因是当前 Docker Desktop 后端启动被旧的 `dockerInference` / `userAnalyticsOtlpHttp.sock` 系统 socket 阻塞；项目代码已准备好下载入口，待 Docker 引擎恢复后再在容器内下载和验证。
