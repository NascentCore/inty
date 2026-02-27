# AGENTS.md · devops/（运维与部署）

## 链接

- GCP 数据库只读副本：https://docs.cloud.google.com/sql/docs/postgres/replication

## 配置与安全
- 配置文件统一使用 `.yaml` 后缀；敏感信息不入库，使用环境变量或密钥管理服务。

## 部署
- 以 `nginx.conf` 与发布文档为单一事实来源；任何变更需附影响评估与回滚方案。
