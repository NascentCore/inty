# RunPod 运行 Z-Image 方案

## 1. 概述

- **Z-Image**：Tongyi-MAI 的 6B 参数图像生成模型，[GitHub](https://github.com/Tongyi-MAI/Z-Image)。Z-Image-Turbo 约 8 NFE、适合 16GB VRAM，支持中英文与写实风格。
- **RunPod**：GPU 云平台，支持 [Pods](https://docs.runpod.io/pods/overview)（按分钟计费、长驻）与 [Serverless](https://docs.runpod.io/serverless/overview)（按秒计费、自动扩缩）。
- **方案选择**：本仓库已有 [experimental/comfyui](../experimental/comfyui/) 的 RunPod ComfyUI 实践（SD3/serverless worker）；Z-Image 在 RunPod 上推荐两条路径：
  - **Pod + ComfyUI**：与 RunPod 官方 [Generate images with ComfyUI](https://docs.runpod.io/tutorials/pods/comfyui) 一致，适合开发/调试与持久化模型（可配合 Network Volume）。
  - **Serverless ComfyUI**：与现有 `runpod_serverless_endpoint_worker_comfyui.py` 一致，需 worker 镜像支持 Z-Image 或自建 worker；适合生产 API。

文档以 **Pod + ComfyUI + Z-Image** 为主（步骤完整、可复现），Serverless 仅作可选延伸说明（见文末方案 B）。

## 2. 前置条件

- RunPod 账号与余额（官方建议至少 $10）。
- 了解 ComfyUI 基本概念（本仓库 [experimental/comfyui/README.md](../experimental/comfyui/README.md) 有节点/工作流等说明）。

## 3. 方案 A：RunPod Pod + ComfyUI + Z-Image-Turbo

### 3.1 创建 ComfyUI Pod

参考 [RunPod 教程](https://docs.runpod.io/tutorials/pods/comfyui)：

- **模板**：标准 GPU 选 [ComfyUI](https://console.runpod.io/hub/template/comfyui)；Blackwell（RTX 5090/B200）选 [ComfyUI Blackwell Edition](https://console.runpod.io/hub/template/comfyui-blackwell-edition-5090-b200)。
- **GPU 选型（目标：10 秒内完成高质量 1024×1024 生图）**：根据公开基准，Z-Image-Turbo 在 1024×1024 下的典型耗时约为：
  - **H800 / H100**：亚秒级（约 1–1.4 秒）
  - **RTX A6000 48GB**：约 4 秒
  - **L40（48GB）**：推理优化，预计约 3–6 秒；RunPod 约 $0.69–0.99/hr，性价比高
  - **A100 PCIe**：预计约 2–5 秒；RunPod 约 $1.39/hr
  - **RTX 4090（24GB）**：预计约 5–10 秒，16GB+ 显存可完整跑满质量
  - **8GB 消费卡（如 RTX 3070）**：约 13–30 秒，不满足 10 秒内目标

  建议：若要求**至少 10 秒内高质量出图**，在 RunPod 上优先选 **L40**、**RTX 4090**、**A100 PCIe** 或 **RTX A6000**；显存建议 ≥16GB（官方推荐 16GB，8GB 可跑但速度较慢）。
- **端口**：8188（ComfyUI HTTP）。
- **存储**：默认或增加磁盘；若需持久化模型，挂载 [Network Volume](https://docs.runpod.io/storage/network-volumes)（本仓库实践为挂载到 `/runpod-volume`，ComfyUI 模板路径以 RunPod 文档为准，一般为 `/workspace/.../ComfyUI/models`）。

部署后等待 Pod 初始化（首次可能约 30 分钟），在 RunPod 控制台找到该 Pod，点击 **Connect** → **Connect to HTTP Service [Port 8188]** 打开 ComfyUI 界面（URL 形如 `https://[POD_ID]-8188.proxy.runpod.net`）。

### 3.2 安装 Z-Image-Turbo 模型

使用 [ComfyUI 官方 Z-Image-Turbo 文档](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo) 中的模型与路径，将以下三个文件放到对应目录（RunPod 模板下一般为 `/workspace/madapps/ComfyUI/models`，以控制台实际路径为准）：

| 文件 | 目录 | 下载链接 |
| ------ | ------ | ---------- |
| `qwen_3_4b.safetensors` | `ComfyUI/models/text_encoders/` | [Hugging Face](https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors) |
| `z_image_turbo_bf16.safetensors` | `ComfyUI/models/diffusion_models/` | [Hugging Face](https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors) |
| `ae.safetensors` | `ComfyUI/models/vae/` | [Hugging Face](https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors) |

在 Pod 内可用 `curl`/`wget` 或 ComfyUI Manager 下载；大文件建议用 Network Volume 预先下载或 [RunPod CLI](https://docs.runpod.io/runpodctl/overview) 上传到 Pod 的 `ComfyUI/models` 对应子目录。

示例（在 Pod 终端中，按实际 `ComfyUI` 根路径替换 `COMFYUI_ROOT`）：

```bash
COMFYUI_ROOT=/workspace/madapps/ComfyUI
cd $COMFYUI_ROOT/models/text_encoders
curl -L -o qwen_3_4b.safetensors "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors"
cd $COMFYUI_ROOT/models/diffusion_models
curl -L -o z_image_turbo_bf16.safetensors "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors"
cd $COMFYUI_ROOT/models/vae
curl -L -o ae.safetensors "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors"
```

### 3.3 加载 Z-Image-Turbo 工作流

- 从 ComfyUI 官方获取 workflow JSON：[image_z_image_turbo.json](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_z_image_turbo.json)。
- 在 ComfyUI Web UI 中：**Workflow** → **Open** → 选择该 JSON 文件。
- 若模板浏览器支持，可在 **Image** → **Z-Image-Turbo** 下直接选模板（需 ComfyUI 已更新至含 Z-Image 模板的版本）。

### 3.4 生成图像

- 在工作流中找到 **CLIP Text Encode (Prompt)**（或对应 prompt 节点），输入提示词。
- 点击 **Run**（或 Ctrl+Enter）开始生成。
- Z-Image-Turbo 建议：约 8–9 steps，CFG 低（1.0–2.0）；分辨率等按 workflow 默认或 [官方示例](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)。

首次生成会加载模型，耗时较长；后续会明显加快。

### 3.5 可选：Z-Image-Turbo Fun Union ControlNet

若需基于参考图的结构引导生成，可增加 ControlNet：

- 下载 [Z-Image-Turbo-Fun-Controlnet-Union.safetensors](https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors) 至 `ComfyUI/models/model_patches/`。
- 使用 ControlNet 专用 workflow：[image_z_image_turbo_fun_union_controlnet.json](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_z_image_turbo_fun_union_controlnet.json)。

## 4. 参考链接汇总

- [Tongyi-MAI/Z-Image](https://github.com/Tongyi-MAI/Z-Image)（模型与 PyTorch/Diffusers 用法）
- [RunPod 文档概览](https://docs.runpod.io/overview)
- [RunPod：Generate images with ComfyUI (Pods)](https://docs.runpod.io/tutorials/pods/comfyui)
- [RunPod：Deploy ComfyUI with Serverless](https://docs.runpod.io/tutorials/serverless/comfyui)
- [ComfyUI：Z-Image-Turbo workflow](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)（模型路径 + workflow 下载）
- [Reddit：realistic portrait using zimage workflow](https://www.reddit.com/r/comfyui/comments/1pim8ti/realistic_portrait_using_zimage_workflow_on/)（社区示例）
- Z-Image-Turbo 推理速度基准：H800 亚秒级、A6000 约 4 秒、8GB 卡约 13–30 秒（见 [zimageturbo.org](https://zimageturbo.org/)、[emergentmind](https://www.emergentmind.com/topics/z-image-turbo)、社区评测）
- 本仓库：[experimental/comfyui/README.md](../experimental/comfyui/README.md)、[experimental/runpod/README.md](../experimental/runpod/README.md)

## 5. 与本仓库的衔接

当前 Inty 后端使用 **fal.ai** 的 `fal-ai/z-image/turbo`（见 `app/core/config.py`、`app/external_services/fal.py`）。若未来改为自建 RunPod 端点，可将图文生成从 fal 切换到 RunPod ComfyUI Serverless endpoint，调用方式参考 [experimental/comfyui/runpod_serverless_endpoint_worker_comfyui.py](../experimental/comfyui/runpod_serverless_endpoint_worker_comfyui.py)。

## 6. 方案 B（可选）：Serverless ComfyUI + Z-Image

使用 RunPod Serverless 的 ComfyUI worker，通过 API 提交 workflow 并取回图片。

- **调用方式**：与现有 SD3 serverless 调用方式相同，仅将 workflow 换为 Z-Image-Turbo 的 JSON（如 [image_z_image_turbo.json](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_z_image_turbo.json)），并确保 endpoint 镜像或挂载卷中有上述三个模型（`qwen_3_4b.safetensors`、`z_image_turbo_bf16.safetensors`、`ae.safetensors`）。
- **参考实现**：本仓库 [experimental/comfyui/runpod_serverless_endpoint_worker_comfyui.py](../experimental/comfyui/runpod_serverless_endpoint_worker_comfyui.py) 传入 `workflow` JSON、用 `endpoint.run_sync()` 取结果。
- **前提**：需使用已包含 Z-Image 模型的 worker 镜像，或自建镜像/在镜像内放置上述三个模型；Serverless 使用 Network Volume 时路径需与 worker 约定一致（如 [experimental/comfyui/README.md](../experimental/comfyui/README.md) 中的 `/runpod-volume`）。镜像构建与 endpoint 部署细节不在此文档展开。

---

CREATED_BY_AGENT
