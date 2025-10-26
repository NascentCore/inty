# 舒适UI

## Pr相对架构

-worker-comfyui 端点
- 包含所有模型、loras 和其他数据项的附加网络卷
- 使用 cpu pod 下载模型以纠正网络卷上的路径

确认：

- 使用带有 [workflow_sd3.json](https://github.com/runpod-workers/worker-comfyui/blob/main/test_resources/workflows/workflow_sd3.json) 的默认模板
- 创建了 [library_night_seducing_api.json](./experimental/comfyui/library_night_sepressive_api.json)
  基于 [civitai](https://civitai.com/images/86482829)
- Worker 镜像无法在 pod 上运行
- 在 runpod 上启动 comfyui pod- 将网络卷附加到`/runpod-volume`（按工人形象要求）
- 打开comfyui webui，打开终端，下载额外的模型
  - 根据工作流程的要求
  - 在civitai上打开工作流程，找到模型下载链接，然后使用`curl`:

    ```bash
    cd /workspace/comfyui/models/checkpoints
    # Need civitai api key to download certain models
    curl --remote-name --remote-header-name --location \
        "https://civitai.com/api/download/models/1761560?type=Model&format=SafeTensor&size=pruned&fp=fp16&Token=<your-token>"
    ```[使用curl下载](https://stackoverflow.com/questions/6881034/curl-to-grab-remote-filename-after-following-location)

## 演示

- [runpod_serverless_endpoint_comfyui_sd3](./runpod_serverless_endpoint_comfyui_sd3.py):
  显示如何向 runpod comfyui 无服务器端点发出请求。
  它将输出图像写入本地 png 文件。

## 工作流程示例

- [civitai 链接](https://civitai.com/images/86482829)
  - [工作流程.json](工作流程.json)
  - [工作流程_高级.json](工作流程_高级.json)

## 指针

- [Runpod工作人员comfyui测试](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/development.md#local-api)
- ComfyUI 管理器
  - 配置文件路径：ComfyUI/user/default/ComfyUI-Manager/config.ini
- [维基](https://comfyui-wiki.com/en)- 安装comfyui，有多个选项，使用`comfy-cli`，这似乎是最可靠的```bash
  mkdir comfyui # Or another dir as the parent dir to install comfyui
  cd comfyui
  python3 -m venv comfy-env
  source comfy-env/bin/activate
  pip install comfy-cli
  comfy install # Install comfyui and comfyui-manager
  ```- [base_api_example.py](./basic_api_example.py) 展示缓存。
  同样的 prompt 将立即返回保存的图像。

## 关键概念

- **节点：** 作为工作流程构建块的各个功能（例如，加载检查点、KSampler）。
- **工作流程：** 连接节点的图形或流程图，定义整个图像生成 process。
- **Procedural：** process 被分解为一系列视觉上的、连续的步骤。
- **模块化：** 节点可以轻松换入和换出以更改管道。- **数据流：**信息（例如，潜在图像、文本 prompts）从一个节点的输出传输到另一个节点的输入。
- **执行缓存：** 仅重新运行输入或参数发生更改的节点，从而节省时间和资源。
- **定制：** 通过社区制作的定制节点添加新功能的能力。
- **PNG 格式的工作流程：** 整个工作流程元数据直接保存在生成​​的图像文件中，以便轻松共享。

## 从 ComfyUI 保存图像

### 自动保存- 图像自动保存到`ComfyUI/output/`目录

- 文件名包括时间戳和工作流程信息
- 参数嵌入 PNG 元数据中

### 手动保存

- 右键单击​​ ComfyUI 中生成的图像

- 选择“保存图像”
- 选择您想要的位置

## 在Automatic1111中使用图像

ComfyUI 和Automatic1111 使用不同的参数格式。使用附带的转换器脚本：

＃＃＃ 安装```bash
pip install -r requirements.txt
```### 单图像转换```bash
python comfyui_to_automatic1111.py path/to/comfyui_image.png
```### 批量转换```bash
python comfyui_to_automatic1111.py --batch ComfyUI/output/
```### 转换器的作用

1. **从PNG元数据中提取** ComfyUI参数
2. **将**它们转换为Automatic1111格式
3. **保存**具有A1111兼容参数的新图像
4.**创建**`automatic1111_ready/`包含转换后的图像的目录

### 在 A1111 中使用转换后的图像

1.复制图像来自`automatic1111_ready/`发送至您的 A1111`outputs/`目录
2.打开A1111并转到“PNG信息”选项卡
3.加载任何转换后的图像以查看参数
4、点击“发送到txt2img”或“发送到img2img”即可使用参数

＃＃ 参考

1.[关键概念](https://g.co/gemini/share/f5ea8079380c)