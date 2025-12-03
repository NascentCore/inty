# 推送功能

https://applink.feishu.cn/client/message/link/open?token=AmTE5KCVRMAEaTBl6u9AzOA%3D
```
.venv) (base) ➜  inty-backend git:(main) ✗ python scripts/fcm/test_push_flow.py --help         
[CONFIG] Loading config from: /Users/donggang/Documents/code/inty-backend/config.yaml
[CONFIG] Database URL: postgresql://postgres:postgres@localhost:5432/devdb
2025-12-03 16:34:27.307 | DEBUG    | app.core.config:<module>:423 - Setting LangSmith environment variables for project: 
2025-12-03 16:34:27.307 | DEBUG    | app.core.config:<module>:424 - LANGSMITH_TRACING_V2: true
2025-12-03 16:34:27.307 | DEBUG    | app.core.config:<module>:425 - LANGSMITH_PROJECT: inty-backend-dev
2025-12-03 16:34:27.307 | DEBUG    | app.core.config:<module>:426 - LANGCHAIN_API_KEY: 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
2025-12-03 16:34:28.730 | DEBUG    | app.utils.admin:<module>:27 - SUPER_USER_EMAILS: ['test.heartmate@gmail.com', 'it@sxwl.ai']
usage: test_push_flow.py [-h] [--chat-id CHAT_ID] [--user-id USER_ID] [--stage {10min,30min,2h,24h,48h}]
                         [--dry-run] [--real]
推送流程测试工具
options:
  -h, --help            show this help message and exit
  --chat-id CHAT_ID     聊天ID（与 --user-id 二选一）
  --user-id USER_ID     用户ID（与 --chat-id 二选一，会测试该用户的所有活跃聊天）
  --stage {10min,30min,2h,24h,48h}
                        推送阶段（默认: 10min）
  --dry-run             Dry run 模式（默认启用，不会实际发送）
  --real                真实发送模式（会实际发送消息）
```
