# AGENTS.md · tests/（测试）

- 不需要单元测试、只需要功能测试：通过调用 API Endpoints 完成一个功能的端到端测试

## 功能测试

- 测试时通过运行在本地的后端服务器调用 API Endpoints；
  服务器启动流程：`cp devops/config.yaml.test config.yaml && backend/inty/start.sh --test`；
  与 GitHub workflow [ci_backend.yaml](../.github/workflows/ci_backend.yaml) 一致。
- 不要 patch 数据库 sqlalchemy 函数，读写都直接进入真实数据库。
- 测试中[依赖的外部服务](app/external_services/fakes)使用 Fake Client 来替代。
