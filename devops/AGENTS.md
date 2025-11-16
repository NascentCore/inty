# AGENTS.md · devops/（运维与部署）

本文件覆盖并补充根 `backend/AGENTS.md`，仅适用于 `devops/`。

## 配置与安全
- 配置文件统一使用 `.yaml` 后缀；敏感信息不入库，使用环境变量或密钥管理服务。
- 不直接改动 `config.yaml.prod`/`config.yaml.dev` 的受控字段；新增项先更新 `config.yaml.template` 并在文档中说明。

## 部署
- 以 `nginx.conf` 与发布文档为单一事实来源；任何变更需附影响评估与回滚方案。
