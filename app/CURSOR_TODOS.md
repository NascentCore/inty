### 架构（FastAPI）架构级 TODO（app 根）

#### P0（必须本期完成）

- [ ] 架构分层与边界
  - [ ] 明确`api/`、`schemas/`、`services/`、`models/`、`utils/`、`middleware/`、`external_services/` 职责
  - [ ] 建立跨层依赖禁止清单与 CI 检查
- [ ] 依赖注入
  - [ ] 统一使用 FastAPI `Depends`暴露服务/存储库；规范生命周期
  - [ ] 清理全局单例与隐式依赖
- [ ] 配置管理
  - [ ] 固化`settings.llm_config`与全局配置优先级
  - [ ] 区分 dev/staging/prod 环境与密钥管理
- [ ] 模型统一错误
  - [ ]`{code, message, details, request_id}`响应模型与异常中间件
  - [ ] HTTP状态映射与规范日志关联
- [ ] 可启动性与追踪
  - [ ] OpenTelemetry Trace/Metrics/Logs 接入
  - [ ]`x-request-id` 贯穿与结构化日志
- [ ] 数据与迁移
  - [ ] Alembic 版本命名/审查流程与自动迁移校验
  - [ ] 外键/索引治理与数据修复脚本库
- [ ] 合同/集成测试
  - [ ] 与 Android 契约测试打通；外部服务打桩
  - [ ] E2E 回归与回放基线

#### P1（高优先）

- [ ] 连接与性能
  - [ ] SQLAlchemy 连接池/超时与 N+1 检测
  - [ ] 分页/游标统一（含确定性排序）
- [ ] 缓存层
  - [ ] Redis 键命名规范/TTL/失效策略；防击穿/雪崩与热点监控
- [ ] 幂等与重试
  - [ ] 写接口幂等键与 `Idempotency-Key`规范
  - [ ] 任务重试与去重策略
- [ ] 后台任务
  - [ ] 选择队列（Celery/RQ/Arq）并标准化
  - [ ] 任务状态表、可视化、失败同样
- [ ] 资源与媒体
  - [ ] CDN/GCS 路径归一化；尺寸信息补齐
  - [ ] 上传/下载限速与损耗

#### P2（中优先）

- [ ] 语音系统
  - [ ] ElevenLabs 客户端复用；队列排列；队列与回退；用量记录
- [ ] 角色卡与提示词
  - [ ] 体系混音（main/mode/output_format）标准化；SillyTavern V2 兼容
- [ ] 代理管理器
  - [ ]实例服务器/闲置清理；强制重载；更新后服务器故障一致性
- [ ] RAI/安全
  - [ ]输入校验与内容过滤；请求大小/速率限制；审计日志
- [ ] 流式接口
  - [ ] SSE/WebSocket协议统一（心跳/重连/鉴权/限流）
- [ ] CI/CD
  - [ ] pre-commit/删除/类型检查（ruff/mypy）；版本化与回滚/迁移手册
- [ ] 文档化
  - [ ] 开发者指南、API 变更说明与迁移路线自动生成