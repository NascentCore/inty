## 后端水平扩展与多实例部署改造方案（Cloud Run + GCLB）

本方案将后端从单实例/Nginx 反代迁移到 Google Cloud 的托管入口：Cloud Run + 外部 HTTP(S) 负载均衡（GCLB）+ Serverless NEG；状态外置到 Cloud SQL（Postgres）与 Memorystore（Redis），并通过 Redis 实现跨实例缓存失效与事件广播，确保 WebSocket/SSE 在多实例下保持一致性与稳定性。

---

### 目标与范围
- **无状态化请求处理**：进程内可变状态移出到 Redis/DB；实例随启随停。
- **共享状态外置**：缓存/锁/广播用 Redis；数据持久化用 Postgres。
- **长连接稳定**：GCLB 粘性会话 + 长超时，支持 WebSocket/SSE。
- **启动/预热/任务解耦**：预热加分布式锁；重活下沉到异步任务。

---

### 推荐目标架构（最简且托管）
- **Cloud Run（FastAPI 容器）**：自动扩缩，原生支持 WS/SSE。
- **GCLB + Serverless NEG**：七层负载，粘性会话，超时可配置。
- **Cloud SQL for Postgres**：当前数据库直迁或复用。
- **Memorystore for Redis**：缓存、分布式锁、Pub/Sub 广播。
- **Secret Manager / Cloud Logging / Monitoring / Trace**：密钥与观测体系。
- （可选）**Cloud Storage + Cloud CDN**：承载静态资源/前端，减轻后端压力。

---

### 入口与基础设施（替换 Nginx）
- **会话粘性**：GCLB 后端服务开启 `GENERATED_COOKIE` 粘性（TTL 3600s）。
- **长连接超时**：GCLB Backend `timeout=3600s`；Cloud Run `--timeout=3600`。
- **TLS/证书**：使用 Managed SSL，自动签发与续期。
- **私网访问**：VPC Serverless Connector；Cloud SQL/Redis 走私网。
- **健康检查**：Serverless NEG 复用 Cloud Run 健康/就绪，无需自建探针。

---

### 应用改造清单（最小必要）
- **缓存与广播**（`app/services/cache_service.py`、`app/services/system_settings_service.py`）
  - 抽象 `CacheBackend` 接口：`get/set/delete/ttl/exists`。
  - 实现 `RedisCacheBackend`（aioredis/redis-py），支持 TTL。
  - 跨实例失效：Redis Pub/Sub（频道如 `cache:invalidate`）。
  - `cache_service` 生产环境选择 Redis；开发保留内存后端。
  - `system_settings_service` 改为依赖 `cache_service`，移除直接 `InMemoryCache` 使用。
- **Agent 管理与一致性**（`app/core/agent/agent.py`）
  - 启动“热门 Agent 预热”加分布式锁（键如 `locks:agent:prewarm`）。
  - 订阅 `agent:invalidated` 频道；收到事件后清理本机 LRU 实例缓存并按需懒加载。
  - 保留每实例短期 LRU 缓存，但不承载跨实例唯一状态。
- **评测实时广播（WS/SSE）**（`app/services/evaluation_service.py`、`app/api/v1/endpoints/evaluation.py`）
  - `_broadcast_update` 改为发布到 Redis 频道：`evaluation:{session_id}`。
  - 新增本机 `WebSocketConnectionRegistry`：仅保存当前实例的连接集合。
  - 订阅 `evaluation:*` 频道：若本机持有 `session_id` 连接则扇出下发。
  - GCLB 粘性保障同一会话长链保持在同一实例。
- **应用生命周期**（`app/main.py`）
  - `startup`：启动缓存清理任务与 Redis 订阅协程（防重入/幂等）。
  - `shutdown`：优雅关闭订阅与清理任务。
- **幂等与并发控制**（按需逐步引入）
  - 同一 `content_hash`（语音生成）用 Redis 分布式锁；DB 唯一约束兜底。
  - 重型任务迁移到异步队列（先用 Redis 队列，后续可上 Cloud Run Jobs/Celery）。
- **配置与环境变量（优先 env，避免直接改 `config.yaml`）**
  - `REDIS_URL`、`PUBSUB_PREFIX`（如 `inty`）、`INSTANCE_ID`（默认 `$HOSTNAME`）。
  - `FEATURES_LEADER_ENABLED=true|false`（仅 leader 实例执行预热）。
  - Cloud SQL 连接参数（私网地址或 Cloud SQL Auth Proxy）。

---

### 部署关键参数与示例（Cloud Run / GCLB）

- 变量示例：`PROJECT_ID`、`REGION`（如 `asia-east1`）、`DOMAIN`、`SERVICE=inty-backend`。

