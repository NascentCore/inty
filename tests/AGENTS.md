# AGENTS.md · tests/（测试）

- Python 后端测试遵循 `pytest` 命名：`test_*.py`；仅调用公开接口，避免依赖实现细节。
- 不要 patch 数据库 sqlalchemy 函数，读写都直接进入真实数据库
- 使用 FakeGCSClient 来测试上传 GCS 的代码
- 新功能或修复必须附带测试
- 测试时假设本地已有测试用后端服务器运行在 http://localhost:8000/；(../.github/workflows/ci_backend.yaml) 中提供了该测试环境；
  服务器启动流程：`cp devops/config.yaml.test config.yaml && backend/inty/start.sh --test`
