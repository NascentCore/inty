# services - 业务服务

## Cursor Summary

- 目录用途: 领域服务层，承载主要业务逻辑，编排外部依赖与数据读写。
- 关键文件:
  - 会话/聊天: `chat_service.py`、`chat_history_service.py`、`question_parser_service.py`、`scoring_service.py`、`evaluation_service.py`。
  - 用户/订阅: `user_service.py`、`subscription_service.py`、`system_settings_service.py`、`settings_service.py`。
  - 资源: `resource_service.py`、`image_transform_service.py`、`gcs_service.py`。
  - 智能体: `agent_service.py`、`character_card_service.py`、`character_card_mapper.py`。
  - 语音: `voice_service.py`、`voice_cache_service.py`。
  - 通知: `notification_service.py`。
  - 全局: `global_services.py`、`cache_service.py`。
- 关联: 与 `app/api/*` 路由对接、与 `app/models`/`app/db` 进行数据操作、与 `app/utils`/`external_services` 进行外部能力调用。
