# api

## 规范

- 所有接口的响应都遵循统一的格式：
  - code: 状态码，200 表示成功
  - message: 状态描述
  - data: 具体的业务数据
- 对于分页接口，统一包含：
  - code: 状态码，200 表示成功
  - message: 状态描述
  - data: 具体的业务数据
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页大小
    - total_pages: 总页数
    - list: 具体数据列表

## Cursor Summary

- 目录用途: 提供 FastAPI 路由分层：
  - `v1`: 用户/鉴权、聊天、语音、资源、代理、设置、订阅、报告、评测、通知、管理等。
  - `v2`: 新版聊天接口聚合路由。
- 关键文件: `api/deps.py`（依赖注入/权限）、`api/v1/router.py`、`api/v2/router.py` 与各 `endpoints/*`。
- 关联: `app/schemas`/`app/services`/`app/models` 分别承担 IO 校验、业务逻辑、数据持久化职责。

## Emotions API（Live2D 情绪选择 Demo）

- 路由前缀：`/api/v1/emotions`
- 认证：需要 Bearer Token（与其他受保护接口一致）

### Endpoints

- `GET /list`：返回可选 20 个情绪名与描述
- `GET /mapping`：获取当前情绪→图片URL 映射（内存级）
- `POST /mapping`：设置映射
  - 请求体：
    ```json
    {
      "replace": true,
      "mapping": {"Happy": "https://cdn/happy.png", "Neutral": "https://cdn/neutral.png"}
    }
    ```
- `POST /select`：根据台词/上下文使用 Gemini 选择情绪并返回对应图片URL
  - 请求体：
    ```json
    {
      "utterance": "什么？我今天专门跑过来，结果它关门了？",
      "context": "角色最喜欢的咖啡馆今天关门",
      "character_state": "略微焦躁"
    }
    ```
  - 响应体（示例）：
    ```json
    { "code":200, "message":"success", "data": {"emotion":"Angry", "image_url":"https://cdn/angry.png"} }
    ```

说明：本 Demo 使用 Google Gemini（`google-genai`）并通过 JSON 模式强约束输出，仅返回 `emotion`。映射存储在进程内存中，适合演示与本地开发。
