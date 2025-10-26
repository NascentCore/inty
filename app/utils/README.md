# utils

[Cropping avatar from image](crop_avatar.py)

<img width="2710" height="1212" alt="image" src="https://github.com/user-attachments/assets/558a06e5-1fad-482a-8840-3d5dcc76babf" />

<img width="2854" height="1164" alt="image" src="https://github.com/user-attachments/assets/8d7c182e-bbe2-4bcb-80e5-20063eee5f19" />

要求生图时对用户生图需要增强提示词，正面照片，降低人脸检测难度

## Cursor Summary

- 目录用途: 提供与第三方/多模态能力的适配与通用实用工具。
- 关键文件:
  - `openai_client.py`/`gemini.py`/`langchain.py`: 多家模型与工具生态的封装，供服务层统一调用。
  - `image.py`/`image_upload.py`: 图片处理与上传。
  - `crop_avatar.py`: 头像裁剪相关脚本与可视化流程示例。
  - `utils/cascades`: OpenCV 模型资源引用。
- 说明: 该目录不承载业务流程，主要提供面向服务层的基础能力模块。
