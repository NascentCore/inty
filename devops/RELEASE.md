# 发布流程

需要至少 2 个人参与：1 个人操作、另 1 个人全程审查，查漏补缺；步骤如下：

1. `git tagging`:
   ```bash
   git tag v<major>.<minor>.<fix>
   git push --tags
   ```2. [GitHub 工作流部署发布](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy.yml)
   选择上一步标签、部署环境为prod；
   <img width="3018" height="902" alt="image" src="https://github.com/user-attachments/assets/875add0c-7a99-4d2d-9f08-a7605b825e3b" />
3.完成后打开[足球系统](https://app.inty.cc/evaluation)点击一个角色聊天一条验证初步一起正常、
   然后使用应用程序同样找一个简单的用户验证
4.打开Android Studio构建签名后的aab，并上传到内部测试轨道
5.之后发布简单验证所有功能