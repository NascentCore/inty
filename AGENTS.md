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

## 语言与输出

- 所有生成的输出必须使用中文（普通话），即使用户指令为英文。

## Coding style

### Do not repeat in comments what's already obvious in the code

Do not generate comments like below.

```python
# Get current setting
def get_current_setting():
  ...
```

Instead, just let the function name or the code to speak for itself:

```python
def get_current_setting():
  ...
```

### Do not use magic number/string/values

Whenever possible define constants to name magic number/string/values to aid code readability.

### Prefer early return

Prefer:

```python
if false:
  return None

...
```

Over

```python
if true:
  ...
else:
  return None
```

## Python

- 避免使用 `try ... except Exception` 来覆盖所有异常，而应该至拦截函数能处理的异常

## Android App

- 只支持 portrait 显示；不支持 landscape 显示，无需在改动时考虑兼容 landscape 显示。

## CloudFlare

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/
