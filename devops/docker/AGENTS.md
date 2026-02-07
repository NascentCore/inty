# Docker

- Dockerfiles
  - `Dockerfile`: 后端主服务镜像构建文件，构建上下文为项目根目录。
  - `Dockerfile.alembic`: 用于运行 Alembic 数据库迁移的轻量级 Docker 镜像。构建上下文应为项目根目录，使用 `docker build -f devops/docker/Dockerfile.alembic -t inty-alembic .` 构建。
  - `Dockerfile.push-worker`: 推送服务镜像构建文件，构建上下文为项目根目录。
- 文档
  - `README.md`: Dockerfile 使用说明与构建注意事项。
