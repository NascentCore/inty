## 教室水平扩展与多实例部署改造方案（Cloud Run + GCLB）

本方案将租户从单实例/Nginx反代迁移到 Google Cloud 的托管入口：Cloud Run + 外部 HTTP(S) 负载均衡（GCLB）+ Serverless NEG；状态外置到 Cloud SQL（Postgres）与 Memorystore（Redis），并通过 Redis 实现跨实例备份失效与事件广播，确保 WebSocket/SSE 在多实例下保持一致性与稳定性。

---

### 目标与范围
- **无状态化请求处理**：进程内可变状态移出到Redis/DB；实例随启随停。
- **共享状态外置**：缓存/锁/广播用Redis；数据持久化用Postgres。
- **长连接稳定**：GCLB粘性会话 + 长超时，支持WebSocket/SSE。
- **启动/前置/任务解耦合**：前置加锁；重活下沉到异步任务。

---

### 推荐目标架构（最简且托管）
- **Cloud Run（FastAPI 容器）**：自动扩缩，初步支持 WS/SSE。
- **GCLB + Serverless NEG**：七层负载，粘性会话，超时可配置。
- **Cloud SQL for Postgres**：当前数据库直迁或复用。
- **Memorystore for Redis**：缓存、全局锁、Pub/Sub 广播。
- **秘密管理器/云记录/监控/追踪**：遥控与安装体系。- （任选）**云存储+云CDN**：承载静态资源/支架，减弱重力。

---

### 入口与基础设施（替换Nginx）
- **会话粘性**：GCLB 桌面服务开启`GENERATED_COOKIE`粘性（TTL 3600s）。
- **长连接超时**：GCLB后端`timeout=3600s`；云跑`--timeout=3600`。
- **TLS/证书**：使用托管SSL，自动签发与续期。
- **私网访问**：VPC Serverless Connector；Cloud SQL/Redis 走私网。
- **健康**：Serverless NEG 复用 Cloud Run 健康/就绪，无需自建标记。

---

###应用改造清单（最小必要）
- ** 缓存与广播**（`app/services/cache_service.py`、`app/services/system_settings_service.py`）
  - 抽象 `CacheBackend` 接口：`get/set/delete/ttl/exists`。
  - 实现 `RedisCacheBackend`（aioredis/redis-py），支持TTL。
  - 跨实例失败：Redis Pub/Sub（频道如`cache:invalidate`）。
  - `cache_service`生产环境选择Redis；开发保留内存。
  -`system_settings_service` 改为依赖 `cache_service`，移除直接 `InMemoryCache`使用。
- **代理管理与一致性**（`app/core/agent/agent.py`）
  - 启动“热门代理预热”加锁（键如）`locks:agent:prewarm`）。
  - 订阅 `agent:invalidated`频道；事件后清理本机LRU接收实例缓存并懒加载。
  - 保留每个实例短期LRU缓存，但不承载跨实例唯一状态。
- **体育实时广播（WS/SSE）**（`app/services/evaluation_service.py`、`app/api/v1/endpoints/evaluation.py`）
  - `_broadcast_update`最初发布到Redis频道：`evaluation:{session_id}`。
  - 新增本机 `WebSocketConnectionRegistry`：仅保存当前实例的连接集合。
  - 订阅 `evaluation:*` 频道：若本机持有 `session_id` 连接则扇出下发。
  - GCLB 粘性保障同一会话长链保持在同一实例。
- **应用生命周期**（`app/main.py`）
  - `startup`：启动服务器清理任务与Redis订阅协程（防重入/幂等）。
  -`shutdown`：优雅关闭订阅与清理任务。
- **幂等与并发控制**（按需逐步引入）
  - 同一 `content_hash`（语音生成）用Redis全球锁；DB约束独家兜底。
  - 重型任务迁移到队列（先用Redis队列，后续可上Cloud Run Jobs/Celery）。
- **配置与环境指标（优先环境，避免直接改）`config.yaml`）**
  - `REDIS_URL`、`PUBSUB_PREFIX`（如 `inty`）、`INSTANCE_ID`（默认 `$HOSTNAME`）。
  - `FEATURES_LEADER_ENABLED=true|false`（仅leader实例执行前置）。
  - Cloud SQL 连接参数（私网地址或 Cloud SQL Auth Proxy）。

---

### 部署关键参数与示例（Cloud Run / GCLB）

- 指标示例：`PROJECT_ID`、`REGION`（如 `asia-east1`）、`DOMAIN`、`SERVICE=inty-backend`。

1) 启用网络服务，创建Redis和VPC Connector```bash
gcloud services enable redis.googleapis.com vpcaccess.googleapis.com

# VPC Serverless Connector
gcloud compute networks vpc-access connectors create serverless-conn \
  --region=REGION --network=default --range=10.8.0.0/28

# Memorystore for Redis（按需调整 tier/size）
gcloud redis instances create inty-redis \
  --region=REGION --size=1 --redis-version=REDIS_6_X --network=default
```2) 部署Cloud Run（超长超时/保温/保温/私网访问）```bash
gcloud run deploy inty-backend \
  --image=gcr.io/PROJECT_ID/inty-backend:TAG \
  --region=REGION --platform=managed --allow-unauthenticated \
  --concurrency=50 --min-instances=2 --max-instances=50 \
  --memory=1Gi --cpu=2 --timeout=3600 \
  --vpc-connector=serverless-conn \
  --set-env-vars=REDIS_URL=redis://REDIS_PRIVATE_IP:6379,PUBSUB_PREFIX=inty,INSTANCE_ID=$HOSTNAME
# 提示：Cloud SQL 建议走私网直连或 Cloud SQL Auth Proxy；把 DATABASE_URL/ASYNC_DATABASE_URL 注入环境变量。
# 可选：--cpu-boost 提升冷启动和流式响应稳定性。
```3) 绑定Serverless NEG，创建GCLB并开启粘性```bash
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
- **流式/长连接**：Cloud Run`--timeout>=3600`；GCLB 后端 `timeout=3600s`；消耗额外头部即可支持WS/SSE。
- **各地组件**：服务器/锁/广播优先用Memorystore（Redis）；如需跨区域/持久化广播，可后续改用Cloud Pub/Sub。
- **数据库迁移**：使用 Cloud Build/Cloud Run Job 运行 Alembic 迁移，不在应用进程内自动迁移。

---

### 里程碑与惊喜
- **里程碑1**：引入Redis服务器与Pub/Sub；服务器/服务器跨实例一致。
- **里程碑2**：`AgentManager` 预热加分布式锁；订阅 `agent:invalidated`生效。
- **里程碑3**：体育广播改为Redis频道；WS/SSE在GCLB下稳定30+分钟。
- **欣赏**：
  - 多实例下更新代理配置，其他实例 1s 内预计失败。
  - 相似的会话连接可接收跨实例广播。
  - 流式/长链稳定，无异常5xx/断链高峰。

---

###风险与对策
- **缓存一致性**：采用“写后删缓存+事件广播”；读侧短TTL；发布/订阅按另外方式减轻分组风暴。
- **分布/双写**：DB 唯一约束 + 多重锁 + 权力等键（如`X-Idempotency-Key`）。
- **长连接中断**：粘性会话 + 长超时；客户端自动重连策略。
- **启动风暴**：仅 leader 预热；其余实例懒加载；设置 `min-instances`。

---

### 回滚策略
- 临时关闭Redis（降级为单实例或本地内存，仅限紧急回退）。
- 关闭订阅与广播逻辑（特性开关）；逐步缩小实例数至 1 观察。
- GCLB 切换为直连Cloud Run 修复窗口，问题解决之后回单一切多实例。