# `experimental/`：原型与实验沙箱

**一句话**：演示、评测脚本、概念验证——**默认不进生产发布**；每个子目录应尽量 **自包含**，自带依赖说明。

## 硬边界

- **不要引用沙箱外的业务代码**（避免实验目录把主产品线拖成耦合图）。
- **文档齐全**：至少 README 说明目的、如何跑、需要什么密钥；复杂实验再拆 AGENTS。

## Python 习惯

- **依赖**：各实验自备 `requirements.txt`；版本号 **不 pin**，由环境解析；需要「强制刷新到最新」时用你习惯的包管理器卸载再装（见子目录 README）。
- **密钥**：用 `python-dotenv` 从 `.env` 读取 API key，**不要**把真实 `.env` 提交进 git。

## 特殊子项目指针

- **Telegram + perpetual_agent 联调**：见 `perpetual_agent/README.md` 与仓库 `tests/docs/TEST_STEPS_TELEGRAM_PERPETUAL_AGENT.md`。
- **Telegram + OpenAI 兼容通道**：同上 README 的「Telegram + OpenAI」章节。

## Inspirations

- Paint by Language Model
  - [Gallery](https://www.liamlaverty.com/paint-by-language-model/)
  - [Programmer API](https://www.liamlaverty.com/paint-by-language-model/draw/api)
