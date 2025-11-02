# api - API 接口

## API 更新流程【建议】

大体流程比较复杂，因此需要小心按照以下流程修改

### 更新代码和测试

* 修改代码，但不更新 app/openapi.json
* 使用 FastAPI TestClient 编写集成测试
* [Test Client](tests/app/api/test_client.py) 编写端到端测试
* 【如有必要】将功能集成到 inty 评测工具，进行测试，如消息生图功能
* 提交代码
* 示例：https://github.com/NascentCore/inty/pull/974/files

### 更新 openapi.json

```bash
export PYTHONPATH=.
python scripts/generate_openapi_json.py
```

等待 stainless build 完成，点击 studio 链接，然后将改动 merge inty-typescript inty-kotlin main 分支

<img width="800" height="744" alt="image" src="https://github.com/user-attachments/assets/d523f7fb-a2f7-4118-9853-27124dfda8ee" />

<img width="800" height="810" alt="image" src="https://github.com/user-attachments/assets/5b2ae567-61af-4bac-b253-b2963f55b8fc" />

点击之后会显示开始向生产环境代码库提交代码：

<img width="800" height="1374" alt="image" src="https://github.com/user-attachments/assets/4ce68cef-14f6-416e-b198-6968bd39874e" />

某些情况下，生成的代码会因为各种原因无法被自动提交到 main 分支，比如：cursor bugbot comment，这时候需要手动提交。

等待代码确认被提交到生产环境主分支后，再提交 openapi.json 更新的 PR。
示例：https://github.com/NascentCore/inty/pull/975

### 更新 Submodules

```bash
./update_inty_sdk_submodule.sh
```

示例：https://github.com/NascentCore/inty/pull/976/files

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
