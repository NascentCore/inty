# 记忆提示词评测工具

CREATED_BY_AGENT

测试不同记忆提示词对 AI 角色对话效果的影响。通过提取用户历史对话生成记忆，对比有记忆和无记忆情况下与新角色对话的效果差异。

## 功能

1. **用户选择**：支持通过邮箱指定用户或按聊天数量选择活跃用户
2. **记忆提取**：使用 LLM 从用户与所有角色的聊天历史中提取用户记忆
3. **对话模拟**：使用 8 个标准测试问题，分别在有记忆和无记忆情况下与新角色对话
4. **效果对比**：生成详细的 Markdown 报告，对比两种情况下的对话效果

## 安装

```bash
cd experimental/memory_prompt_benchmark
pip install -r requirements.txt
```

## 使用方法

### 运行评测

```bash
# 按聊天数选择前 20 个用户（默认）
python benchmark.py run --top 20

# 指定用户邮箱
python benchmark.py run --emails "user1@example.com,user2@example.com"

# 使用自定义记忆提取提示词
python benchmark.py run --top 10 --memory-prompt prompts/custom.txt

# 指定 LLM 模型
python benchmark.py run --top 5 --model "anthropic/claude-3-haiku"
```

### 列出用户

```bash
# 列出消息数最多的 50 个用户
python benchmark.py list-users --top 50
```

### 重新生成报告

```bash
# 从已有结果重新生成报告
python benchmark.py report --dir results/20260122_123456
```

## 配置

工具读取项目根目录的 `config.yaml` 配置文件，使用以下配置项：

- `database.*`：数据库连接配置
- `agent.api_key`：OpenRouter API 密钥
- `agent.base_url`：OpenRouter API 地址
- `agent.model`：默认 LLM 模型

## 测试问题

每个用户会使用以下 8 个问题进行测试（每个问题是独立的单轮对话）：

1. Hey! Nice to meet you~
2. I've been feeling stressed lately...
3. I've been feeling really stressed lately...
4. Tell me something interesting.
5. What do you think we should talk about?
6. Let's talk about rejection of infidelity
7. Do you think you really understand me?
8. Hi, I just want to chat. What's on your mind?

## 输出

评测结果保存在 `results/<timestamp>/` 目录下：

- `report.md`：Markdown 格式的评测报告
- `raw_data.json`：原始数据（JSON 格式）

### 报告内容

1. **测试概览**：用户列表、消息数、聊天历史字数
2. **用户详情**：
   - 用户基本信息
   - 提取的用户记忆（摘要 + 完整分析）
   - 8 组对话对比（有记忆 vs 无记忆）
3. **分析结论**：评估记忆提示词的效果

## 自定义记忆提示词

默认的记忆提取提示词位于 `prompts/default_memory.txt`。你可以创建自定义提示词文件，然后通过 `--memory-prompt` 参数指定。

提示词应该指导 LLM 从聊天历史中提取：

- 用户基本信息（称呼、性别、职业等）
- 对话风格偏好
- 兴趣与话题偏好
- 情感需求与动机
- 敏感话题与禁忌
- 行为模式
- 与 AI 角色的互动特点

## 目录结构

```
memory_prompt_benchmark/
├── README.md                # 本文件
├── requirements.txt         # Python 依赖
├── config.py               # 配置读取
├── benchmark.py            # CLI 入口
├── db_service.py           # 数据库查询
├── memory_extractor.py     # 记忆提取
├── chat_simulator.py       # 对话模拟
├── report_generator.py     # 报告生成
├── prompts/
│   └── default_memory.txt  # 默认记忆提取提示词
└── results/                # 评测结果
```

## 注意事项

1. 确保数据库连接配置正确
2. 确保 OpenRouter API 密钥有效
3. 处理大量用户时可能需要较长时间（每个用户约 1-2 分钟）
4. 聊天历史较长的用户可能需要更多的 API 调用

## Tool Trigger 对比评测（flat vs layered memory）

新增脚本：`tool_trigger_benchmark.py`

用途：
- 固定一组“应触发工具 / 不应触发工具”查询；
- 比较两种 memory 注入结构下的工具触发率：
  - `flat`：非结构化记忆块
  - `layered`：core/profile/episodic/tool_affinity 分层记忆
- 输出 `report.md` 和 `raw_data.json`。

运行示例（按你的配置要求）：

```bash
/workspace/.venv/bin/python experimental/memory_prompt_benchmark/tool_trigger_benchmark.py \
  --config devops/config.yaml.dev \
  --model "google/gemini-2.5-flash" \
  --samples-per-case 4 \
  --temperature 0.4
```

脚本会优先读取环境变量中的 `OPENROUTER_API_KEY` / `OPENAI_API_KEY`，否则回退到 `devops/config.yaml.dev` 的 `agent.api_key`。

关键指标：
- Trigger rate when needed（应触发时触发率）
- False trigger rate when not needed（不应触发时误触发率）
- Expected tool match rate（应触发场景下，工具命中率）