1) 启用服务与网络，创建 Redis 与 VPC Connector
```bash
gcloud services enable redis.googleapis.com vpcaccess.googleapis.com

# VPC Serverless Connector
gcloud compute networks vpc-access connectors create serverless-conn \
  --region=REGION --network=default --range=10.8.0.0/28

# Memorystore for Redis（按需调整 tier/size）
gcloud redis instances create inty-redis \
  --region=REGION --size=1 --redis-version=REDIS_6_X --network=default
```

2) 部署 Cloud Run（长超时/并发/保温/私网访问）
```bash
gcloud run deploy inty-backend \
  --image=gcr.io/PROJECT_ID/inty-backend:TAG \
  --region=REGION --platform=managed --allow-unauthenticated \
  --concurrency=50 --min-instances=2 --max-instances=50 \
  --memory=1Gi --cpu=2 --timeout=3600 \
  --vpc-connector=serverless-conn \
  --set-env-vars=REDIS_URL=redis://REDIS_PRIVATE_IP:6379,PUBSUB_PREFIX=inty,INSTANCE_ID=$HOSTNAME
# 提示：Cloud SQL 建议走私网直连或 Cloud SQL Auth Proxy；把 DATABASE_URL/ASYNC_DATABASE_URL 注入环境变量。
# 可选：--cpu-boost 提升冷启动和流式响应稳定性。
```

3) 绑定 Serverless NEG，创建 GCLB 并开启粘性
```bash
# Serverless NEG 指向 Cloud Run
gcloud compute network-endpoint-groups create inty-neg \
  --region=REGION --network-endpoint-type=serverless \
  --cloud-run-service=inty-backend

# Backend Service（粘性 & 超时）
gcloud compute backend-services create inty-bes \
  --global --load-balancing-scheme=EXTERNAL_MANAGED --protocol=HTTP \
  --timeout=3600s --session-affinity=GENERATED_COOKIE --affinity-cookie-ttl=3600

gcloud compute backend-services add-backend inty-bes \
  --global --network-endpoint-group=inty-neg --network-endpoint-group-region=REGION

# URL Map / Proxy / Forwarding Rule
gcloud compute url-maps create inty-map --default-service=inty-bes

gcloud compute ssl-certificates create inty-cert \
  --domains=DOMAIN --global

gcloud compute target-https-proxies create inty-https-proxy \
  --url-map=inty-map --ssl-certificates=inty-cert

gcloud compute forwarding-rules create inty-https-fr \
  --global --target-https-proxy=inty-https-proxy --ports=443
# 将域名 A 记录指向 inty-https-fr 的全局 IP；证书将自动签发。
```

---

### 应用侧与基础设施配合
- **环境变量**：
  - `REDIS_URL=redis://10.x.x.x:6379`
  - `PUBSUB_PREFIX=inty`
  - `INSTANCE_ID=$HOSTNAME`（用于日志与调试定位）
  - `DATABASE_URL`/`ASYNC_DATABASE_URL`（Cloud SQL 私网/代理）
- **流式/长连接**：Cloud Run `--timeout>=3600`；GCLB 后端 `timeout=3600s`；无需额外头部即可支持 WS/SSE。
- **分布式组件**：缓存/锁/广播优先用 Memorystore（Redis）；如需跨区域/持久化广播，可后续改用 Cloud Pub/Sub。
- **数据库迁移**：使用 Cloud Build/Cloud Run Job 运行 Alembic 迁移，不在应用进程内自动迁移。

---

### 里程碑与验收
- **里程碑1**：引入 Redis 缓存后端与 Pub/Sub；缓存/失效跨实例一致。
- **里程碑2**：`AgentManager` 预热加分布式锁；订阅 `agent:invalidated` 生效。
- **里程碑3**：评测广播改为 Redis 频道；WS/SSE 在 GCLB 下稳定 30+ 分钟。
- **验收**：
  - 多实例下更新 Agent 配置，其他实例 1s 内命中失效。
  - 同一评测会话连接可收到跨实例广播。
  - 流式/长链稳定，无异常 5xx/断链峰值。

---

### 风险与对策
- **缓存一致性**：采用“写后删缓存 + 事件广播”；读侧短 TTL；发布/订阅按前缀分组降低风暴。
- **并发/双写**：DB 唯一约束 + 分布式锁 + 幂等键（如 `X-Idempotency-Key`）。
- **长连接中断**：粘性会话 + 长超时；客户端自动重连策略。
- **启动风暴**：仅 leader 预热；其余实例懒加载；设置 `min-instances`。

---

### 回滚策略
- 临时关闭 Redis 后端（降级为单实例或本地内存，仅限紧急回退）。
- 关闭订阅与广播逻辑（特性开关）；逐步缩减实例数至 1 观察。
- GCLB 切换为直连单一 Cloud Run 修复窗口，问题解决后再回切多实例。
