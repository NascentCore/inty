# DevOps 日常操作

## 查询用户 emotional needs profile

```
WITH latest AS (SELECT DISTINCT ON (m.user_id) m.user_id, m.created_at, m.content FROM memory m WHERE m.memory_type = 'user_common' AND m.content IS NOT NULL AND btrim(m.content) <> '' ORDER BY m.user_id, m.created_at DESC) SELECT user_id, created_at, content AS emotional_needs_profile FROM latest ORDER BY created_at DESC LIMIT 10;
```

## 创建 Email+Password （测试）用户

```bash
ssh inty
# 根据后端环境选择 dev 或者 prod
docker exec -it inty-backend-{dev|prod} bash
# 进入运行中的容器后：
export PYTHONPATH=.
python tools/scripts/create_email_password_superuser.py \
  --email test@sxwl.ai \
  --password sxwltest \
  --nickname "Free Test User" \        
  --is-superuser=false \
  --yes
```

## 手动操作 alembic versions

- 找到对应环境的 docker image
- `docker run -it <docker-image> bash`
- `export PYTHONPATH=.`
- 使用 `alembic -c backend/alembic/alembic.ini ...` 命令行来操作

## 重启后端服务器

1. 重启 GCE VM
2. 所有 docker 容器应该自动重启
3. 检查 app.inty.cc
4. 重启 GitHub self-hosted runner，使用 gcp web ssh 登录
   ```bash
   cd github-self-hosted-actions-runner
   nohup ./run.sh &
   tail -f nohup.out # 观察日至输出，确保服务正常启动
   ```
6. 确保 https://github.com/NascentCore/inty/actions/workflows/dify_chat_cron.yaml https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml 正常运行

## 修改 AI 角色

- 所有改动都在 <!-- TODO(!3499): dev.inty.sxwl.ai/evaluation no longer served --> https://dev.inty.sxwl.ai/evaluation 进行，然后由
  https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml
  同步到 prod
