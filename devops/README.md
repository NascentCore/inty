# DevOps - 运维部署

## Google Play 发布

- AdsPower 指纹浏览器 cliproxy VPN it@sxwl.ai 提供给 Facebook 环境
- 商业化测试
  - <https://intellimate.app/> 可以访问
  - <https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f>
  - 检查 [Terms of Use](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/terms-of-service)
  - 检查 [Privacy Policy](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/privacy-policy)
- Git tagging, 打标规则
  - app backend tag 同一
  - release tag 格式 v<major>.<minor>.<fix>
  - dev branch 格式 <release-tag>-dev (v<major>.<minor>.<fix>-dev)
    - dev branch tag 须为 <fix> 增 1，如 v1.0.2-dev release tag 为 v1.0.3
  - `git tag -d $GIT_TAG && git push origin --delete $GIT_TAG`
  - `git tag $GIT_TAG && git push --tags`
- 生产环境部署之前要跑一次压力测试，了解其性能指标是否有明显问题
- app 构建发布
  - app 构建产出物为 aab，发布于 Google Play，版本号为 git commit ID，注入为 app 内版本号，发布于内测轨道后，内测人员下载安装，确认版本号
    - [内测轨道](https://play.google.com/store/apps/details?id=com.ai.intellimate)
  - 上传 aab 到 Google Play，填写 Release Notes
- backend 构建发布
  - backend 构建产出物为 docker image，发布于 Google Cloud VM，版本号为 git commit ID，注入为 docker image tag，发布后，内测人员确认版本号
    `docker inspect --format '{{.Config.Image}}' inty-backend-prod` 确认生产环境服务器 docker 镜像版本
- 确认测试 Google 账户可用
  - test.heartmate@gmail.com 填入 [Google Play Testing Instructions](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-content/testing-credentials)
- app 测试
  - 人工测试【全员集中测试直到没有其他问题】
  - Expresso 测试【TBA】
  - Firebase test lab【TBA】

### 发布前最终检查

- `docker inspect --format '{{.Config.Image}}' inty-backend-prod` 确认生产环境服务器 docker 镜像版本
- My->Settings->About 确认 App 版本
- 打开 [Firebase Crashlystics](https://console.firebase.google.com/project/alien-paratext-461204-i9/releasemonitoring/app/android:com.ai.intellimate)
  确认内测版本崩溃率为 0

### 发布

- 填写各项表单
- 将送审版本发布到 [Google Play production track](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/production?tab=releaseDashboard)

## Dev Instance

这里记录了生成环境实例的设置

- Dev instance is on GCP, serves all backend services.
- This instance should only run docker images, do not perform any coding or used for other purposes.
- nginx is the reverse proxy
- in front of dev & prod inty backend, 和 intellimate.app web app

详情请查看 [NGINX](NGINX.md)

## Inty prod & dev 部署

- 公用同一数据库服务器 inty-prod，dev:inty-dev prod:inty
  - [看板](https://console.cloud.google.com/sql/instances/inty-prod/system-insights?project=alien-paratext-461204-i9)
  - [查询性能分析](https://console.cloud.google.com/sql/instances/inty-prod/insights;duration=P1D;sort_by=TOTAL_EXEC_TIME/executed?project=alien-paratext-461204-i9)
- GCP zone: asia-southeast1-a
  - CloudSQL Postgres: [inty-prod](https://console.cloud.google.com/sql/instances/inty-prod):sxwl666A!
  - GCE VM: [dev-instance](https://console.cloud.google.com/compute/instancesDetail/zones/asia-southeast1-a/instances/dev-instance)
- GitHub deployment environment: prod
- Cloud logging on prod container: [streaming logs](https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9)
  - 基于 [docker gcplogs 驱动](https://github.com/GoogleCloudPlatform/community/blob/master/archived/docker-gcplogs-driver/index.md)
  - [Docker run 命令行参数](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L73)
  - [日志标签设置](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L80)，日志标签示例：<img width="600" alt="image" src="https://github.com/user-attachments/assets/f0414fe4-053e-4ce2-b8d4-4fb39049a929"/>
- [GCP inty-prod endpoint check](https://console.cloud.google.com/monitoring/synthetic-monitoring?project=alien-paratext-461204-i9)
- API endpoint: <https://app.inty.cc>
  - Monitoring: <https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f>
- CloudFlare: `it@sxwl.ai`
  - 图片裁切、图片缩放、图片压缩（不改变文件格式 80% 质量缩小到 1/4）

### Inty-dev

共享的用于支持开发和评测的后端

- URL：<https://dev.inty.sxwl.ai>
- [logs](https://cloudlogging.app.goo.gl/X1mKZ555YZnRUYFD6)
- 运营评测工具：<https://dev.inty.sxwl.ai/evaluation>

## Other services

- GCP 谷歌云平台，提供文生图等各类后端服务：<it@sxwl.ai>
  - CloudSQL Postgres:
    - asia-southeast1-1:inty-prod:sxwl666A!
      - 与后端服务器同一 zone
  - logging:
  - All services are running on 1 gcp vm (<it@sxwl.ai>)
    - [GCP VM url](https://console.cloud.google.com/welcome?inv=1&invt=Ab4RWg&project=bustling-pen-sv00q)
    - <img width="3022" height="420" alt="image" src="https://github.com/user-attachments/assets/931abe03-e7c9-4475-bbb0-abb2d2247152" />
    - 定期在该服务器上运行 `docker system prune -a --volumes` 来清楚不用的容器和镜像和挂载卷。
  - All services are behind nginx; nginx config: `/etc/nginx/conf.d/sxwl.ai.conf` on the above VM
  - nginx provide password protection for internal services
  - [Arch diagram feishu source](https://tricorder.feishu.cn/wiki/RjfPw00OKiWKNvk8Ldmc4d2snNc#share-KZGQdQrWSo1eb2xAq6mcLHjfn5c)
    <img width="800" height="468" alt="image" src="https://github.com/user-attachments/assets/acce2ea3-b571-4bd6-8f66-b1eea9796742" />
- langsmith 监控平台：<try@sxwl.ai>
- OpenRouter 大模型聚合调用平台：<it@sxwl.ai>
  - 下面 2 个 API key 应该删除（不知道哪里用到）
  - <img width="800" height="268" alt="image" src="https://github.com/user-attachments/assets/322ef239-ef54-4679-b7e0-441b0025a93c" />
- ElevenLabs 语音 AI 平台：<it@sxwl.ai>
  - <img width="800" height="610" alt="image" src="https://github.com/user-attachments/assets/450ebfae-bb29-47fe-9f59-e89d7a49386a" />

部署环境：dev prod GitHub deployment environments

- [后端部署](https://github.com/NascentCore/inty-backend/actions/workflows/build_and_deploy_backend.yml)
- [推送服务部署](https://github.com/NascentCore/inty-backend/actions/workflows/build_and_deploy_push_worker.yml)
- [前端 APK 发布](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)
- [前端 AAB 发布](https://github.com/NascentCore/inty-app/blob/main/.github/workflows/playdebug_release.yaml)

## 推送服务部署

推送服务（Push Worker）独立于后端服务运行，负责处理推送通知任务。

### 部署配置

- **镜像名称**：`ghcr.io/nascentcore/inty-backend/inty-push-worker`
- **容器名称**：`inty-push-worker-{environment}`（如 `inty-push-worker-dev`、`inty-push-worker-prod`）
- **Dockerfile**：`Dockerfile.push-worker`
- **启动脚本**：`start_push_worker.sh`
- **配置文件**：使用与后端服务相同的配置文件路径 `devops/config.yaml.{environment}`
- **挂载卷**：与后端服务相同的密钥文件
  - `/opt/inty-{environment}/inty-backend-key.json`
  - `/opt/inty-{environment}/inty-firebase-key.json`
- **日志**：使用 GCP Cloud Logging 驱动，标签为 `application=inty-push-worker`、`environment={environment}`

### 部署流程

1. 代码推送到 `main` 分支且涉及推送服务相关文件时，自动触发构建和部署
2. 构建 Docker 镜像并推送到 GitHub Container Registry
3. 通过 SSH 连接到 GCP VM，拉取镜像并重启容器
4. 检查容器运行状态和初始化日志

### 验证部署

检查容器状态：

```bash
sudo docker ps | grep inty-push-worker
```

查看容器日志：

```bash
sudo docker logs inty-push-worker-{environment}
```

检查镜像版本：

```bash
sudo docker inspect --format '{{.Config.Image}}' inty-push-worker-{environment}
```

### 相关文件

- Dockerfile: `Dockerfile.push-worker`
- 启动脚本: `start_push_worker.sh`
- Workflow: `.github/workflows/build_and_deploy_push_worker.yml`
- 服务代码: `app/services/push_worker.py`

postgres with pgvector (docker container) migration to gcp cloudsql
pg_dump > inty_prd.sql
然后倒入到 db
<img width="300" height="1662" alt="image" src="https://github.com/user-attachments/assets/9c4e52a2-9128-4b50-a620-443c0c2547be" />
<img width="300" height="1186" alt="image" src="https://github.com/user-attachments/assets/fdff5c54-aec4-44a2-91bc-8c9bbbda222b" />
