# 发布流程

* 例行的测试版本发布到内测轨道，不再使用 internal app sharing
* 个别共享仍然可以使用 internal app sharing

## Backend 发布流程

1. GitHub 创建 release（选择创建新的 tag）
   <img width="800" height="996" alt="image" src="https://github.com/user-attachments/assets/cb58a6d5-79cb-4772-8736-814c585bb165" />
2. [Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
   选择刚刚创建的 tag，环境选择 prod
   <img width="800" height="1210" alt="image" src="https://github.com/user-attachments/assets/3e0fe7de-abf5-4eb8-b81d-ae9f31fa6399" />

## Android app 发布流程

1. 在 GitHub 上创建 release（选择创建新的 tag）
2. 在本地 git checkout 出对应的 tag，构建 release aab（使用 release build type）
3. 上传内测轨道
   <img width="800" height="1614" alt="image" src="https://github.com/user-attachments/assets/07cc93c6-a573-40d8-98f2-f716fce5826a" />
5. 从 Google Play 商店下载内测版本测试
6. 创建生产环境发布版本，选择前面测试的内测版本
   <img width="800" height="1340" alt="image" src="https://github.com/user-attachments/assets/a3a327d1-70a7-4236-a4b0-02c15283ac49" />
8. 提交审核
9. 审核通过后，正式发布
10. 完成后使用非内测账户检查 Google Play 商店打开 https://play.google.com/store/apps/details?id=com.ai.intellimate 确认版本可见
