# __保留__0__

## 生成版本

-`alembic upgrade head`：运行此命令以确保本地数据库与最新版本同步
- `alembic revision --autogenerate --message "<write your message for this version>"：这将为您编写新版本的脚本
-`alembic upgrade head`：再次运行此命令以应用您的新版本文件
- 如果上述失败，您需要与@yaxiong 调试失败的原因
- 如果您想重做最新版本，请先回滚本地更改`alembic downgrade -1`然后删除新版本
  您生成的文件`alembic revision --autogenerate --message "<...>"`，然后通过重新运行来重新创建版本文件`alembic revision --autogenerate --message "<...>"`。

## 标准操作程序

### 手动设置alembic_版本时

-`alembic_version`表只有一行，写入应用于数据库的最新版本。- 您可以将其值更新为最新版本号：`insert into alembic_version (version_num) values ('75796d073cb2');`- 之后的修订将在录制版本后应用