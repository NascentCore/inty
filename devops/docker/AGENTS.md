# Docker

- Dockerfiles
  - `Dockerfile.alembic`: 用于运行 Alembic 数据库迁移的轻量级 Docker 镜像。构建上下文应为项目根目录，使用 `docker build -f devops/docker/Dockerfile.alembic -t inty-alembic .` 构建。
