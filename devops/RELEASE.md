# 发布流程

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
   
