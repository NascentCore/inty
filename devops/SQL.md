# SQL 查询用于支持开发和运营

```sql:为新的Inty后端服务实例创建新数据库
CREATE DATABASE "inty-imate";
```

```sql:更新用户和某角色的聊天中国的 chat-style
UPDATE chat_settings
   SET style_prompt = 'write very detailed and elaborate descriptions of actions and thoughts'
   WHERE chat_id = (
     SELECT id FROM chats
     WHERE user_id = 'user-testing'
       AND agent_id = 'agent-b0b86fda'
       AND is_active = true
     LIMIT 1
   );
UPDATE 1
```

```sql:
-- Requires: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Find agents with the most chage mssages
-- Include each and every avatar's avatar and photos fields

SELECT
  agg.agent_id,
  a.name AS agent_name,
  a.avatar,
  a.photos,
  a.exclusive_photos,
  a.background,
  a.background_images,
  a.background_animated,
  agg.message_count
FROM (
  SELECT
    c.agent_id,
    COUNT(ch.id) AS message_count
  FROM chats c
  JOIN chat_history ch
    -- 6ba7b810-9dad-11d1-80b4-00c04fd430c8 is the UUID namespace for DNS from RFC 4122 (UUIDs).
    ON ch.session_id = uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, c.id)
    AND ch.deleted_at IS NULL
  GROUP BY c.agent_id
) agg
JOIN agents a ON a.id = agg.agent_id
ORDER BY agg.message_count DESC;
```
