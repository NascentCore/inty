# Docker

- Dockerfiles
  - `Dockerfile`: 后端主服务镜像构建文件，构建上下文为项目根目录。
  - `Dockerfile.push-worker`: 推送服务镜像构建文件，构建上下文为项目根目录。
  - `Dockerfile.ops`: Ops 平台（evaluation + /api/v1）镜像构建文件，构建上下文为项目根目录；部署见 `.github/workflows/build_and_deploy_ops.yml`。
- 文档
  - `README.md`: Dockerfile 使用说明与构建注意事项。
