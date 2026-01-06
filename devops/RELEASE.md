# 发布流程

* 例行的 Android app 测试版本发布到内测轨道，不再使用 internal app sharing

## 流程概览

1. 从 tag 启动相应 GitHub Actions 工作流创建新的发布产物（后端服务的 docker 容器镜像、web app 在服务器上的静态文件等等）
2. 版本号命名规则：`v1.<minor>.<fix>-<组件>`
   - 使用后缀区分发布的组件：-backend、-android、-web
   - 数字版本号所有组件共享，也就是如果后端发布了 v1.3.1-backend，下一个 android 发布名称为 v1.3.2-android

## Backend 发布流程

1. `-backend` 后缀添加到版本号上，版本号依次递增，每次 backend android 发布都要增加 fix 或者 minor 版本号；
2. [Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
   选择对应的 tag，环境选择 prod
   <img width="800" height="1210" alt="image" src="https://github.com/user-attachments/assets/3e0fe7de-abf5-4eb8-b81d-ae9f31fa6399" />

## Android app 发布流程

1. 修改代码中的 versionName 到新的版本号，否则会触发版本检查错误，如 https://github.com/NascentCore/inty/commit/0c18b413401dedc48efe9c1bcc67e2ba999065be
   <img width="900" height="400" alt="image" src="https://github.com/user-attachments/assets/186335c0-fc96-4520-b8da-d89f0f892a23" />
2. 在本地 git checkout 出对应的 tag，构建 release aab（使用 release build type）并确认其 versionName
   <img width="480" height="208" alt="image" src="https://github.com/user-attachments/assets/433d8afe-911f-4494-8e0f-39a666653afc" />
3. 上传内测轨道
   <img width="800" height="1614" alt="image" src="https://github.com/user-attachments/assets/07cc93c6-a573-40d8-98f2-f716fce5826a" />
   编写有价值的更新说明
4. 从 Google Play 商店下载内测版本测试
5. 创建生产环境发布版本，选择前面测试的内测版本
   <img width="800" height="1340" alt="image" src="https://github.com/user-attachments/assets/a3a327d1-70a7-4236-a4b0-02c15283ac49" />
6. 提交审核
7. 审核通过后，正式发布
8. 完成后使用非内测账户检查 Google Play 商店打开 https://play.google.com/store/apps/details?id=com.ai.intellimate 确认版本可见

## Web app 发布流程

1. 打开 [build_and_deploy_web_app](https://github.com/NascentCore/inty/blob/main/.github/workflows/build_and_deploy_web_app.yml)
2. 选择 tag 及 prod 环境
   <img width="800" height="756" alt="image" src="https://github.com/user-attachments/assets/066e530b-3d1d-402e-a72f-97169178e606" />
