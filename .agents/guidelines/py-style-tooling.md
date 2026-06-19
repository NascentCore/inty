# Google Python 本地风格（Cursor 交互）

依据 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.md)。仓库根 [`pylintrc`](../../pylintrc) 与 [`pyproject.toml`](../../pyproject.toml) 中的 `[tool.black]` / `[tool.pylint.main]` 为唯一配置来源。

## 安装

在仓库根目录、Python 3.12：

```bash
uv sync --group dev
```

## 常用命令

```bash
uv run black <paths>
uv run pylint <paths>    # 例：app backend tools/scripts
uv run ty check
```

首次对大范围路径跑 `pylint` 会有大量既有告警，仅作交互参考，不表示环境未装好。

## pylint 抑制（pyguide §2.1.4）

对确属误报或项目约定处，使用行级注释并写明原因：

```python
def do_PUT(self):  # WSGI name, so pylint: disable=invalid-name
    ...
```

优先 `pylint: disable=`，不用已废弃的 `disable-msg`。

## 与 Inty AGENTS 的分歧

| 主题 | pyguide | Inty |
|------|---------|------|
| `assert` | 不作业务前置校验 | 用 `assert` 校验参数 |
| 异常 | 避免过宽 `except` | 业务层少写 try/except |

交互改代码时按需抑制，勿为清零告警而大改无关逻辑。

## Cursor / Pylint 扩展（可选）

若安装 Pylint 扩展，在用户或工作区设置中让 pylint 使用仓库根 rc，例如：

```json
"pylint.args": ["--rcfile=${workspaceFolder}/pylintrc"]
```

不强制提交 `.vscode/settings.json`。

## 后续 TODO（非本次范围）

1. **ty agentic loop**：按 [Pyrefly agentic loop](https://pyrefly.org/blog/pyrefly-agentic-loop/) 的模式，用已有 `uv run ty check` 落地（不引入 Pyrefly）——Cursor skill、根 `AGENTS.md` 或 harness AGENTS 的「改 Python 后必须 ty check → 修错 → 再跑」、可选 Stop hook；参考 [pyrefly_hooks_demo](https://github.com/kinto0/pyrefly_hooks_demo)。
2. **pre-commit**：black + pylint + 可选 ty。
3. **`tools/scripts/lint-python.sh`**：与 `fmt.sh` 对称的一键 check / `--fix`。
4. **fmt 对齐**：`fmt.sh` 与定时 format workflow 使用 `pyproject.toml` 80 列。
5. **CI**：`ci_backend.yaml` 增加 lint（可先 `pylint --errors-only`）。
6. **Cloud Agent**：见 [CLOUD_AGENTS.md](CLOUD_AGENTS.md) **Verify Python dev tools**；`.cursor/cloud-agent-install.sh` 用 `pip` 把 `uv`/`ruff` 等装进 `.venv`（非全局 PATH）；系统 apt 包（含 `gcloud`）在 `.cursor/cloud-agent-apt.sh`。
7. **消噪 / 格式化 PR**：全库 black 80、pylint 配置收紧。
8. **Pyink**（可选）：替换 Black。
