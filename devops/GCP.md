# GCP

## BigQuery CloudSQL-Postgres 链接

https://docs.cloud.google.com/bigquery/docs/working-with-connections#console_1
BigQuery Federated Queries (for on-demand querying)

DataStream 比较麻烦，因为需要从主数据库同步数据、要重启数据库；

- [ ] 是否能在只读副本上直接增加数据同步到 big query？ <img width="600" height="608" alt="image" src="https://github.com/user-attachments/assets/cdb6bce5-beb9-4d56-ad08-c3e53eae8c48" /> <img width="600" height="750" alt="image" src="https://github.com/user-attachments/assets/6e50aaa5-d5ef-449c-8bd0-b545cebcd667" />


## Dev/Prod 环境概览（Inty）

本节记录线上/开发环境的基础信息与常用入口（与发布流程相关的操作请见 `RELEASE.md`）。

- **GCP zone**：asia-southeast1-a
- **数据库**：共用同一 CloudSQL Postgres 实例，dev:inty-dev prod:inty
  - [看板](https://console.cloud.google.com/sql/instances/inty-prod/system-insights?project=alien-paratext-461204-i9)
  - [查询性能分析](https://console.cloud.google.com/sql/instances/inty-prod/insights;duration=P1D;sort_by=TOTAL_EXEC_TIME/executed?project=alien-paratext-461204-i9)
- **GCE VM**：[dev-instance](https://console.cloud.google.com/compute/instancesDetail/zones/asia-southeast1-a/instances/dev-instance)
- **反向代理**：nginx（详见 `nginx/README.md`）
- **API endpoint**：https://app.inty.cc
  - Monitoring：https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f
- **Inty-dev**：https://dev.inty.sxwl.ai
  - 运营评测工具：https://dev.inty.sxwl.ai/evaluation

### 日志

- Cloud logging：prod container streaming logs https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9
- 使用 docker `gcplogs` driver（概念与选项参考）：https://docs.docker.com/engine/logging/drivers/gcplogs/

### 其它外部依赖/平台账号（便于排查）

- CloudFlare：`it@sxwl.ai`（图片裁切/缩放/压缩等）
- LangSmith：`try@sxwl.ai`
- OpenRouter：`it@sxwl.ai`
- ElevenLabs：`it@sxwl.ai`

## DataStream + CloudSQL

- Network attachment
  - <img width="1904" height="752" alt="image" src="https://github.com/user-attachments/assets/a32f0f9b-665b-4271-b150-6d9725ce16bb" />
- Private network connectivity: VPC peering
- <img width="1320" height="1602" alt="image" src="https://github.com/user-attachments/assets/757063e7-a218-42cf-a084-60345a8e1c89" />
