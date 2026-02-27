-- CREATED_BY_AGENT
-- A/B 测试对比分析：minimax-m2-her vs gemini-2.5-flash-lite
-- 测试周期：2026-02-07 ~ 2026-02-26
-- 变量1：对话模型（minimax-m2-her / gemini-2.5-flash-lite）
-- 变量2：角色创建渠道（人工创建 / 自动创建）
--
-- 前置条件：需要启用 uuid-ossp 扩展（用于将 chat_id 映射到 session_id）
-- 如果未启用，先执行: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
--
-- ⚠️ 注意：以下角色 ID 从测试方案截图中提取，部分 ID 可能因图片压缩导致
-- 字符不清晰。请先运行 Query 0 验证所有 ID 是否存在于数据库中，
-- 如有缺失请手动修正。


-- ============================================================
-- Query 0: 验证角色 ID 是否正确存在
-- 先运行此查询，确认 20 个角色 ID 都能查到
-- ============================================================
SELECT id, name, source, created_at
FROM agents
WHERE id IN (
    -- 组1: minimax-m2-her + 人工创建
    '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
    '24735102-e08b-489c-b8c0-19ab837ee1f6',
    '2da8c51d-0917-4225-84b3-a42a7988fb912',
    '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
    'c2734505-a8b2-4316-8931-6ebbe11c336e',
    -- 组2: minimax-m2-her + 自动创建
    '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
    'd8fba8d5-5836-4398-aa6b-cdb0b0268f683',
    '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
    '1a431b04-c454-48dc-a17d-a62bf00bb3fc',
    '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
    -- 组3: gemini-2.5-flash-lite + 人工创建
    'ede49321-0183-4117-8a66-3b3364b1a1a3',
    '23649e0f-1e86-4e1c-b8bc-d83d19d93372',
    '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a',
    '6e628aa7-366b-405b-914b-fd1a99a6b408',
    'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e',
    -- 组4: gemini-2.5-flash-lite + 自动创建
    '22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
    '0fb3ee22-13f5-4072-ab6c-cc79304a0310',
    'b1a89922-44c5-4b4f-beb1-9712b97900e57',
    '7eeed630-6358-4956-90dc-b127a1c6c77c',
    '0191e798-0352-4b72-9d43-bbd0511754ee'
)
ORDER BY source, name;


-- ============================================================
-- Query 1: 四组总览对比（核心指标）
-- 每组的聊天用户数、总聊天轮数、人均轮数、会话深度
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        a.name AS agent_name,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
                '24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912',
                '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e'
            ) THEN '组1: minimax + 人工'
            WHEN c.agent_id IN (
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
                'd8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
                '1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN '组2: minimax + 自动'
            WHEN c.agent_id IN (
                'ede49321-0183-4117-8a66-3b3364b1a1a3',
                '23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a',
                '6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '组3: gemini + 人工'
            WHEN c.agent_id IN (
                '22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
                '0fb3ee22-13f5-4072-ab6c-cc79304a0310',
                'b1a89922-44c5-4b4f-beb1-9712b97900e57',
                '7eeed630-6358-4956-90dc-b127a1c6c77c',
                '0191e798-0352-4b72-9d43-bbd0511754ee'
            ) THEN '组4: gemini + 自动'
        END AS group_label,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
                '24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912',
                '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e',
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
                'd8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
                '1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN 'minimax-m2-her'
            ELSE 'gemini-2.5-flash-lite'
        END AS model,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
                '24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912',
                '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e',
                'ede49321-0183-4117-8a66-3b3364b1a1a3',
                '23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a',
                '6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '人工创建'
            ELSE '自动创建'
        END AS source_type
    FROM chats c
    JOIN agents a ON c.agent_id = a.id
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
        '24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912',
        '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e',
        '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683',
        '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc',
        '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3',
        '23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a',
        '6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e',
        '22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310',
        'b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c',
        '0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
chat_rounds AS (
    SELECT
        eg.chat_id,
        eg.user_id,
        eg.agent_id,
        eg.agent_name,
        eg.group_label,
        eg.model,
        eg.source_type,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' = 'human'
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS user_rounds,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' IN ('ai', 'AIMessage')
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS ai_rounds
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    GROUP BY eg.chat_id, eg.user_id, eg.agent_id, eg.agent_name, eg.group_label, eg.model, eg.source_type
)
SELECT
    group_label AS "实验组",
    model AS "模型",
    source_type AS "创建渠道",
    COUNT(DISTINCT user_id) AS "聊天用户数",
    COUNT(DISTINCT chat_id) AS "会话数",
    SUM(user_rounds) AS "总用户消息轮数",
    SUM(ai_rounds) AS "总AI回复轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS "人均用户轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT chat_id), 0), 2) AS "每会话平均轮数",
    COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 5) AS ">=5轮会话数",
    COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 10) AS ">=10轮会话数",
    COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 20) AS ">=20轮会话数",
    ROUND(
        COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 5)::numeric * 100
        / NULLIF(COUNT(DISTINCT chat_id), 0), 1
    ) AS ">=5轮占比%",
    ROUND(
        COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 10)::numeric * 100
        / NULLIF(COUNT(DISTINCT chat_id), 0), 1
    ) AS ">=10轮占比%"
