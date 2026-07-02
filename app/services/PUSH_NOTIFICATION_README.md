# 推送通知服务快速指南

## 快速开始

### 1. 配置

在 `config.yaml` 中添加推送服务配置：

```yaml
push_notification:
  enabled: true # 启用推送服务
  batch_size: 50 # 每批处理的聊天数量
  max_retries: 3 # 最大重试次数
  intervals:
    10min: 10 # 10分钟推送
    30min: 30 # 30分钟推送
    2h: 120 # 2小时推送
```

### 2. 数据库迁移

运行数据库迁移创建推送历史表：

```bash
alembic upgrade head
```

### 3. 运行服务

#### 本地运行

启动推送服务：

```bash
python -m backend.push_worker.main
```

或使用 systemd/supervisor 等进程管理器。

#### 容器化部署

推送服务支持 Docker 容器化部署，使用独立的 Dockerfile 和启动脚本。

**构建镜像**：

```bash
docker build \
  --build-arg CONFIG_FILE=devops/config.yaml.dev \
  -f devops/docker/Dockerfile.push-worker \
  -t inty-push-worker:latest .
```

**运行容器**：

```bash
docker run -d \
  --name inty-push-worker \
  --restart unless-stopped \
  --label application=inty-push-worker \
  --label environment=dev \
  --volume /opt/inty-dev/inty-backend-key.json:/inty-backend-key.json \
  --volume /opt/inty-dev/inty-firebase-key.json:/inty-firebase-key.json \
  inty-push-worker:latest
```

**GitHub Actions 自动部署**：

推送服务通过 GitHub Actions workflow 自动构建和部署：
- Workflow 文件：`.github/workflows/build_and_deploy_push_worker.yml`
- 触发条件：推送服务相关代码变更时自动触发
- 部署环境：支持 dev 和 prod 环境
- 镜像仓库：`ghcr.io/nascentcore/inty-backend/inty-push-worker`
- 容器名称：`inty-push-worker-{environment}`

查看部署状态：[推送服务部署](https://github.com/NascentCore/inty-backend/actions/workflows/build_and_deploy_push_worker.yml)

## 服务架构

```
backend/push_worker/main.py (入口)
    ↓
push_scheduler_service.py (定时任务调度)
    ↓
push_notification_service.py (核心逻辑)
    ├── get_chats_needing_push() (查询需要推送的聊天)
    ├── generate_agent_message() (生成 Agent 消息)
    ├── send_push_notification() (发送 FCM 推送)
    └── record_push_history() (记录推送历史)
```

## 推送流程

1. **定时任务触发**：APScheduler 按配置的时间间隔触发检查任务
2. **查询聊天**：查询距离最后用户消息达到阈值且未发送过推送的聊天
3. **生成消息**：使用 Agent 生成个性化推送消息
4. **发送推送**：通过 Firebase FCM 发送推送通知
5. **记录历史**：将推送记录保存到数据库，避免重复发送

## 推送阶段

- **10 分钟推送**：每 5 分钟检查一次，推送距离最后消息 10 分钟的聊天
- **30 分钟推送**：每 10 分钟检查一次，推送距离最后消息 30 分钟的聊天
- **2 小时推送**：每 30 分钟检查一次，推送距离最后消息 2 小时的聊天
- **节日记忆通知**（可选，`festival_memory_enabled`）：每 15 分钟扫描未投递且未发过 system notification 的节日记忆，发送 FCM；点击进入该角色 Love Journal 并定位到对应记忆条目。`push_type = "festival_memory"`，`stage = "festival"`。

## 注意事项

1. 确保 Firebase 服务账号已配置（`firebase.service_account_path`）
2. 确保用户设备已注册 FCM token（通过 `/api/v1/users/device/register`）
3. 推送服务独立运行，不影响主应用
4. 建议在生产环境使用进程管理器管理服务

## 故障排查

### 推送未发送

1. 检查配置：`push_notification.enabled` 是否为 `true`
2. 检查日志：查看是否有错误信息
3. 检查数据库：确认 `push_notification_history` 表已创建
4. 检查 Firebase：确认 Firebase 初始化成功

### 消息生成失败

1. 检查 Agent 数据：确认 Agent 存在且未删除
2. 检查用户数据：确认用户存在且未删除
3. 检查日志：查看 Agent 生成消息的错误信息

## 相关文档

- 详细文档：`backend/docs/PUSH_NOTIFICATION_SYSTEM.md`
- 代码实现：`app/services/push_notification_service.py`
