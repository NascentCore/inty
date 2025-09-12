# Stainless OpenAPI SDK generator

总体工作流程：

1. 修改 fastapi endpoints 类型定义、增加/删除 endpoints，改动 `app/api/**/*.py` 提交代码到代码库
2. 改动 `app/api/**/*.py` 触发
   [update_openapi_json GitHub action](https://github.com/NascentCore/inty/actions/workflows/update_openapi_json.yaml)
   该工作流更新 `app/openapi.json` 并创建 Pull Request，如 https://github.com/NascentCore/inty/pull/448
3. 创建的 Pull Request 触发 [Stainless 工作流](https://github.com/NascentCore/inty/actions/workflows/stainless.yaml)
   发送生成请求到 [stainless project](https://app.stainless.com/inty/inty/overview)
   生成并更新：
   [inty-kotlin](https://github.com/NascentCore/inty-kotlin)
   [inty-python](https://github.com/NascentCore/inty-python)
   [inty-typescript](https://github.com/NascentCore/inty-typescript)
   TODO: 此处 stainless 会启动这 3 个代码库上的 release 工作流，但是其中个别工作流会失败（release docker）导致无法自动提交 pull request；
   需要手动提交
4. 提交 openapi.json 更新的 pull request
5. 更新 inty-kotlin submodule [android_app/library/inty_sdk](android_app/library/inty_sdk),
   该 module 来自 [inty-kotlin](https://github.com/NascentCore/inty-kotlin)
