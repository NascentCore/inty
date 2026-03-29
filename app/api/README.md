# api - API 接口

## API 更新流程【建议】

大体流程比较复杂，因此需要小心按照以下流程修改

### 更新代码和测试

* 修改代码
* 使用 FastAPI TestClient 编写集成测试
* [Test Client](tests/app/api/test_client.py) 编写端到端测试
* 【如有必要】将功能集成到 inty 评测工具，进行测试，如消息生图功能
* 提交代码
* 示例：https://github.com/NascentCore/inty/pull/974/files

### SDK 更新

仓库已不再维护 SDK submodule。若需要更新 SDK，请参考对应目录 README 的最新构建流程。

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
