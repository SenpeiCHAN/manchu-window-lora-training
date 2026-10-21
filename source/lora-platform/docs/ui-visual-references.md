# LoRA 面板视觉参考

整理日期：2026-10-07。用途：供用户选择改版方向，尚未修改前端。

## A. Linear：简洁工作台

参考重点：统一灰阶、清晰字号层级、低干扰导航、列表与详情分栏。适合数据集列表、参数表单和模型管理。可以采用浅色或深色主题。

[官方界面设计说明](https://linear.app/now/how-we-redesigned-the-linear-ui)

![Linear 界面参考](https://webassets.linear.app/images/ornj730p/production/23839a6bacba4a7617728dada3d37a40dc3584aa-2352x1380.png?auto=format&dpr=2&q=95)

## B. InvokeAI：专业图像工作区

参考重点：深色背景、参数侧栏、中央大图、图片库与工具分区。适合数据集标注与 SD + LoRA 推理对比。我们的版本应精简控件数量，让常用操作更容易找到。

[官方页面](https://invoke.ai/)

![InvokeAI 界面参考](https://invoke.ai/_astro/invoke-webui-canvas.C95hAGI9_Z1aQRGy.webp)

## C. Krea：作品优先的创作界面

参考重点：大面积图片、集中提示词输入、少量核心按钮。适合结果浏览、LoRA 作品展示和推理页；训练参数需要使用独立分组面板。

[官方产品页面](https://www.krea.ai/features/ai-image-generator)

![Krea 界面截图](https://kive.ai/images/learn/best-ai-image-generators/krea.jpeg)

截图来源：[Kive 的产品参考文章](https://kive.ai/learn/15-best-ai-image-generators)。截图版本可能与当前产品不同。

## D. Weights & Biases：训练监控

参考重点：训练任务列表、指标曲线、参数对照和系统资源。适合任务中心；不需要把所有页面都做成密集仪表盘。曲线应在真实指标采集完成后展示。

[官方实验追踪页面](https://site.wandb.ai/experiment-tracking/)

![训练指标界面参考](https://user-images.githubusercontent.com/4751805/227524828-3b8a9a39-c15c-459e-bfa9-ca955f1d71be.png)

截图来源：[W&B 官方仓库 issue](https://github.com/wandb/wandb/issues/5174)。

## 选择建议

| 方向 | 适合的页面 | 视觉特点 |
| --- | --- | --- |
| A | 数据集、参数配置、模型与设置 | 克制、清楚、统一 |
| B | 图片标注、推理对比 | 专业、分栏、操作集中 |
| C | 结果图库、推理页 | 图片突出、简洁、有创作感 |
| D | 任务与训练监控 | 指标明确、便于比较 |

建议组合：A 的基础框架 + C 的图片展示 + D 的训练监控。若希望整个产品像本地图像编辑软件，可优先选 B。
