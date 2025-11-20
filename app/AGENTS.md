# AGENTS.md · app/（后端服务）

- 本文件覆盖并补充仓库根 `AGENTS.md`，仅适用于 `app/`
- 不要编辑 `stainless.yml` `openapi.json` 这两个自动生成的配置文件

## 范围与目标
- 负责 FastAPI HTTP 服务与业务逻辑。
- 变更必须做到可测试、可回滚、可观测。

## 代码与结构
- 遵循根文件的 Python 风格要求：避免捕获笼统异常、优先早返回、避免魔法常量、日志使用 `logger.debug()`。
- API 入口在 `app/api/`（按版本与路由拆分）；核心逻辑放在 `app/services/` 与 `app/core/`；数据模型在 `app/models/` 与 `app/schemas/`。
- 配置读取走 `app/core/config.py`，不要在代码中硬编码环境变量名或路径。

## 数据库与迁移
- 所有数据结构变更必须配套 `alembic/` 迁移；禁止直接修改历史迁移，新增迁移代替。
- `agents.version` 为整型版本号，新增或更新 Agent 时由 ORM 自动递增，可通过该字段感知数据更新。

## 异步与性能
- FastAPI 路由中避免阻塞式 I/O；必须使用异步客户端或在线程池隔离。
- 外部调用要有超时与重试的上限，错误走统一异常与错误码。

## 测试与文档
- 新增/变更功能需在 `tests/` 添加或更新用例
- 测试时假设本地已有测试用后端服务器运行在 http://localhost:8000/
