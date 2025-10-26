# AGENTS.md · tests/（测试）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `tests/`。

## 约定
- Python 后端测试遵循 `pytest` 命名：`test_*.py`；仅调用公开接口，避免依赖实现细节。
- 新功能或修复必须附带测试；保持测试独立可重复、无外部状态依赖。
