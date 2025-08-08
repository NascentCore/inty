# 管理预置角色

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
