# AGENTS.md · app/（后端服务）

- 不要编辑 `stainless.yml` `openapi.json` 这两个自动生成的配置文件
- API endpoints 返回给调用方的信息必须用英文，因为用户都是美国用户
- `global_services.py` 不能被任何其他 `*_service.py` 文件调用
- 使用 `dependency injection`（依赖注入）来编写函数，减少对全局变量的使用

## 超级用户权限

- 超级用户跳过所有订阅检查，使用 is_superuser（位于 app/core/user_privilege/superuser_check.py）

## 代码与结构

- 遵循根文件的 Python 风格要求：避免捕获笼统异常、优先早返回、避免魔法常量、日志使用 `logger.debug()`。
- API 入口在 `app/api/`（按版本与路由拆分）；核心逻辑放在 `app/services/` 与 `app/core/`；数据模型在 `app/models/` 与 `app/schemas/`。
- 配置读取走 `app/core/config.py`，不要在代码中硬编码环境变量名或路径。
