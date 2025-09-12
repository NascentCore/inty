# Inty: long term AI companionship: start with intimacy for young adults 

Based on [AGENTS.md](https://agents.md/)

## Repo structure

- `android_app/` IntelliMate, android app code，kotlin 原生架构
- `app/` Inty 包含全部后端服务，fastapi http 服务
- `alembic/` Inty 后端服务数据库管理组件，使用 <https://github.com/sqlalchemy/alembic>
- `sdks/` Inty SDKs 包含多种语言的后端服务 SDK，使用 [stainless OpenAPI](https://www.stainless.com/docs) 生成
  - `sdks/python` 后端服务 Python SDK，git module
  - `sdks/typescript` 后端服务 Python SDK，git module
- `evaluation/` Inty-eval, Inty 智能体/角色管理及评测工具，react 浏览器应用
- `experimental/` 原型代码
- `scripts/` 运维、运营脚本
- `devops/` Inty IntelliMate 运维相关代码
- `docs/` 文档

## Alembic deprecating column

Use the pattern below to deprecate a column in sqlalchemy table.

```python
@property
  def col_to_deprecate(self):
    warnings.warn(...)
    return self._col_to_deprecate
```
