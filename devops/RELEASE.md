# 发布流程

* 例行的 Android app 测试版本发布到内测轨道，不再使用 internal app sharing

## 流程概览

1. 创建 GitHub release（这个过程会打 tag，编写 release notes）名称为 `v1.<minor>.<fix>-<组件>`
   1. release、tag 必须同名
   2. 使用后缀区分发布的组件 -backend -android -web
   3. previous release 选择同样后缀的 tag，如下面发布 web app 就选择 -web 后缀
      <img width="480" height="374" alt="image" src="https://github.com/user-attachments/assets/22f307a2-eefb-437d-acec-437ccd16ef0f" />
   4. 数字版本号所有组件共享，也就是如果后端发布了 v1.3.1-backend，下一个 android 发布名称为 v1.3.2-android
3. 然后从创建的 tag 启动相应 GitHub Actions 工作流创建新的发布产物（后端服务的 docker 容器镜像、web app 在服务器上的静态文件等等）

## Backend 发布流程

1. [新建 GitHub Release](https://github.com/NascentCore/inty/releases/new) 选择创建新的 tag
   <img width="800" height="996" alt="image" src="https://github.com/user-attachments/assets/cb58a6d5-79cb-4772-8736-814c585bb165" />
2. `-backend` 后缀添加到版本号上，版本号依次递增，每次 backend android 发布都要增加 fix 或者 minor 版本号；
3. [Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
   选择刚刚创建的 tag，环境选择 prod
   <img width="800" height="1210" alt="image" src="https://github.com/user-attachments/assets/3e0fe7de-abf5-4eb8-b81d-ae9f31fa6399" />

## Android app 发布流程

1. 修改代码中的 versionName 到新的版本号，否则会触发版本检查错误，如 https://github.com/NascentCore/inty/commit/0c18b413401dedc48efe9c1bcc67e2ba999065be
   <img width="900" height="400" alt="image" src="https://github.com/user-attachments/assets/186335c0-fc96-4520-b8da-d89f0f892a23" />
2. 在 GitHub 上创建 release（选择创建新的 tag）添加`-android` 后缀
   <img width="900" height="402" alt="image" src="https://github.com/user-attachments/assets/090663da-e86a-4b8f-a8a5-dd98a34f1c9c" />
   <img width="900" height="984" alt="image" src="https://github.com/user-attachments/assets/95438de0-8c3c-4aad-8d12-0591395b8d5e" />
3. 在本地 git checkout 出对应的 tag，构建 release aab（使用 release build type）并确认其 versionName
   <img width="480" height="208" alt="image" src="https://github.com/user-attachments/assets/433d8afe-911f-4494-8e0f-39a666653afc" />
4. 上传内测轨道
   <img width="800" height="1614" alt="image" src="https://github.com/user-attachments/assets/07cc93c6-a573-40d8-98f2-f716fce5826a" />
   编写有价值的更新说明
5. 从 Google Play 商店下载内测版本测试
6. 创建生产环境发布版本，选择前面测试的内测版本
   <img width="800" height="1340" alt="image" src="https://github.com/user-attachments/assets/a3a327d1-70a7-4236-a4b0-02c15283ac49" />
7. 提交审核
8. 审核通过后，正式发布
9. 完成后使用非内测账户检查 Google Play 商店打开 https://play.google.com/store/apps/details?id=com.ai.intellimate 确认版本可见

## Web app 发布流程

1. 与上述相同创建 release
2. 打开 [build_and_deploy_web_app](https://github.com/NascentCore/inty/blob/main/.github/workflows/build_and_deploy_web_app.yml)
3. 选择 tag 及 prod 环境
   <img width="800" height="756" alt="image" src="https://github.com/user-attachments/assets/066e530b-3d1d-402e-a72f-97169178e606" />