FROM chat_rounds
GROUP BY group_label, model, source_type
ORDER BY group_label;


-- ============================================================
-- Query 1b: 按模型维度汇总对比（忽略创建渠道）
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
                '24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912',
                '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e',
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
                'd8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
                '1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN 'minimax-m2-her'
            ELSE 'gemini-2.5-flash-lite'
        END AS model
    FROM chats c
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
chat_rounds AS (
    SELECT
        eg.chat_id,
        eg.user_id,
        eg.model,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' = 'human'
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS user_rounds
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    GROUP BY eg.chat_id, eg.user_id, eg.model
)
SELECT
    model AS "模型",
    COUNT(DISTINCT user_id) AS "聊天用户数",
    SUM(user_rounds) AS "总用户轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS "人均轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT chat_id), 0), 2) AS "每会话平均轮数",
    ROUND(COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 5)::numeric * 100 / NULLIF(COUNT(DISTINCT chat_id), 0), 1) AS ">=5轮占比%",
    ROUND(COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 10)::numeric * 100 / NULLIF(COUNT(DISTINCT chat_id), 0), 1) AS ">=10轮占比%"
FROM chat_rounds
GROUP BY model
ORDER BY model;


-- ============================================================
-- Query 1c: 按创建渠道维度汇总对比（忽略模型）
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae',
                '24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912',
                '44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e',
                'ede49321-0183-4117-8a66-3b3364b1a1a3',
                '23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a',
                '6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '人工创建'
            ELSE '自动创建'
        END AS source_type
    FROM chats c
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
chat_rounds AS (
    SELECT
        eg.chat_id,
        eg.user_id,
        eg.source_type,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' = 'human'
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS user_rounds
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    GROUP BY eg.chat_id, eg.user_id, eg.source_type
)
SELECT
    source_type AS "创建渠道",
    COUNT(DISTINCT user_id) AS "聊天用户数",
    SUM(user_rounds) AS "总用户轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS "人均轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT chat_id), 0), 2) AS "每会话平均轮数",
    ROUND(COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 5)::numeric * 100 / NULLIF(COUNT(DISTINCT chat_id), 0), 1) AS ">=5轮占比%",
    ROUND(COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 10)::numeric * 100 / NULLIF(COUNT(DISTINCT chat_id), 0), 1) AS ">=10轮占比%"
FROM chat_rounds
GROUP BY source_type
ORDER BY source_type;


