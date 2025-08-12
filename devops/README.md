# DevOps

## Inty prod 部署

* GCP zone: asia-southeast1-a
  * CloudSQL Postgres: [inty-prod](https://console.cloud.google.com/sql/instances/inty-prod):sxwl666A!
  * GCE VM: [dev-instance](https://console.cloud.google.com/compute/instancesDetail/zones/asia-southeast1-a/instances/dev-instance)
* GitHub deployment environment: prod
* Cloud logging on prod container: [streaming logs](https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9)
  * 基于 [docker gcplogs 驱动](https://github.com/GoogleCloudPlatform/community/blob/master/archived/docker-gcplogs-driver/index.md)
  * [Docker run 命令行参数](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L73)
  * [日志标签设置](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L80)，日志标签示例：<img width="600" height="1062" alt="image" src="https://github.com/user-attachments/assets/f0414fe4-053e-4ce2-b8d4-4fb39049a929" />
* Website: https://intellimate.app
  * Status page: https://stats.uptimerobot.com/XqJhsnW1cN
* API endpoint: https://app.inty.cc
  * Monitoring: https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f

## Inty-dev

共享的用于支持开发和评测的后端

* Endpoint: <https://dev.inty.sxwl.ai>
* [logs](https://cloudlogging.app.goo.gl/X1mKZ555YZnRUYFD6)

## Other services

* GCP 谷歌云平台，提供文生图等各类后端服务：it@sxwl.ai
  * CloudSQL Postgres:
    * asia-southeast1-1:inty-prod:sxwl666A!
      * 与后端服务器同一 zone
  * logging: 
  * All services are running on 1 gcp vm (it@sxwl.ai)
    * [GCP VM url](https://console.cloud.google.com/welcome?inv=1&invt=Ab4RWg&project=bustling-pen-sv00q)
    * <img width="3022" height="420" alt="image" src="https://github.com/user-attachments/assets/931abe03-e7c9-4475-bbb0-abb2d2247152" />
    * 定期在该服务器上运行 `docker system prune -a --volumes` 来清楚不用的容器和镜像和挂载卷。
  * All services are behind nginx; nginx config: `/etc/nginx/conf.d/sxwl.ai.conf` on the above VM
  * nginx provide password protection for internal services
  * [Arch diagram feishu source](https://tricorder.feishu.cn/wiki/RjfPw00OKiWKNvk8Ldmc4d2snNc#share-KZGQdQrWSo1eb2xAq6mcLHjfn5c)
    <img width="800" height="468" alt="image" src="https://github.com/user-attachments/assets/acce2ea3-b571-4bd6-8f66-b1eea9796742" />
* langsmith 监控平台：try@sxwl.ai
* OpenRouter 大模型聚合调用平台：it@sxwl.ai
  * 下面 2 个 API key 应该删除（不知道哪里用到）
  * <img width="800" height="268" alt="image" src="https://github.com/user-attachments/assets/322ef239-ef54-4679-b7e0-441b0025a93c" />
* ElevenLabs 语音 AI 平台：it@sxwl.ai
  * <img width="800" height="610" alt="image" src="https://github.com/user-attachments/assets/450ebfae-bb29-47fe-9f59-e89d7a49386a" />

部署环境：dev prod GitHub deployment environments

* [后端部署](https://github.com/NascentCore/inty-backend/actions/workflows/build_and_deploy.yml)
* [前端 APK 发布](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)
* [前端 AAB 发布](https://github.com/NascentCore/inty-app/blob/main/.github/workflows/playdebug_release.yaml)

postgres with pgvector (docker container) migration to gcp cloudsql
pg_dump > inty_prd.sql
然后倒入到 db
<img width="300" height="1662" alt="image" src="https://github.com/user-attachments/assets/9c4e52a2-9128-4b50-a620-443c0c2547be" />
<img width="300" height="1186" alt="image" src="https://github.com/user-attachments/assets/fdff5c54-aec4-44a2-91bc-8c9bbbda222b" />

