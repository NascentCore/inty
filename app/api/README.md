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
