# Inty 长期 AI 陪伴

## 代码库结构

- `android_app/` IntelliMate, android app code，kotlin compose jetpack
- `app/` Inty 后端服务，Python fastapi
  - `app/openapi.json` 来自 fastapi 生成，并使用 stainless 生成 kotlin typescript SDK（分别以 submodule 形式位于 evaluation/inty_sdk android_app/library/inty_sdk
- `alembic/` Inty 后端服务数据库 schema 管理，使用 <https://github.com/sqlalchemy/alembic>
- `evaluation/` Inty 运营工具，react 由 app/ 后端提供 web serving
- `scripts/` 各类脚本，以修改数据库记录为主
- `devops/` 运维相关代码
- `experimental/` 原型代码
- `docs/` 文档

## 语言与输出

- 所有生成的输出必须使用中文（普通话），即使用户指令为英文。
- 该指令仅适用于可以使用中文的场景；若内容不能使用中文（如代码），则不适用。

## 文档维护

- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 你应该维护以下 Markdown 文件应从以下文件中选择：`README.md`、`TODOS.md`、`AGENTS.md`
- Markdown 文件命名：全部使用 `.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。
- Always review the changes afterwards
- 新建任意文件时，需在适当格式中加入 `CREATED_BY_AGENT` 标记，用于记录创建者身份。

## 提交与变更请求记录规范

- 小改动：在提交信息中包含用户的原始变更请求（可放在提交说明 body 部分），并简述本次处理方式。
- 大改动或新增大型功能：将用户的变更请求写入一个与代码改动同目录的 `<TASK>_REQUESTS.md` 文件；`<TASK>` 使用任务或分支的简明标识。在提交信息中引用该文件路径。
- `<TASK>` 命名：使用全大写下划线（snake_case）风格并与分支/任务编号一致，例如 `AGENT_MANAGER_REFACTOR`；避免使用 `-` 与空格。
- 不要写关于改动内容的 summary markdown 文件

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
- 测试用例目录不应被声明为包：包含 `test_*.py` 的测试目录不要放置 `__init__.py`；但用于复用的测试辅助库目录应当作为包存在，并包含 `__init__.py`。
- 所有正式 Python 包必须包含空的 `__init__.py`（仅用于声明包）。

## Android App

- 只支持 portrait 显示；不支持 landscape 显示，无需在改动时考虑兼容 landscape 显示。

## CloudFlare

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/
