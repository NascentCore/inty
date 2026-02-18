# 记忆抽取消息数量限制功能

## 问题背景

生产环境日志显示记忆抽取时出现 token 超限错误：

```
Error code: 400 - {'error': {'message': 'This endpoint\'s maximum context length is 262144 tokens. 
However, you requested about 292596 tokens (288596 of text input, 4000 in the output). 
Please reduce the length of either one, or use the "middle-out" transform to compress your prompt automatically.', 'code': 400}}
```

- 错误位置：`app/services/memory_extraction_service.py:extract_and_save:349`
- 根本原因：`get_all_messages_for_user()` 拉取用户**所有历史消息**，无数量限制
- 影响：当用户消息数过多时（如数千条），会超过 LLM endpoint 的 token 限制（~260k tokens）

## 解决方案

添加消息数量限制配置，在拉取消息时只保留最新的 N 条消息。

### 1. 配置新增

在 `app/utils/config.py` 的 `MemoryExtractionConfig` 中新增：

```python
max_messages_for_extraction: int = 1000  # 单次记忆抽取允许的最大消息数
```

- 默认值：1000 条消息
- 可通过 `config.yaml` 中的 `memory_extraction.max_messages_for_extraction` 配置
- 设为 `None` 或不配置时，保持原有行为（不限制）

### 2. 函数签名更新

#### `get_all_messages_for_user()`

```python
def get_all_messages_for_user(
    user_id: str, 
    prefer_replica_read: bool = False, 
    max_messages: Optional[int] = None  # 新增参数
) -> List[Tuple[str, str]]:
```

- `max_messages=None`：不限制消息数量（向后兼容）
- `max_messages=N`：仅返回最新的 N 条消息

#### `extract_and_save()`

```python
async def extract_and_save(
    db: AsyncSession, user_id: str, prefer_replica_read: bool = False
) -> None:
    cfg = getattr(global_config_loaded_from_config_yaml, "memory_extraction", None)
    max_messages = getattr(cfg, "max_messages_for_extraction", None)
    messages = await asyncio.to_thread(
        get_all_messages_for_user, user_id, prefer_replica_read, max_messages
    )
    # ... 后续处理
```

### 3. SQL 查询优化

当 `max_messages` 有限制时，使用子查询 + LIMIT 获取最新的 N 条消息：

```sql
-- 有限制时 (max_messages = 1000)
SELECT message FROM (
    SELECT message, created_at
    FROM chat_history
    WHERE session_id::text IN (...) AND deleted_at IS NULL
    ORDER BY created_at ASC
) AS all_messages
ORDER BY created_at DESC
LIMIT 1000
```

- 子查询：按时间升序获取所有消息
- 外层查询：按时间降序排列，LIMIT N 取最新的 N 条
- Python 代码：反转结果，保持最终输出按时间升序

```sql
-- 无限制时 (max_messages = None)
SELECT message
FROM chat_history
WHERE session_id::text IN (...) AND deleted_at IS NULL
ORDER BY created_at ASC
```

### 4. 测试覆盖

新增测试文件：`tests/app/services/test_memory_extraction_message_limit.py`

测试用例：
- `test_get_all_messages_respects_max_messages_limit()` - 验证消息限制功能
- `test_get_all_messages_no_limit_when_max_messages_none()` - 验证无限制场景
- `test_get_all_messages_query_includes_limit_clause()` - 验证 SQL 查询正确性

## 使用方式

### 默认配置（推荐）

不需要修改配置文件，使用默认值 1000 条消息：

```yaml
# config.yaml 中不配置或留空
memory_extraction:
  enabled: true
  cron_hour: 3
  # max_messages_for_extraction 使用默认值 1000
```

### 自定义配置

如需调整消息数量限制，在 `config.yaml` 中配置：

```yaml
memory_extraction:
  enabled: true
  cron_hour: 3
  max_messages_for_extraction: 2000  # 自定义为 2000 条
```

### 完全不限制（不推荐）

虽然支持，但不推荐在生产环境使用：

```yaml
memory_extraction:
  enabled: true
  cron_hour: 3
  max_messages_for_extraction: null  # 或设为很大的数字
```

## 技术细节

### 为什么选择保留最新消息？

1. **相关性更高**：最新消息更能反映用户当前的兴趣和状态
2. **记忆一致性**：用户近期的行为模式比早期更稳定
3. **技术实现简单**：使用 `ORDER BY created_at DESC LIMIT N` 即可

### 为什么默认 1000 条？

根据经验估算：
- 平均每条消息 ~100 tokens
- 1000 条消息 ≈ 100k tokens
- 加上提示词（~3k tokens）≈ 103k tokens
- 远低于大多数 LLM 的上下文限制（260k+ tokens）
- 为特别活跃用户留出足够空间

### 向后兼容性

- 现有代码调用 `get_all_messages_for_user()` 无需修改（默认 `max_messages=None`）
- 现有配置文件无需修改（使用默认值 1000）
- 数据库查询逻辑向后兼容（`max_messages=None` 时不添加 LIMIT）

## 部署说明

### 生产环境部署

1. 合并 PR 后自动部署
2. 配置会使用默认值 `max_messages_for_extraction: 1000`
3. 如需调整，修改生产配置文件 `devops/config.yaml.prod`

### 监控指标

可通过 `memory_extraction_log` 表监控效果：

```sql
-- 查看消息数量分布
SELECT 
    messages_processed_count,
    COUNT(*) as extraction_count
FROM memory_extraction_log
WHERE extracted_at > NOW() - INTERVAL '7 days'
GROUP BY messages_processed_count
ORDER BY messages_processed_count DESC;

-- 查看 token 使用情况
SELECT 
    AVG(prompt_tokens) as avg_prompt_tokens,
    MAX(prompt_tokens) as max_prompt_tokens
FROM memory_extraction_log
WHERE extracted_at > NOW() - INTERVAL '7 days'
  AND status = 'success';
```

## 相关文件

- `app/utils/config.py` - 配置类定义
- `app/services/memory_extraction_service.py` - 核心逻辑实现  
- `tests/app/services/test_memory_extraction_message_limit.py` - 单元测试
- `evaluation/docs/MEMORY_FEATURE_IMPLEMENTATION_SUMMARY.md` - 功能文档更新
- `docs/FR_MESSAGE_LIMIT.md` - 本文档（功能需求）

## 未来优化方向

1. **智能采样**：不仅保留最新消息，还可以采样历史重要消息
2. **动态调整**：根据 token 使用情况动态调整消息数量
3. **分段抽取**：对超长历史分段抽取，再合并记忆
4. **压缩技术**：使用 LLM 的 "middle-out" 压缩功能
