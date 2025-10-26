# 开发运营

## Google Play 发布

- AdsPower 指纹浏览器 cliproxy VPN it@sxwl.ai 提供 Facebook 环境
- 商业化测试
  - <https://intellimate.app/> 可以访问
  - <https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f>
  - 查看[使用条款](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/terms-of-service)
  - 检查 [Pr隐私政策](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/privacy-policy)
- Git标签、打标规则
  - 应用程序后端标签相同
  - 发布标签格式 v<major>.<minor>.<fix>
  - dev 分支格式 <release-tag>-dev (v<major>.<minor>.<fix>-dev)
    - dev分支标签须为<fix>增1，如v1.0.2-dev发布标签为v1.0.3-`git tag -d $GIT_TAG && git push origin --delete $GIT_TAG`
  - `git tag $GIT_TAG && git push --tags`- 生产环境部署前要跑一次压力测试，了解其性能指标是否有明显问题
- 应用程序构建发布
  - app构建金字塔物为aab，发布于Google Play，版本号为git commit ID，注入为app内版本号，发布于内测轨道后，内测人员下载安装，确认版本号
    - [内测轨道](https://play.google.com/store/apps/details?id=com.ai.intellimate)
  - 上传 aab 到 Google Play，填写 Release Notes
- 后端构建发布
  - 后端构建构建物为 docker 镜像，发布于 Google Cloud VM，版本号为 git commit ID，注入为 docker 镜像 tag，发布后，内测人员确认版本号`docker inspect --format '{{.Config.Image}}' inty-backend-prod`确认生产环境服务器docker镜像版本
- 确认测试Google账户可用
  - test.heartmate@gmail。com 填入 [Google Play 测试说明](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-content/testing-credentials)
- 应用程序测试
  - 人工测试【全员集中测试到目前为止没有其他问题】
  - Expresso 测试【待定】
  - Firebase测试实验室【待定】

### 最终检查前发布

-`docker inspect --format '{{.Config.Image}}' inty-backend-prod`确认生产环境服务器docker镜像版本
- 我的->设置->关于确认App版本
- 打开 [Firebase Crashlystics](https://console.firebase.google.com/project/alien-paratext-461204-i9/releasemonitoring/app/android:com.ai.intellimate)
  确认内测版本崩溃工程 0

### 发布

- 填写表单
- 将送审版本发布到 [Google Play production track](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/production?tab=releaseDashboard)

## 开发实例

这里记录了生成环境实例的设置

- 开发实例位于 GCP 上，为所有后端服务提供服务。
- 此实例应仅运行 docker 映像，不执行任何编码或用于其他目的。
- nginx 是相反的 proxy
- 在 dev 和 prod inty 后端前面，inty-eval

文件放置在主机上的以下路径中```text
htpasswd:/etc/nginx/.htpasswd # Used by nginx.conf
nginx.conf:/etc/nginx/conf.d/sxwl.ai.conf
```## Inty prod 部署

- GCP 区域：asia-southeast1-a
  - CloudSQL Postgres：[inty-prod](https://console.cloud.google.com/sql/instances/inty-prod)：sxwl666A！
  - GCE VM：[开发实例](https://console.cloud.google.com/compute/instancesDetail/zones/asia-southeast1-a/instances/dev-instance)
- GitHub部署环境：prod
- prod 容器上的云日志记录：[流日志](https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9)
  - 基于 [docker gcplogs 驱动](https://github.com/GoogleCloudPlatform/community/blob/master/archived/docker-gcplogs-driver/index.md)
  - [Docker运行命令行参数](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L73)
  - [日志标签设置](https://github.com/NascentCore/inty-backend/blob/9fa17750b82d5eeaf5519d486cd20e04dff4370c/.github/workflows/build_and_deploy.yml#L80)，日志标签示例：<img width="600" alt="image" src="https://github.com/user-attachments/assets/f0414fe4-053e-4ce2-b8d4-4fb39049a929"/>
- [GCP inty-prod 端点检查](https://console.cloud.google.com/monitoring/synthetic-monitoring?project=alien-paratext-461204-i9)
- API 端点：<https://app.inty.cc>
  - 监控：<https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f>

## Inty-dev

共享用于支持开发和足球的场地

- 端点：<https://dev.inty.sxwl.ai>- [日志](https://cloudlogging.app.goo.gl/X1mKZ555YZnRUYFD6)

## 其他服务

- GCP 谷歌云平台，提供文生图等全民服务：<it@sxwl.ai>
  - CloudSQL Postgres：
    - 亚洲-东南1-1：inty-prod：sxwl666A！
      - 与主轴服务器同一区域
  - 记录：
  - 所有服务都在 1 个 gcp 虚拟机上运行 (<it@sxwl.艾>)
    - [GCP 虚拟机网址](https://console.cloud.google.com/welcome?inv=1&invt=Ab4RWg&project=bustling-pen-sv00q)
    - <img width="3022" height="420" alt="image" src="https://github.com/user-attachments/assets/931abe03-e7c9-4475-bbb0-abb2d2247152" />
    - 定期在该服务器上运行`docker system prune -a --volumes`来明确使用的容器和镜像和挂载卷。
  - 所有服务都在nginx后面； nginx 配置：`/etc/nginx/conf.d/sxwl.ai.conf`在上述虚拟机上
  - nginx pr为内部服务提供密码pr保护
  - [Arch 图飞书源码](https://tricorder.feishu.cn/wiki/RjfPw00OKiWKNvk8Ldmc4d2snNc#share-KZGQdQrWSo1eb2xAq6mcLHjfn5c)
    <img width="800" height="468" alt="image" src="https://github.com/user-attachments/assets/acce2ea3-b571-4bd6-8f66-b1eea9796742" />
- langsmith 监控平台：<try@sxwl.ai>
- OpenRouter 大模型聚合调用平台：<it@sxwl.ai>
  - 下面2个API钥匙应该删除（不知道哪里有用）
  - <img width="800" height="268" alt="image" src="https://github.com/user-attachments/assets/322ef239-ef54-4679-b7e0-441b0025a93c" />
- ElevenLabs 语音AI平台：<it@sxwl.ai>
  - <img width="800" height="610" alt="image" src="https://github.com/user-attachments/assets/450ebfae-bb29-47fe-9f59-e89d7a49386a" />

部署环境：dev prod GitHub部署环境

- [教室部署](https://github.com/NascentCore/inty-backend/actions/workflows/build_and_deploy.yml)
- [前端APK发布](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)
- [前端AAB发布](https://github.com/NascentCore/inty-app/blob/main/.github/workflows/playdebug_release.yaml)postgres 与 pgvector（docker 容器）迁移到 gcp cloudsql
pg_dump > inty_prd。sql
然后导入到db
<img width="300" height="1662" alt="image" src="https://github.com/user-attachments/assets/9c4e52a2-9128-4b50-a620-443c0c2547be" />
<img width="300" height="1186" alt="image" src="https://github.com/user-attachments/assets/fdff5c54-aec4-44a2-91bc-8c9bbbda222b" />