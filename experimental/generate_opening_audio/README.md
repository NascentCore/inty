# 批量生成开场白语音工具

这个工具用于为数据库中 `opening_audio_url` 为空的 agents 批量生成开场白语音。

## 功能特性

- ✅ 从根目录 `config.yaml` 读取数据库和 ElevenLabs 配置
- ✅ 查询 `opening_audio_url` 为 NULL 且有开场白文本的 agents
- ✅ 复用现有的 `VoiceService` 和语音生成逻辑
- ✅ 自动处理 Jinja2 模板变量（`{{ char }}`, `{{ user }}`）
- ✅ 根据 agent 的 `voice_id` 或性别选择音色
- ✅ 批量处理支持（默认 10 个/批）
- ✅ Dry-run 模式（只查询和生成语音，不更新数据库）
- ✅ 详细的进度显示和日志
- ✅ 单个失败不影响其他处理
- ✅ 支持语音缓存复用

## 使用方法

### 前置要求

1. 确保已安装项目依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 确保 `config.yaml` 中配置了正确的数据库和 ElevenLabs API 信息：
   ```yaml
   database:
     host: localhost
     port: 5432
     user: postgres
     password: your_password
     db: your_database

   elevenlabs:
     api_key: "your_elevenlabs_api_key"
     enabled: true
   ```

### 基本用法

#### 1. 查看需要处理的 agents 数量（Dry-run）

推荐首先使用 dry-run 模式查看有多少 agents 需要生成语音：

```bash
python generate_missing_opening_audio.py --dry-run
```

这会生成语音但不会保存到数据库，可以验证配置是否正确。

#### 2. 生成所有缺失的开场白语音

```bash
python generate_missing_opening_audio.py
```

#### 3. 只处理前 N 个 agents（测试用）

```bash
python generate_missing_opening_audio.py --limit 5
```

#### 4. 为指定的 agent 生成语音

```bash
python generate_missing_opening_audio.py --agent-id <agent-id>
```

#### 5. 使用自定义配置文件

```bash
python generate_missing_opening_audio.py --config /path/to/config.yaml
```

#### 6. 自定义批处理大小

```bash
python generate_missing_opening_audio.py --batch-size 20
```

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | string | `../../config.yaml` | 配置文件路径 |
| `--batch-size` | int | `10` | 每批处理的数量 |
| `--dry-run` | flag | `false` | 只查询和生成语音，不更新数据库 |
| `--limit` | int | 无 | 限制处理的数量（用于测试） |
| `--agent-id` | string | 无 | 只处理指定的 agent ID |

### 查看帮助

```bash
python generate_missing_opening_audio.py --help
```

## 工作流程

1. **加载配置**：从 `config.yaml` 读取数据库和 ElevenLabs 配置
2. **连接数据库**：使用 SQLAlchemy AsyncSession 连接数据库
3. **查询 agents**：查找满足以下条件的 agents：
   - `deleted_at IS NULL`（未删除）
   - `opening IS NOT NULL` 且 `opening != ''`（有开场白文本）
   - `opening_audio_url IS NULL`（没有语音 URL）
4. **批量处理**：按批次处理 agents（默认 10 个/批）
   - 处理 Jinja2 模板变量（`{{ char }}` → agent.name, `{{ user }}` → "you"）
   - 确定 voice_id（优先使用 agent.voice_id，否则根据性别选择默认值）
   - 调用 VoiceService 生成语音
   - 上传到 GCS 并获取 URL
   - 更新数据库（非 dry-run 模式）
5. **输出统计**：显示处理结果统计

## 日志和输出

脚本会输出详细的日志信息，包括：

- 配置加载状态
- 数据库连接状态
- 需要处理的 agents 数量
- 每个 agent 的处理进度
- 生成的语音 URL 和时长
- 成功/失败/跳过的统计

示例输出：