-- ============================================================
-- Query 2: 每个角色的详细数据
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        a.name AS agent_name,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e'
            ) THEN '组1: minimax+人工'
            WHEN c.agent_id IN (
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba','d8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc','1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN '组2: minimax+自动'
            WHEN c.agent_id IN (
                'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '组3: gemini+人工'
            ELSE '组4: gemini+自动'
        END AS group_label
    FROM chats c
    JOIN agents a ON c.agent_id = a.id
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
chat_rounds AS (
    SELECT
        eg.chat_id,
        eg.user_id,
        eg.agent_id,
        eg.agent_name,
        eg.group_label,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' = 'human'
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS user_rounds
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    GROUP BY eg.chat_id, eg.user_id, eg.agent_id, eg.agent_name, eg.group_label
)
SELECT
    group_label AS "实验组",
    agent_name AS "角色名",
    agent_id AS "角色ID",
    COUNT(DISTINCT user_id) AS "聊天用户数",
    COUNT(DISTINCT chat_id) AS "会话数",
    SUM(user_rounds) AS "总用户轮数",
    ROUND(SUM(user_rounds)::numeric / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS "人均轮数",
    COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 5) AS ">=5轮会话",
    COUNT(DISTINCT chat_id) FILTER (WHERE user_rounds >= 10) AS ">=10轮会话"
FROM chat_rounds
GROUP BY group_label, agent_name, agent_id
ORDER BY group_label, agent_name;


-- ============================================================
-- Query 3: 按日聊天轮数趋势（各组每天的聊天轮数）
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e'
            ) THEN '组1: minimax+人工'
            WHEN c.agent_id IN (
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba','d8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc','1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN '组2: minimax+自动'
            WHEN c.agent_id IN (
                'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '组3: gemini+人工'
            ELSE '组4: gemini+自动'
        END AS group_label
    FROM chats c
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
)
SELECT
    DATE(ch.created_at AT TIME ZONE 'UTC') AS "日期",
    eg.group_label AS "实验组",
    COUNT(*) FILTER (
        WHERE ch.message->>'type' = 'human'
        AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
        AND ch.deleted_at IS NULL
    ) AS "用户消息数",
    COUNT(DISTINCT eg.user_id) AS "活跃用户数",
    COUNT(DISTINCT eg.chat_id) AS "活跃会话数"
FROM experiment_groups eg
JOIN chat_history ch
    ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
    AND ch.created_at >= '2026-02-07'::timestamptz
    AND ch.created_at < '2026-02-27'::timestamptz
GROUP BY DATE(ch.created_at AT TIME ZONE 'UTC'), eg.group_label
ORDER BY "日期", eg.group_label;


-- ============================================================
-- Query 4: 用户参与深度分布
-- 统计每组中用户的聊天轮数分布（1-2轮、3-5轮、6-10轮、11-20轮、20+轮）
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e'
            ) THEN '组1: minimax+人工'
            WHEN c.agent_id IN (
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba','d8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc','1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN '组2: minimax+自动'
            WHEN c.agent_id IN (
                'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
                '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
                'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e'
            ) THEN '组3: gemini+人工'
            ELSE '组4: gemini+自动'
        END AS group_label
    FROM chats c
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
chat_rounds AS (
    SELECT
        eg.chat_id,
        eg.user_id,
        eg.group_label,
        COUNT(*) FILTER (
            WHERE ch.message->>'type' = 'human'
            AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
            AND ch.deleted_at IS NULL
        ) AS user_rounds
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    GROUP BY eg.chat_id, eg.user_id, eg.group_label
),
bucketed AS (
    SELECT
        group_label,
        CASE
            WHEN user_rounds BETWEEN 1 AND 2 THEN 'A: 1-2轮'
            WHEN user_rounds BETWEEN 3 AND 5 THEN 'B: 3-5轮'
            WHEN user_rounds BETWEEN 6 AND 10 THEN 'C: 6-10轮'
            WHEN user_rounds BETWEEN 11 AND 20 THEN 'D: 11-20轮'
            WHEN user_rounds > 20 THEN 'E: 20+轮'
            ELSE 'F: 0轮'
        END AS depth_bucket,
        chat_id
    FROM chat_rounds
)
SELECT
    group_label AS "实验组",
    depth_bucket AS "聊天深度",
    COUNT(*) AS "会话数",
    ROUND(COUNT(*)::numeric * 100 / SUM(COUNT(*)) OVER (PARTITION BY group_label), 1) AS "占比%"
FROM bucketed
GROUP BY group_label, depth_bucket
ORDER BY group_label, depth_bucket;


-- ============================================================
-- Query 5: 用户次日留存对比
-- 统计首次聊天后，第二天是否还有消息的用户比例
-- ============================================================
WITH experiment_groups AS (
    SELECT
        c.id AS chat_id,
        c.user_id,
        c.agent_id,
        CASE
            WHEN c.agent_id IN (
                '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
                '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
                'c2734505-a8b2-4316-8931-6ebbe11c336e',
                '3b7a1a60-0a2b-461a-a8e6-0658d57a72ba','d8fba8d5-5836-4398-aa6b-cdb0b0268f683',
                '80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc','1a431b04-c454-48dc-a17d-a62bf00bb3fc',
                '1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa'
            ) THEN 'minimax-m2-her'
            ELSE 'gemini-2.5-flash-lite'
        END AS model
    FROM chats c
    WHERE c.agent_id IN (
        '4520d4b8-e500-4559-9fde-6ce4fa1c3ae','24735102-e08b-489c-b8c0-19ab837ee1f6',
        '2da8c51d-0917-4225-84b3-a42a7988fb912','44eebe1d-fcb8-4311-8e98-11b8a69737d1',
        'c2734505-a8b2-4316-8931-6ebbe11c336e','3b7a1a60-0a2b-461a-a8e6-0658d57a72ba',
        'd8fba8d5-5836-4398-aa6b-cdb0b0268f683','80a05aa6-6f1d-4b7e-9a50-e75a03bd45bc',
        '1a431b04-c454-48dc-a17d-a62bf00bb3fc','1e7c06f1-7b58-4499-ac2d-f3ca3554a8fa',
        'ede49321-0183-4117-8a66-3b3364b1a1a3','23649e0f-1e86-4e1c-b8bc-d83d19d93372',
        '1ece85c4-c4f6-4b60-9a8c-a9e42e73f8a','6e628aa7-366b-405b-914b-fd1a99a6b408',
        'dbb4c4b7-4320-4f14-ba98-7f71c8a6ce6e','22d6c676-ff0a-4828-ae08-02fbd4d8d0bb',
        '0fb3ee22-13f5-4072-ab6c-cc79304a0310','b1a89922-44c5-4b4f-beb1-9712b97900e57',
        '7eeed630-6358-4956-90dc-b127a1c6c77c','0191e798-0352-4b72-9d43-bbd0511754ee'
    )
    AND c.is_active = true
),
user_daily_activity AS (
    SELECT DISTINCT
        eg.user_id,
        eg.model,
        DATE(ch.created_at AT TIME ZONE 'UTC') AS active_date
    FROM experiment_groups eg
    JOIN chat_history ch
        ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, eg.chat_id)
        AND ch.created_at >= '2026-02-07'::timestamptz
        AND ch.created_at < '2026-02-27'::timestamptz
    WHERE ch.message->>'type' = 'human'
        AND (ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR ch.meta_data->>'isOpening' != 'true')
        AND ch.deleted_at IS NULL
),
user_first_day AS (
    SELECT
        user_id,
        model,
        MIN(active_date) AS first_active_date
    FROM user_daily_activity
    GROUP BY user_id, model
),
retention AS (
    SELECT
        ufd.model,
        COUNT(DISTINCT ufd.user_id) AS "首日用户数",
        COUNT(DISTINCT CASE
            WHEN uda.active_date = ufd.first_active_date + INTERVAL '1 day'
            THEN ufd.user_id
        END) AS "次日留存用户数",
        COUNT(DISTINCT CASE
            WHEN uda.active_date > ufd.first_active_date
            THEN ufd.user_id
        END) AS "回访用户数"
    FROM user_first_day ufd
    LEFT JOIN user_daily_activity uda
        ON ufd.user_id = uda.user_id AND ufd.model = uda.model
    GROUP BY ufd.model
)
SELECT
    model AS "模型",
    "首日用户数",
    "次日留存用户数",
    ROUND("次日留存用户数"::numeric * 100 / NULLIF("首日用户数", 0), 1) AS "次日留存率%",
    "回访用户数",
    ROUND("回访用户数"::numeric * 100 / NULLIF("首日用户数", 0), 1) AS "回访率%"
FROM retention
ORDER BY model;
