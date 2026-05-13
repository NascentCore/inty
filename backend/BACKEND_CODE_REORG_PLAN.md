CREATED_BY_AGENT
# Backend 代码重组计划

## 目标
- 将所有后端相关代码与资源统一放入 `backend/` 目录，理清边界，降低根目录噪音。
- 更新构建、部署、开发文档与自动化流程以匹配新的路径结构。
- 在迁移过程中保持服务可用性，确保 CI/CD 流程持续通过。

## 里程碑
1. **目录搭建**
   - 创建 `backend/`，逐步迁入后端服务目录（`app/`、`alembic/`、`tools/scripts/`、`devops/` 等）。
   - 迁移同时保留原路径的引用映射记录，便于后续批量替换。
   - 进展：2025-11-16 已将根目录的 `README.md`、`AGENTS.md`、`TODOS.md` 与 `docs/` 迁入 `backend/`。
2. **脚本与配置同步**
   - 更新根层脚本（`Dockerfile*`、`docker-compose.yaml`、`start*.sh`、`tools/scripts/fmt.sh`、`evaluation/build.sh`）。
   - 校正 Python 配置（`pyproject.toml`、`pytest.ini`、`requirements*.txt`）与服务入口（`README.md`、`docs/DEV.md`）。
3. **引用修复**
   - 全仓库搜索硬编码路径，替换为 `backend/...`。
   - 验证 Python 包导入、模块相对路径、数据脚本调用等不会断裂。
4. **CI/CD 与部署**
   - 更新 `.github/workflows/` 及任何外部部署脚本，必要时设置 `working-directory: backend`。
   - 修正 `devops/` 配置（`config.yaml.*`、`nginx.conf` 等）与 Terraform/SOPS 相关引用。
5. **验证与回归测试**
   - 本地跑 `docker compose up pgvector -d`、`./backend/inty/start.sh --dev`、单元/集成测试。
   - 触发或手动运行 CI 确认工作流通过，记录迁移注意事项。

## 风险与缓解
- **路径漏改**：使用 `rg`/IDE 搜索确认所有引用；迁移后运行静态检查与测试。
- **脚本顺序依赖**：迁移时保持提交粒度小且可回滚；必要时增加兼容软链接（短期）。
- **CI/CD 中断**：在 workflow 修改后立即跑一次完整流水线，必要时引入临时变量控制新旧路径。

## 后续行动
- 为迁移准备清单（详列每个目录、脚本的旧路径与新路径）。
- 在迁移完成后更新相关 `AGENTS.md` 或 README，记录新的目录结构与操作指南。