```
============================================================
开场白语音批量生成工具
============================================================
2025-01-11 10:00:00 | INFO     | 加载配置文件: /path/to/config.yaml
2025-01-11 10:00:00 | INFO     | 配置加载成功
2025-01-11 10:00:00 | INFO     | 连接数据库: localhost:5432/inty_prd
2025-01-11 10:00:01 | INFO     | 数据库连接建立成功
2025-01-11 10:00:01 | INFO     | ElevenLabs 语音服务已启用
2025-01-11 10:00:02 | INFO     | 找到 42 个需要生成语音的 Agents
2025-01-11 10:00:02 | INFO     | 本次将处理 42 个 Agents
------------------------------------------------------------

批次 1/5: 处理 10 个 Agents
------------------------------------------------------------
2025-01-11 10:00:03 | INFO     | [1/10] 处理 Agent abc-123 (小雨)
2025-01-11 10:00:05 | INFO     | ✓ Agent abc-123 (小雨) 语音生成成功: gs://... [时长: 3.45秒]
...

============================================================
处理完成！统计信息：
  总数: 42
  已处理: 42
  成功: 40
  失败: 1
  跳过: 1
  耗时: 125.67 秒
============================================================
```

## 错误处理

- **单个 agent 失败**：不会中断整个批次，会记录错误并继续处理下一个
- **数据库连接失败**：脚本会退出并显示错误信息
- **ElevenLabs API 失败**：会记录错误，该 agent 标记为失败
- **配置文件不存在**：脚本会退出并提示配置文件路径

## 注意事项

1. **API 配额**：ElevenLabs API 有调用限制，大量处理时注意配额
2. **网络连接**：需要稳定的网络连接以访问 ElevenLabs API 和 GCS
3. **数据库权限**：需要对 `agents` 表有 SELECT 和 UPDATE 权限
4. **模板变量**：开场白中的 `{{ char }}` 会替换为 agent 名字，`{{ user }}` 会替换为 "you"
5. **voice_id 选择**：
   - 优先使用 agent 自己的 `voice_id`
   - 如果没有，根据性别使用默认值：
     - MALE → `rHWSYoq8UlV0YIBKMryp`
     - FEMALE → `4tRn1lSkEn13EVTuqb0g`
     - OTHER → `O7p2vmz2iEYgMXxkbsif`
6. **语音缓存**：如果相同文本和音色已生成过语音，会复用缓存

## 安全建议

- 在生产环境运行前，先使用 `--dry-run` 和 `--limit` 测试
- 建议先在测试数据库上运行
- 定期备份数据库
- 监控 API 调用配额

## 疑难解答

### 配置文件找不到

确保配置文件路径正确。默认路径是相对于脚本的 `../../config.yaml`（即项目根目录）。

### 数据库连接失败

检查 `config.yaml` 中的数据库配置，确保数据库服务正在运行。

### ElevenLabs API 错误

检查：
1. API key 是否正确
2. `elevenlabs.enabled` 是否为 `true`
3. 网络连接是否正常
4. API 配额是否充足

### 语音生成失败

检查日志中的详细错误信息。常见原因：
- 文本长度超过限制（默认 5000 字符）
- voice_id 无效
- 网络超时

## 技术实现

### 依赖模块

- `sqlalchemy` - 数据库操作
- `asyncpg` - PostgreSQL 异步驱动
- `pyyaml` - 配置文件解析
- `loguru` - 日志记录
- 项目内部模块：
  - `app.models.agent.Agent` - Agent 模型
  - `app.services.voice_service.VoiceService` - 语音服务
  - `app.core.agent.prompt_template` - 模板处理

### 数据库查询

```sql
SELECT * FROM agents
WHERE deleted_at IS NULL
  AND opening IS NOT NULL
  AND opening != ''
  AND opening_audio_url IS NULL
ORDER BY created_at DESC;
```

## 相关文档

- [ElevenLabs API 文档](https://docs.elevenlabs.io/)
- [语音服务实现](../../app/services/voice_service.py)
- [Agent 模型定义](../../app/models/agent.py)
- [创建 Agent 时的语音生成逻辑](../../app/services/agent_service.py)

## 贡献

如有问题或建议，请联系开发团队。
