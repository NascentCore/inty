# 不锈钢 OpenAPI SDK 发电机

总体工作流程：

1.修改 fastapi endpoints 类型定义、增加/删除端点，`app/api/**/*.py` 提交代码到代码库
2. 改动 `app/api/**/*.py`触发
   [更新_openapi_json GitHub 操作](https://github.com/NascentCore/inty/actions/workflows/update_openapi_json.yaml)
   工作流程更新`app/openapi.json`并创建 Pull Request，如 https://github.com/NascentCore/inty/pull/448
3. 创建拉取请求触发器 [Stainless 工作流程](https://github.com/NascentCore/inty/actions/workflows/stainless.yaml)
   发送生成请求到 [stainless project](https://app.stainless.com/inty/inty/overview)
   生成并更新：
   [inty-kotlin](https://github.com/NascentCore/inty-kotlin)
   [inty-打字稿](https://github.com/NascentCore/inty-typescript)
   更新产生的 Pull Request 需要手动合并到代码库，如 https://github.com/NascentCore/inty-kotlin/pull/3
   TODO: 这里不锈钢会启动这3个代码库上的release工作流，但是其中个别工作流会失败（release docker）导致无法自动提交pull request；
   需要手动提交
4.合并前面创建的app/openapi.json的pull request；如：https://github.com/NascentCore/inty/pull/448
5. 更新 inty-kotlin 子模块 [android_app/library/inty_sdk](android_app/library/inty_sdk),
   该模块来自 [inty-kotlin](https://github.com/NascentCore/inty-kotlin)```bash
   cd android_app/library/inty_sdk
   git checkout main
   git pull
   cd ...
   git commit -m "更新 kotlin sdk"
   git push
   ```创建 PR 并合并
6.更新 Android 应用依赖到新的 kotlin sdk 版本`android_app/app/build.gradle.kts`；如：https://github.com/NascentCore/inty/pull/453

## 流程示例

以 https://github.com/NascentCore/inty/pull/630 https://github.com/NascentCore/inty/pull/635 为例：

-首先使用 [generate_openapi_json.py](../scripts/generate_openapi_json.py) 更新 [openapi.json](openapi.json)
- 提交钱包并创建 Pull request，该 PR 会触发不锈钢工作流程，如下图所示：
  <img width="960" height="1210" alt="image" src="https://github.com/user-attachments/assets/5516d301-a067-41e8-84e7-6f1fbfc486e6" />
- 待不锈钢工作流程完成，代码会自动同步到kotlin python typescript代码库，打开链接确认最新的代码已经提交；
  如果没有提交，则需要手动将代码提交
  <img width="960" height="1490" alt="image" src="https://github.com/user-attachments/assets/6e644f75-2b73-4c4c-816f-9941e4d05ac6" />- 更新对应的子模块，生成pull request来进行更新；注意`android_app/library/inty_sdk`
  同时须更新 `android_app/app/build.gradle.kts` 中的 `implementation("com.inty.api:inty-kotlin:0.9.0")`版本号到子模块版本。
  译文：https://github.com/NascentCore/inty/pull/635
  <img width="960" height="522" alt="image" src="https://github.com/user-attachments/assets/cedf19cb-3576-4d37-9024-921ad70cc8a9" />