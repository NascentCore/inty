# 发布流程

* 例行的测试版本发布到内测轨道，不再使用 internal app sharing
* 个别共享仍然可以使用 internal app sharing

## Android app 发布流程

1. 在 GitHub 上创建 release（选择创建新的 tag）
2. 在本地 git checkout 出对应的 tag，构建 aab
3. 上传内测轨道
   <img width="800" height="1614" alt="image" src="https://github.com/user-attachments/assets/07cc93c6-a573-40d8-98f2-f716fce5826a" />
5. 测试
6. 创建生产环境版本，选择前面测试的内测版本
7. 提交审核

需要至少 2 个人参与：1 个人操作、另 1 个人全程审查，查漏补缺；步骤如下：

1. `git tagging`:
   ```bash
   git tag v<major>.<minor>.<fix>
   git push --tags
   ```
2. [GitHub 工作流部署发布后端](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy.yml)
   选择上一步 tag、部署环境为 prod；
   <img width="3018" height="902" alt="image" src="https://github.com/user-attachments/assets/875add0c-7a99-4d2d-9f08-a7605b825e3b" />
3. 完成后打开[评测系统](https://app.inty.cc/evaluation)点击一个角色聊一句初步验证一起正常、
   然后使用 app 同样找一个简单用户验证
4. 打开 Android Studio 构建签名后的 aab，并上传到 Internal Testing track
5. 发布之后简单验证所有功能
   