- [背景图片](https://applink.feishu.cn/client/message/link/open?token=AmTE5KCVRMAEaXdRy%2BdBDMg%3D)

## 创建新的 api key 给特定用户 id

```bash
ssh inty # 登录生产服务器
docker exec -it inty-backend-prod bash # 进入生产环境后端容器
# 每次运行都会生成新的 api key
# 生产环境，360 指有效的天数
python3 tools/scripts/generate_prod_token.py --env prod  user-01JWZ34Y4D1C92GD86A5R6EWYJ  360
# dev环境，360 指有效的天数
python3 tools/scripts/generate_prod_token.py --env dev  user-01JWZ34Y4D1C92GD86A5R6EWYJ 360 
```

## 增加数据连接数

现象是服务端错误日志“asyncpg.exceptions.TooManyConnectionsError: remaining connection slots are reserved for roles with privileges of the "pg_use_reserved_connections" role”，google cloud postgres 数据库实例连接数已满，同一实例下的多个库共用数据库连接数，需要修改实例的连接数配置，编辑实例，修改 max_connnection flag,等待实例重启完成，然后重启后端。

## 定期清理服务器上的 docker 缓存

```terminal
licairong@dev-instance:~$ docker system prune -a
WARNING! This will remove:
  - all stopped containers
  - all networks not used by at least one container
  - all images without at least one container associated to them
  - all build cache

Are you sure you want to continue? [y/N] y
...
```

## Docker pull 卡住

体现为 docker pull step github workflow 超时

![img_v3_02s4_5190d049-13cf-4553-96c4-1de32d770e7g](https://github.com/user-attachments/assets/09cc0d21-e8e0-4bd6-bf74-5318deadd834)

重启 docker daemon，并确保 docker daemon 重启后正常运行

```terminal
licairong@dev-instance:~$ sudo systemctl restart docker
licairong@dev-instance:~$ sudo systemctl status docker
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-11-17 05:13:19 UTC; 1min 56s ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 1198652 (dockerd)
      Tasks: 49
     Memory: 67.2M
        CPU: 2.159s
     CGroup: /system.slice/docker.service
             ├─1198652 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
             ├─1198879 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5432 -container-ip 172.17.0.5 -container-port 5432
             ├─1198885 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8100 -container-ip 172.17.0.4 -container-port 8000
             ├─1198902 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 5432 -container-ip 172.17.0.5 -container-port 5432
             └─1198907 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 8100 -container-ip 172.17.0.4 -container-port 8000
```

## 手动修改 chat settings（SQL）

聊天风格等设置存于表 `chat_settings`，按 `chat_id` 唯一。若需绕过 API（如订阅校验）直接改库，可按以下步骤操作。

**表与字段**（见 `app/models/chat_settings.py`）：

- `chat_settings.chat_id`：关联 `chats.id`，一个 chat 对应一行 settings
- `chat_settings.user_id`、`chat_settings.agent_id`：与 chat 一致
- `chat_settings.style_prompt`：风格提示词，可为空；有值时会在 `app/core/agent/agent.py` 的 `build_system_messages` 中注入为系统消息
- 其他：`language`、`voice_enabled`、`keep_talking`、`premium_mode` 等

**步骤：**

1. 确认该用户与该 agent 的 chat 已存在（若无，需先通过 API 或业务创建一条 chat）。
2. 根据 `user_id`、`agent_id` 找到 `chat_id`，再更新或确认存在对应的 `chat_settings` 行。
3. 执行更新 SQL。

**示例：为指定用户与 agent 设置 style_prompt**

```sql
-- 先查 chat_id（user_id / agent_id 按实际替换）
SELECT id AS chat_id FROM chats
WHERE user_id = 'user-testing'
  AND agent_id = 'agent-52cfa352'
  AND is_active = true
LIMIT 1;

-- 若该 chat 尚无 chat_settings，需先插入一行（id 用 UUID，其余字段按需填）
-- 若已有行，则直接更新 style_prompt：
UPDATE chat_settings
SET style_prompt = 'write very detailed and elaborate descriptions of actions and thoughts'
WHERE chat_id = (
  SELECT id FROM chats
  WHERE user_id = 'user-testing'
    AND agent_id = 'agent-52cfa352'
    AND is_active = true
  LIMIT 1
);
```

**注意：** 直接改库不经过 API，因此不会做订阅/超级用户校验；仅运维或调试时使用。

## IntelliMate 本地 Postgres（Docker）

IntelliMate dev（`inty-dev`）与 prod（`inty`）均在 VM 容器 `inty-pg`；完整说明见 [LOCAL_POSTGRES.md](LOCAL_POSTGRES.md)。

**推荐入口（幂等 / 可验证）**：

```bash
cd /path/to/inty
devops/scripts/ensure_inty_dev_postgres_container.sh
devops/scripts/verify_local_postgres_durability.sh
devops/scripts/verify_local_postgres_durability.sh --restart-test   # 迁移或 prod cutover 前
```

**禁止**：在 VM 上直接 `docker volume rm inty-dev-postgres-data` 或未加 guard 的 `docker volume prune`。若需 prune 其他 volume：

```bash
devops/scripts/guard_docker_volume_prune.sh && docker volume prune
# guard 检测到 inty-dev-postgres-data 时会 exit 1，阻止 prune
```

**每日备份 / 每周巡检**：由 GitHub Actions [`.github/workflows/local_postgres_maintenance.yaml`](../.github/workflows/local_postgres_maintenance.yaml) 在 `inty-prod-server-gcp` 上定时执行（UTC 03:15 备份（含 14 天 dump 清理）；UTC 周日 04:00 耐久性 verify）。`task: all` 时 verify 在 backup 完成后串行执行。可 **Actions → Local Postgres maintenance → Run workflow** 手动触发（`restart_test: true` 等价于 `--restart-test`）。

常用命令：

```bash
docker start inty-pg
docker stop inty-pg
PGPASSWORD='<见 config.yaml.dev / config.yaml.prod>' psql -h localhost -U postgres -d inty-dev
PGPASSWORD='<见 config.yaml.prod>' psql -h localhost -U postgres -d inty
```

**Cloud SQL → 本地增量同步**（`created_at` cutoff，见 [LOCAL_POSTGRES.md](LOCAL_POSTGRES.md)）：

```bash
devops/scripts/sync_cloudsql_inty_incremental.sh --check-only
devops/scripts/sync_cloudsql_inty_incremental.sh --apply
```

## 迁移已有后端数据库到一个新的服务器

大体流程：

1. 初始化数据库 schema
2. 转移数据

### 初始化数据库 schema

1. 准备一个新的 config.yaml.new 文件，修改其 数据库 指向新的数据库实例
2. 使用最新的后端容器镜像，启动 bash

   ```bash
   docker run -it -v $(pwd)/config.yaml.new:/config.yaml ghcr.io/nascentcore/inty-backend/inty-server:main-dev
   ```

   这个命令会启动后端服务，后端服务启动初期会初始化数据库 schema

### 从 Cloud SQL 同步 IntelliMate dev / prod 到本地 Docker

见 [LOCAL_POSTGRES.md](LOCAL_POSTGRES.md)。要点：用 `postgres:17` 容器做 `pg_dump` / `pg_restore`；本地运行镜像为 `pgvector/pgvector:pg17`；`ensure_inty_dev_postgres_container.sh` 负责容器与 config 密码对齐。

### 通用 dump / restore 示例

```bash
docker run --rm -e PGPASSWORD=<password> --network host postgres:17 pg_dump -h <source-host> -p 5432 -U postgres -d <source-db> -Fc -f /tmp/devdb.dump
docker run --rm -e PGPASSWORD=<password> --network host -v /tmp:/tmp postgres:17 pg_restore -h localhost -p 5432 -U postgres -d inty-dev --clean --if-exists --no-owner --no-privileges /tmp/devdb.dump
```
