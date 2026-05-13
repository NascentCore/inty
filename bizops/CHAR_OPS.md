# 管理预置角色

## 添加角色类型（亲密行为风格）

- 御姐
- 萝莉可爱型
- 狂野型

## 角色同步定时工作流

[GitHub 同步角色定时工作流](../.github/workflows/sync_ai_chars.yaml)

https://github.com/NascentCore/inty/settings/actions/runners
<img width="3022" height="700" alt="image" src="https://github.com/user-attachments/assets/6a9eafa4-9b03-4e8f-8309-b8a4ac58d0fc" />

## Dev→Prod 同步脚本行为

- 手动脚本：`tools/scripts/sync_agents_dev_to_prod/sync_agents.py` 会比对指定运营账号在 dev、prod 中的未删除角色。
- `FIELDS_TO_SYNC` 覆盖 `intro`、`opening`、`prompt`、`character_card_*`、`photos`、`voice_id` 等角色核心字段。只要 dev 中的这些字段被修改（包括简介 `intro` 之类），脚本就会把差异复制到 prod。
- 同步顺序为“先更新已存在的角色，再创建缺失的角色”，并在执行前校验 dev / prod 的 Alembic 版本一致性。需要实际落地更新时去掉 `--dry-run` 参数。
- 因此想让 dev 的改动（例如简介文案）进入 prod，必须运行该脚本或等待相应的自动化工作流触发，它会自动检测出差异并写入 prod。

## 删除角色

```
inty=> DELETE FROM agents WHERE name = 'Sophie Walsh  Hot';
ERROR:  update or delete on table "agents" violates foreign key constraint "chat_settings_agent_id_fkey" on table "chat_settings"
DETAIL:  Key (id)=(28c46073-43b2-4bf5-b1aa-6d772d255d61) is still referenced from table "chat_settings".
inty=> select * from chat_settings where id = 28c46073-43b2-4bf5-b1aa-6d772d255d61
inty-> ;
ERROR:  trailing junk after numeric literal at or near "28c46073"
LINE 1: select * from chat_settings where id = 28c46073-43b2-4bf5-b1...
                                               ^
inty=> select * from chat_settings where id = '28c46073-43b2-4bf5-b1aa-6d772d255d61';
 id | user_id | agent_id | language | voice_enabled | keep_talking | created_at | updated_at | chat_id
----+---------+----------+----------+---------------+--------------+------------+------------+---------
(0 rows)

inty=> select * from chat_settings where agent_id = '28c46073-43b2-4bf5-b1aa-6d772d255d61';
inty=> delete from chat_settings where agent_id = '28c46073-43b2-4bf5-b1aa-6d772d255d61';
DELETE 2
inty=> DELETE FROM agents WHERE name = 'Sophie Walsh  Hot';
ERROR:  update or delete on table "agents" violates foreign key constraint "chats_agent_id_fkey" on table "chats"
DETAIL:  Key (id)=(28c46073-43b2-4bf5-b1aa-6d772d255d61) is still referenced from table "chats".
inty=> select * from chats where agent_id = '28c46073-43b2-4bf5-b1aa-6d772d255d61';
inty=> delete from chats where agent_id = '28c46073-43b2-4bf5-b1aa-6d772d255d61';
DELETE 14
inty=> DELETE FROM agents WHERE name = 'Sophie Walsh  Hot';
DELETE 1
inty=>
```

## 更新角色字段

```
update agents set opening = $$ ... $$ where id = '...';
```
