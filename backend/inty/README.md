# AI 陪伴后端主服务

提供核心聊天功能、及配套支持功能

- 启动：在仓库根目录执行 `./backend/inty/start.sh --dev`（见仓库根 README 与 `backend/README.md`）

## APIs

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/` | GET | `backend/inty/main.py`（`build_health_check_data(ops=False)`） |
| `/metrics` | GET | `backend/inty/main.py`（`app.debug` 为 true 或 `environment` 为 `TEST` 时可用；否则 404） |
