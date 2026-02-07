# Inty 长期 AI 陪伴（仓库总入口 AGENTS.md）

- IntelliMate Android App 内用户可见的改动都要对应更新[用户手册](docs/INTELLIMATE.md)
  - app/（后端）改动不改动[用户手册](docs/INTELLIMATE.md)
- 本代码库开发人员母语为中文普通话
- 如有可能、在不影响正确性前提下，使用中文编写各类非代码的文字内容：代码注释、GitHub Pull Request 标题 & 描述等等

## 市场定位

IntelliMate 定位为面向 35+、工作稳定且具有较好社会地位与自我认知的美国男性用户的长期 AI 陪伴产品，提供可信赖、持续进化的情感支持与日常助理服务。
iMate 是所有角色的泛称。

## 基础约定

- **语言**：所有可自然语言表达的输出统一使用中文（普通话）。代码、命令、标识符不受该限制。
  只包含文档的目录用中文命名、方便理解，包含代码的目录必须用 English 以方便调用。
- **Python 版本**：仓库 `pyproject.toml` 约束为 `>=3.12`。
- **优先可维护性**：避免“为了省事”引入隐式行为（魔法常量、吞异常、无边界重试、隐藏的全局状态）。
- **改完要自查**：每次修改后都应回看 diff，确保改动与意图一致、无泄漏敏感信息、无无关文件被改动。

## Alembic

- 按照 alembic/README.md 中的步骤创建新的 alembic version 文件，而不是直接编写
- 修改数据库表 schema 应该**单独**进行，不要与其他改动混合：保证 alembic version 可以快速同步，避免多人并行产生非线性迁移链。
  - 例如：当前 alembic head revision 为 1，改动 A 与改动 B 同时修改 DB，则可能出现两个并行 version 文件都依赖 revision 1。

## 代码库结构

- `android_app/` IntelliMate, android app code，kotlin compose jetpack
- `app/` Inty 后端服务，Python fastapi
  - `app/openapi.json` 来自 FastAPI 生成，并使用 stainless 生成 Kotlin/TypeScript SDK（分别以 submodule 形式位于 `evaluation/inty_sdk`、`android_app/library/inty_sdk`）
- `alembic/` Inty 后端服务数据库 schema 管理，使用 <https://github.com/sqlalchemy/alembic>
- `evaluation/` Inty 运营工具，react 由 app/ 后端提供 web serving
- `web_app/` 独立 Web App（React/TS）
- `scripts/` 各类脚本，以修改数据库记录为主
- `devops/` 运维相关代码
- `experimental/` 原型代码
- `docs/` 文档
- `backend/`：后端相关文档与迁移中的说明（以目录内文档为准）

## 语言与输出

- 所有生成的输出默认使用中文（普通话），即使用户指令为英文。
- 如果输出文件主体使用英文，则输出用英文。
- 该指令仅适用于可以使用中文的场景；若内容不能使用中文（如代码），则不适用。

## 文档维护

- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 你应该维护的 Markdown 文件应从以下文件中选择：`README.md`、`TODOS.md`、`AGENTS.md`
- Markdown 文件命名：全部使用 `.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。
- 修改后务必回看 diff，确认无误再提交/交付。
- 新建任意文件时，需在适当格式中加入 `CREATED_BY_AGENT` 标记，用于记录创建者身份。
- 测试步骤写入 tests/docs/ 如 tests/docs/TEST_STEPS_RUNTIME_URL_SWITCH.md
- 新功能/需求开发对应的文档应该添加 FR_ 前缀，如 docs/FR_CHAR_BOOSTING.md

## 提交与变更请求记录规范

- 小改动：在提交信息中包含用户的原始变更请求（可放在提交说明 body 部分），并简述本次处理方式。
- 大改动或新增大型功能：将用户的变更请求写入一个与代码改动同目录的 `<TASK>_REQUESTS.md` 文件；`<TASK>` 使用任务或分支的简明标识。在提交信息中引用该文件路径。
- `<TASK>` 命名：使用全大写下划线（snake_case）风格并与分支/任务编号一致，例如 `AGENT_MANAGER_REFACTOR`；避免使用 `-` 与空格。
- 不要写关于改动内容的 summary markdown 文件

## Coding style

- 各类语言函数体不应超过 50 行；100 行以上必须拆分为更小函数；50-100 行之间酌情处理。

### 不要在注释里重复显而易见的代码含义

不要写这种“复述函数名”的注释：

```python
# Get current setting
def get_current_setting():
  ...
```

应该让函数名/代码本身表达含义：

```python
def get_current_setting():
  ...
```

### 避免魔法数字/字符串/值

尽可能用具名常量替代魔法值，提升可读性与可维护性。

### 优先早返回（early return）

优先：

```python
if false:
  return None

...
```

而不是：

```python
if true:
  ...
else:
  return None
```

## Python

- 避免使用 `try ... except Exception` 覆盖所有异常；只捕获当前函数**能够处理**的特定异常类型。
- 测试用例目录不应被声明为包：包含 `test_*.py` 的测试目录不要放置 `__init__.py`；但用于复用的测试辅助库目录应当作为包存在，并包含 `__init__.py`。
- 所有正式 Python 包必须包含空的 `__init__.py`（仅用于声明包）
- 严禁向已有的 `__init__.py` 内添加新逻辑代码（除非该目录规则明确要求）
- 使用 [cyclopts](https://github.com/BrianPugh/cyclopts) 来实现命令行界面

## 测试（仓库级）

- `pytest` 配置在 `pytest.ini`，默认收集 `app/` 与 `tests/` 下的 `test_*.py`。
- 常用命令（按环境选择 `python` 或 `python3`）：

```bash
python -m pytest
python -m pytest -m "not slow"
python -m pytest tests/app/services/test_chat_service.py -k test_xxx
```

## Android App

- 只支持 portrait 显示；不支持 landscape 显示，无需在改动时考虑兼容 landscape 显示。

## CloudFlare

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/
