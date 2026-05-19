# `research/`：研究项目

## 硬边界

- 每个项目单独创建文件夹
- 不进生产发布
- **自包含**：每个子目录包含全部外部依赖说明。
- 不依赖生产代码：除非用户明确要求、不引用本目录以外本代码库其他代码。
- **文档齐全**：记录原始请求、如何运行、记录分析结论。
- **代码不做容错处理**：只考虑成功路径
- **只做手动测试**：不写单元测试和其他自动化测试

## Python

- 虚拟环境：使用 `requirements.txt` `uv venv` `uv pip install -r ...`
- 使用：`python-dotenv` `Cyclopts`

## Pending things to explore

- [Agora-1: multi-agents world models](https://news.ycombinator.com/item?id=48183748)
