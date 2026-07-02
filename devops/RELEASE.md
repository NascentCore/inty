# 发布流程

- 例行的 Android app 测试版本发布到内测轨道，不再使用 internal app sharing

## 版本号与打标（Tagging）

- **release tag 格式**：`v<major>.<minor>.<fix>-<组件>`
  - 组件后缀用于区分发布产物：`-backend`、`-android`、`-web`
  - 数字版本号所有组件共享：例如如果后端发布了 `v1.3.1-backend`，下一个 Android 发布名称通常为 `v1.3.2-android`
- **dev branch 格式**：`<release-tag>-dev`（例如 `v1.0.3-dev`）
  - dev branch tag 一般做 `<fix>` + 1，例如 `v1.0.2-dev` 对应下一个 release tag 为 `v1.0.3-xxx`
- **常用命令**：

```bash
git tag -d $GIT_TAG && git push origin --delete $GIT_TAG
git tag $GIT_TAG && git push --tags
```

## 发布前准备（通用）

- 确保审查员账户可以登录
- 商业化测试
  - `https://intellimate.app/` 可以访问
  - `https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f`
  - 检查 [Terms of Use](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/terms-of-service)
  - 检查 [Privacy Policy](https://app.termly.io/dashboard/website/0619077d-bb29-4da6-af36-9a465bf36f08/privacy-policy)
- 生产环境部署之前跑一次压力测试，了解其性能指标是否有明显问题
- 确认测试 Google 账户可用
  - `test.heartmate@gmail.com` 填入 Google Play Console 的 Testing Instructions

## 流程概览

1. 从 tag 启动相应 GitHub Actions 工作流创建新的发布产物（后端服务的 docker 容器镜像、web app 在服务器上的静态文件等等）
2. 版本号命名规则：见「版本号与打标（Tagging）」

## Backend 发布流程

1. `-backend` 后缀添加到版本号上，版本号依次递增，每次 backend android 发布都要增加 fix 或者 minor 版本号；
2. 修改配置文件 `devops/config.yaml.{prod,dev}` 中 `google_play.current_version_code`，与 Google Play 最新包 version code 保持一致
3. [Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
   选择对应的 tag，环境选择 prod
   <img width="800" height="1210" alt="image" src="https://github.com/user-attachments/assets/3e0fe7de-abf5-4eb8-b81d-ae9f31fa6399" />
4. 部署完成后（可选）在目标机器确认容器镜像版本：
   - `docker inspect --format '{{.Config.Image}}' inty-backend-prod`

## 推送服务（Push Worker）发布/部署

推送服务通过**独立** GitHub Actions workflow 构建与部署（镜像与后端同源 monorepo，但 workflow 分离）。

- **Workflow**：`.github/workflows/build_and_deploy_push_worker.yml`
- **镜像名称**：`ghcr.io/nascentcore/inty-backend/inty-push-worker`
- **容器名称**：`inty-push-worker-{environment}`（如 `inty-push-worker-dev`、`inty-push-worker-prod`）
- **Dockerfile**：`devops/docker/Dockerfile.push-worker`
- **启动脚本**：`backend/push_worker/start.sh`
- **配置文件**：使用与后端服务一致的 `devops/config.yaml.{environment}`（构建期注入进镜像，见下文「配置文件如何进入 Docker 镜像」）
- **挂载卷**：
  - `/opt/inty-{environment}/inty-backend-key.json`
  - `/opt/inty-{environment}/inty-firebase-key.json`
- **日志**：Docker 默认 `json-file`（stdout 在 VM 本地；见 [DEPLOYMENT_STATE.md](DEPLOYMENT_STATE.md)）

验证部署：

```bash
sudo docker ps | grep inty-push-worker
sudo docker inspect --format '{{.Config.Image}}' inty-push-worker-{environment}
```

## Android app 发布流程

1. 【已自动化】[每日构建并上传 AAB 到内测轨道](https://github.com/NascentCore/inty/actions/workflows/build_and_upload_android.yaml)
   测试发布负责人不需要检查这个，如有问题联系 @亚雄
2. 【手动完成】打开 Google Play 更新内测轨道版本，确保能看到自己打开的 Internal Tester 版本

   <img width="200" height="696" alt="image" src="https://github.com/user-attachments/assets/bdde0572-bf2d-473b-9865-cbaca556af4c" />
   <img width="200" height="694" alt="image" src="https://github.com/user-attachments/assets/7a2cb850-dfc4-4d74-b238-59bcd95a1248" />
3. 【手动测试】使用下面的测试账户来测试 App 各项功能
   ```text
   test@sxwl.ai
   sxwltest
   ```
4. 【测试通过后】将该内测版本发布到 Production；确保内测轨道 app 版本号（me->settings）与 Google Play 上要发布的版本号一致；然后填写 release notes

   <img width="200" height="1220" alt="image" src="https://github.com/user-attachments/assets/8abdfb90-b4a2-4df8-9d57-459ef00580e4" />
   <img width="600" height="1152" alt="image" src="https://github.com/user-attachments/assets/ee4177a7-5a27-4d8a-9de7-5e7e14d7ee54" />
   <img width="600" height="1616" alt="image" src="https://github.com/user-attachments/assets/380669dc-4671-4551-bc20-201625f228be" />
   <img width="600" height="1288" alt="image" src="https://github.com/user-attachments/assets/89c1d846-ab5c-4d74-b1ee-8c935d7916d0" />

   1. 参考 [Change logs](/android_app/docs/CHANGE_LOGS.md) 找到距离上次发布依赖的改动，填写 release notes
5. 审核通过后，正式发布
6. 完成后使用非内测账户检查 Google Play 商店打开 https://play.google.com/store/apps/details?id=com.ai.intellimate 确认版本可见
7. 发布完成后，需要把后端用于版本检查的 `current_version_code` 更新到最新 app version code：
   - 修改 `devops/config.yaml.{prod,dev}` 中 `google_play.current_version_code`
   - （了解用法/默认值参考）`../app/core/config.py` 的 `GooglePlayConfig.current_version_code`

## 发布前最终检查（建议）

- `docker inspect --format '{{.Config.Image}}' inty-backend-prod` 确认生产环境服务器 docker 镜像版本
- My->Settings->About 确认 App 版本
- 打开 [Firebase Crashlystics](https://console.firebase.google.com/project/alien-paratext-461204-i9/releasemonitoring/app/android:com.ai.intellimate) 确认内测版本崩溃率为 0

## 发布（Google Play production）

- 填写各项表单
- 将送审版本发布到 [Google Play production track](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/production?tab=releaseDashboard)

## Web app 发布流程

1. 打开 [build_and_deploy_web_app](https://github.com/NascentCore/inty/blob/main/.github/workflows/build_and_deploy_web_app.yml)
2. 选择 tag 及 prod 环境
   <img width="800" height="756" alt="image" src="https://github.com/user-attachments/assets/066e530b-3d1d-402e-a72f-97169178e606" />

## 配置文件如何进入 Docker 镜像，以及运行时如何“选中”

后端服务与推送服务的配置读取逻辑**不依赖环境变量去“选择不同配置文件”**；它们都会在进程启动时（更准确地说：`app/core/config.py` 被 import 时）从当前工作目录读取固定路径的 `config.yaml`。

- **关键约束**：容器里必须存在 `config.yaml`，否则服务会直接启动失败。
- **当前生产/开发部署方式（推荐）**：在 **构建镜像阶段**把目标环境配置文件 bake 进镜像，统一落到镜像内的 `config.yaml`；运行时只需要 `docker run` 启动对应镜像即可。

### 构建期注入（当前采用）

配置源文件位于 `devops/`：

- **开发环境**：`devops/config.yaml.dev`
- **生产环境**：`devops/config.yaml.prod`
- **CI / pytest 单元测试**：`devops/config.yaml.test`（faked 外部服务，不调用真实 LLM/GCS）
- **REPL 回归 E2E**：`devops/config.yaml.regression_tests`（真实 LLM/GitHub；与 local 分离）
- **工程师本地开发**：`devops/config.yaml.local`（本地/线上部署不应混用 test yaml）

在 GitHub Actions 部署工作流中，通过 `CONFIG_FILE` build-arg 选择并注入配置：

- **Workflow**：`.github/workflows/build_and_deploy_backend.yml`
- **Backend Dockerfile**：`devops/docker/Dockerfile`
- **Push worker Dockerfile**：`devops/docker/Dockerfile.push-worker`

工作流会按环境（`dev`/`prod`）计算出：

- **build-arg**：`CONFIG_FILE=devops/config.yaml.${environment}`

Dockerfile 会把该文件复制到镜像根目录并命名为 `config.yaml`（Dockerfile 的 `WORKDIR /` 确保服务启动时能读到它）。

这意味着：

- **“选中哪个环境配置”发生在 build 阶段**（构建镜像时已经确定）
- **运行时不会再根据 env 做二次选择**（`docker run` 只负责启动对应镜像）

### 运行期挂载（可选，但需要自己保证一致性）

如果你希望同一份镜像在不同环境复用，也可以在运行时把宿主机上的配置挂载到容器内的 `config.yaml` 路径：

```bash
sudo docker run --detach \
  --name inty-backend-dev \
  --volume /opt/inty-dev/config.yaml:/config.yaml:ro \
  ghcr.io/nascentcore/inty-backend/inty-server:<tag>
```

注意：当前仓库的默认部署工作流采用的是“构建期注入”，因此 workflow 的 `docker run` 命令行**没有挂载 `config.yaml`**；如果你切换到运行期挂载方案，需要同步调整部署脚本/工作流以免启动失败。
