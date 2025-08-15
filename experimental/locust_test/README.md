# Inty Backend Chat API 负载测试

本目录包含用于 Inty Backend chat 接口并发性能测试的完整解决方案，使用 Locust 框架进行负载测试，支持在 Google Cloud Platform 上部署和执行。

## 📁 文件结构

```
experimental/locust_test/
├── README.md                    # 项目说明文档
├── test-plan.md                 # 详细测试计划和规格
├── locustfile.py               # Locust测试脚本
├── docker-compose.test.yml     # Docker测试环境配置
├── gcp-deployment.md           # GCP部署指南
└── requirements.txt            # Python依赖文件
```

## 🎯 测试目标

- **主要目标**: 评估 Inty Backend 在 1c2g 资源限制下的并发性能
- **测试环境**: GCP VM (4c8g) + Docker 容器 (1c2g 限制)
- **核心接口**:
  - 游客注册: `POST /api/v1/auth/guest`
  - Agent 聊天: `POST /api/v1/chats/agents/{agent_id}/chat/completions`

## 🚀 快速开始

### 0. 数据库准备 (推荐)

```bash
# 从生产环境导出完整数据库结构和数据
./export_database.sh --full --init

# 查看导出选项
./export_database.sh --help
```

### GCP 部署测试

详细步骤请参考 [gcp-deployment.md](./gcp-deployment.md)

```bash
# 创建GCP VM
gcloud compute instances create inty-load-test-vm --machine-type=e2-standard-4 --zone=asia-east1-a

# SSH连接并部署
gcloud compute ssh inty-load-test-vm --zone=asia-east1-a

# 在VM上执行测试
docker-compose -f docker-compose.test.yml up -d
```

## 📊 测试场景

### 场景 1: 基础负载测试

- **用户数**: 5 → 20 (渐进增长)
- **持续时间**: 10 分钟
- **目标**: 建立性能基线

### 场景 2: 压力测试

- **用户数**: 20 → 100 (渐进增长)
- **持续时间**: 15 分钟
- **目标**: 找到性能拐点

### 场景 3: 峰值测试

- **用户数**: 100 → 200 (快速增长)
- **持续时间**: 5 分钟
- **目标**: 测试极限承载能力

### 场景 4: 稳定性测试

- **用户数**: 50 (恒定)
- **持续时间**: 30 分钟
- **目标**: 验证长期稳定性

## 🔧 配置说明

### 容器资源限制

```yaml
# 后端服务资源限制
deploy:
  resources:
    limits:
      cpus: "1.0" # 1核CPU
      memory: 2G # 2GB内存

# 配置文件挂载 (基于生产环境config.yaml)
volumes:
  - ./config.test.yaml:/config.yaml:ro
  - ./inty-backend-key.json:/inty-backend-key.json:ro
  - ./inty-firebase-key.json:/inty-firebase-key.json:ro
```

### 配置文件说明

- **config.test.yaml**: 基于生产环境 config.yaml 的测试配置
- **inty-backend-key.json**: Google Cloud 服务账号密钥 (测试环境使用 mock 文件)
- **inty-firebase-key.json**: Firebase 服务账号密钥 (测试环境使用 mock 文件)

### 测试参数

- **并发用户**: 可通过 Locust Web 界面或命令行调整
- **Agent IDs**: 在 locustfile.py 中配置实际的 agent_id
- **测试消息**: 预设了多种聊天消息模拟真实场景

## 📈 性能指标

### 响应时间

- 平均响应时间
- P50/P95/P99 响应时间
- 最大响应时间

### 吞吐量

- RPS (每秒请求数)
- 并发用户数
- 事务完成率

### 资源使用

- CPU 使用率
- 内存使用情况
- 数据库连接数

### 错误率

- HTTP 错误分布
- 业务逻辑错误
- 超时请求比例

## 🔑 镜像访问权限

测试环境使用的是生产镜像，需要适当的访问权限：

```bash
# 如果是私有镜像，需要先登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 或使用GitHub个人访问令牌
docker login ghcr.io -u your-github-username
```

## 🎮 使用方法

### Web 界面测试

1. 启动 Locust 服务: `docker-compose -f docker-compose.test.yml up -d locust-master`
2. 访问: `http://localhost:8089`
3. 设置参数并开始测试

### 命令行测试

```bash
# 基础测试
locust -f locustfile.py --host=http://localhost:8000 --users=20 --spawn-rate=2 --run-time=10m --headless --html=basic-test.html

# 压力测试
locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=5 --run-time=15m --headless --csv=stress-test

# 自定义场景
locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=10 --run-time=30m --headless
```

## 📋 预期结果

### 正常负载 (≤20 并发)

- 平均响应时间: < 1.5 秒
- P95 响应时间: < 3 秒
- 成功率: > 98%
- CPU 使用率: < 70%

### 压力负载 (20-100 并发)

- 平均响应时间: < 3 秒
- P95 响应时间: < 8 秒
- 成功率: > 90%
- CPU 使用率: < 90%

## 🔍 监控和分析

### 实时监控

```bash
# Docker资源监控
docker stats

# 系统资源
htop

# 应用日志
docker-compose logs -f inty-backend
```

### 监控界面

- **Locust Dashboard**: `http://localhost:8089`
- **Grafana**: `http://localhost:3000` (如果启用监控)
- **Prometheus**: `http://localhost:9090` (如果启用监控)

## ⚠️ 注意事项

### 测试前准备

1. 确保测试环境资源充足
2. 检查网络连接稳定性
3. 配置正确的 Agent IDs
4. 验证数据库连接

### 测试期间

1. 监控系统资源使用
2. 观察错误日志
3. 记录关键性能指标
4. 避免其他重负载操作

### 测试后清理

1. 保存测试报告和数据
2. 停止所有测试服务
3. 清理 Docker 资源
4. 删除 GCP 实例(如果使用)

## 🛠️ 故障排除

### 常见问题

1. **连接超时**: 检查网络配置和服务状态
2. **认证失败**: 验证 token 生成和传递
3. **资源不足**: 调整并发数或增加资源
4. **数据库连接**: 检查连接池配置

### 调试命令

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs inty-backend

# 测试API连通性
curl http://localhost:8000/health
```

## 📝 测试报告

测试完成后会生成以下报告：

- HTML 格式的详细报告
- CSV 格式的原始数据
- 性能指标汇总
- 系统资源使用统计

## 🤝 贡献指南

如需修改或扩展测试：

1. 修改 `locustfile.py` 添加新的测试场景
2. 更新 `test-plan.md` 记录变更
3. 调整 `docker-compose.test.yml` 配置
4. 更新相关文档

---

**联系信息**: 如有问题请联系开发团队或查看相关文档。
