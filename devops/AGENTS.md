# `devops/`：部署、配置与运维叙事

Inty 后端服务（及关联服务和代码）部署到云端服务器

## 部署模型

- 单服务器实例：GCP VM
- 单体后端服务架构：没有横向扩缩容
- Nginx 反向代理：基于 DNS 域名路由到多个不同后端服务
- 数据库采用 gcp 托管 postgresql 实例（提供备份、高可用、横向纵向扩展性等）

## 原则

- 配置：应用配置文件 YAML 格式，其他依赖系统按照其原生格式
- 密钥：目前写入配置文件、应改为写入环境变量
- 所有系统配置文件须提交本代码仓库
- 部署环境抽象：典型顺序是 **建库 → 为该环境写独立 config 变体 → 接入 CI/CD**——细节随基础设施演进，以同目录 README 为准。
- iOS Android App 相关内容也在这里

## Database setup

- Use `postgres:17` Docker container image to deploy local DB server to support Inty backends
- For local development, smoke testing, CI testing use `config.yaml.local`
  - Database configs in `config.yaml.test` must be kept compatible with `config.yaml.local`
- For dev & prod development, use `config.yaml.dev` and `config.yaml.prod` respectively
  - Google Cloud CloudSQL was used before, but was deprecated because of high cost
