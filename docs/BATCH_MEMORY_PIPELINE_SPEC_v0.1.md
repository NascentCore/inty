Batch Memory Pipeline Spec（v0.1）

1) 目标与边界
目标
把离线记忆生成迁移到 Vertex Gemini Batch，优先覆盖：

user_common 抽取（当前每日调度）
festival 抽取（当前 5 分钟扫描配置）
后续 daily_bonding 自动写入链路（当前文档已规划、实现未完成）push_scheduler_service.py:169-201 push_scheduler_service.py:393-537 FR_DAILY_MEMORY_BONDING.md:25-30
非目标
不改在线聊天/消息接口的“按需投递”路径（delivery_at + *_memory_prompt）
不把实时回复迁移到 batchmemory_service.py:129-133 memory_service.py:408-480 memory_service.py:561-619
2) 为什么现在就值得做（硬约束）
Vertex batch 的关键约束与你场景匹配：

成本：batch 相比实时推理约 50% 折扣
容量：单作业最多 200,000 requests
时效：异步，不适合实时；运行后通常 24h 内完成
Cloud Storage 输入时有 1GB 上限
高峰会排队，队列最长可到 72h6e1c4fe9-eb5a-4797-948a-cd8e820e72be.txt:8-34
输入输出形态也完全可用：

GCS：instancesFormat=jsonl（一行一个请求）
BigQuery：instancesFormat=bigquery
输出可写回 GCS 或 BigQuerye08fda65-62bc-4526-94aa-e8451c358e83.txt:3-9 e08fda65-62bc-4526-94aa-e8451c358e83.txt:69-93
3) 目标架构（推荐）
Candidate Selector（Cloud Run Job A）

复用你现有筛选逻辑（get_users_to_extract / festival pair selector）
输出到 bq.memory_batch_requests（或 GCS JSONL）memory_extraction_service.py:301-347 festival_memory_service.py:86-95
Vertex Batch Submitter（Cloud Run Job B）

按 memory_type 分批提交 BatchPredictionJob
存 batch_job_id + source snapshot id
Result Importer（Cloud Run Job C）

拉取 batch output（BQ/GCS）
解析、校验、映射到 memory + memory_extraction_log
幂等 upsert（见第 5 节）
Orchestrator（Cloud Scheduler + Cloud Run Jobs）

你仓库已有 Cloud Run Job + Scheduler 实践可直接复用README.md:1-4 README.md:52-60 README.md:82-91
4) 批处理数据契约（建议）
Request（统一）
字段：

request_id（UUID，幂等主键）
memory_type (user_common|festival|daily_bonding)
user_id
agent_id（user_common 可空）
metadata_json（festival/date、local_date、timezone等）
prompt_text（完整 prompt）
model（可覆盖）
created_at
Response（统一）
字段：

request_id
status (success|failed|invalid_output)
raw_output_text
parsed_content（最终 memory content）
prompt_tokens
completion_tokens
error_message
finished_at
5) 幂等与写库策略（核心）
user_common
保持你当前语义：同一用户仅保留最新一条；导入时执行“删除旧 + 插入新”。memory_extraction_service.py:425-457

festival
按 (user_id, agent_id, festival_name, festival_date) 去重覆盖（你已有 _find_festival_memory_ids 逻辑可复用）。festival_memory_service.py:349-375 festival_memory_service.py:403-413

daily_bonding
按文档目标加唯一性：(user_id, agent_id, memory_type, local_date)，保证一天最多一条。FR_DAILY_MEMORY_BONDING.md:59-60 FR_DAILY_MEMORY_BONDING_IMPLEMENTATION.md:113-117

重要原则
导入任务失败不影响在线聊天：在线只读 memory 现有数据
delivery_at 仍由在线“按需投递”更新，不在 batch 中改memory_service.py:129-133 memory_service.py:474-480
6) 与现有代码映射（最小改造路径）
替换 _run_memory_extraction 内部执行方式：

现在：逐用户实时调用 extract_and_save
改为：构建 batch request -> 提交 job -> 异步导入结果push_scheduler_service.py:393-423 memory_extraction_service.py:349-457
替换 _run_festival_memory_extraction 的逐 pair LLM 调用：

候选 pair 计算与配置占位逻辑保持不变
仅把 extract_festival_and_save 改成 batch pipelinepush_scheduler_service.py:471-537
daily_bonding 写入链路直接 batch-native 实现（别再先做同步版再迁移）。FR_DAILY_MEMORY_BONDING.md:25-30

7) 调度建议（结合 batch SLA）
user_common：每日 1 次（可凌晨）
festival：建议提早触发（例如节日后窗口结束即提交），避免排队导致迟到
daily_bonding：按“本地日关闭后”批量触发（你文档建议约 local 04:05）FR_DAILY_MEMORY_BONDING.md:73-75
因为 queue 可能到 72h，业务上要接受“迟到但可达”；若某些场景强时效，保留小规模同步兜底通道。

8) 风险与控制
输出格式漂移

继续使用 structured-output schema 思路（你当前已在 user_common 使用）memory_extraction_service.py:35-59 memory_extraction_service.py:383-399
批作业超大失败

大任务按 request_count 分片（如 50k/片）
每片独立 job_id，可重跑
数据驻留要求

需要驻留就不要用 global endpoint（官方说明 global 不满足驻留）6e1c4fe9-eb5a-4797-948a-cd8e820e72be.txt:20-23
在线体验回退

batch 未产出时继续使用旧 memory，不阻断 chat API
9) 两周落地计划（建议）
Week 1
建 memory_batch_requests/results/jobs 三张表（或 BigQuery 同名表）
完成 user_common batch 端到端（submit + import + 幂等）
对齐 memory_extraction_log 指标写入
Week 2
接 festival batch
实现 daily_bonding batch 写入（同时补唯一索引）
加监控面板：成功率、延迟、token、失败类型、重跑次数
如果你同意，我下一步可以直接给你：

表结构 SQL（Postgres + BigQuery）
3 个 Cloud Run Job 的最小 Python 骨架
把 push_scheduler_service 改成“提交批任务而不是逐条调用 LLM” 的具体 patch 方案。
