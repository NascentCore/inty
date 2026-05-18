# `devops/docker/`：容器构建上下文

**一句话**：这里放 **把各进程打进 OCI 镜像** 的 Dockerfile；构建上下文通常是 **仓库根**，以便同时看到 `app/`、`backend/` 等依赖。

## 心智图

- **主后端镜像**：服务 App 的 Inty API 进程。
- **推送 worker 镜像**：异步通知/任务侧车或独立进程。
- **Ops 镜像**：带评测前端与运营 API 的那套进程。

## 深入阅读

- 各文件的参数、构建缓存与部署挂钩说明：见同目录 [`README.md`](README.md) 与 `.github/workflows` 中对应 build 任务。
