# AGENTS.md · devops/（运维与部署）

## 链接

- GCP 数据库只读副本：https://docs.cloud.google.com/sql/docs/postgres/replication

## 配置与安全
- 配置文件统一使用 `.yaml` 后缀；敏感信息不入库，使用环境变量或密钥管理服务。

## 部署
- 以 `nginx.conf` 与发布文档为单一事实来源；任何变更需附影响评估与回滚方案。

## 部署新的Inty后端服务实例

- 在数据库服务器上创建库
- 创建devops/config.yaml.<实例名称>配置文件实例
- 创建CI部署后端服务器

## 发布新的App实例

- 创建自动发布GitHub Workflow
  - <img width="3018" height="1700" alt="img_v3_0210t_48e461e3-113d-49b9-99cf-b527a1837a2g" src="https://github.com/user-attachments/assets/adf83b64-3629-489c-b516-6a7afc3c8d34" />

