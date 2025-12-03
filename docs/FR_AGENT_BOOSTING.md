# CREATED_BY_AGENT

# FR_AGENT_BOOSTING

## 背景
- Explore 页面新增 Boost 榜单，需要在同一接口返回精选和 Boost 两类角色列表
- Boost 榜单展示积分最高的前 N（默认 10）个角色

## 数据库
- `agents` 表新增整型字段 `points`，默认值 0，用于记录 Boost 积分
- 通过 Alembic 版本 `20251203_061500_add_points_to_agents.py` 管理 schema 变更

## API
- `/api/v1/ai/agents/recommend` 与 `/api/v2/ai/agents/recommend` 请求新增 `types`（数组）与 `boost_limit` 参数
  - `types` 支持 `FEATURED`、`BOOSTED`，按请求顺序返回对应列表
  - `boost_limit` 控制 Boost 榜单返回数量，默认 10，上限 50
- 响应结构升级为列表形式：`[{ "type": "FEATURED", "data": PaginationData }, ...]`
- `BOOSTED` 列表按照积分降序返回角色，不会混入精选数据

## 响应字段
- `Agent`/`AgentInfo` Pydantic 模型新增只读字段 `points`，用于前端展示积分
