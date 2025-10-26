# 代理。md·experimental/（原型与实验）

本文件覆盖并补充根`AGENTS.md`，仅适用于 `experimental/`。

## 边界
- 非生产代码；不作为发布工件依赖；不影响 `app/` 与 `android_app/` 的构建。

## 约定
- 尽量最小化依赖并隔离环境；如需脚本/服务，请在本目录自备 `requirements.txt` 或说明。
- 若原型成熟，应迁移到对应正式目录并补齐测试与文档。
