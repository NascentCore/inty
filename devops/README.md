# DevOps - 运维（目录索引）

## dev 与 prod 环境

- 共享同一台 gcp VM
- 差别在配置文件：[dev](config.yaml.dev) [prod](config.yaml.prod)
- 操作这两个环境必须先写 python 脚本，严禁直接操作数据库、或者直接调用管理员权限的 API Endpoint，步骤如下（以 dev 为例）：

  ```bash
  ssh <gcp-vm>
  docker exec -it inty-backend-dev bash
  python scripts/<...>.py <flags>
  ```

### dev 环境测试用户

dev 环境预制了 3 个测试用户：

- test1@sxwl.ai sxwl666!
- test2@sxwl.ai sxwl666!
- test3@sxwl.ai sxwl666!

## 链接

- [prod push worker logs](https://cloudlogging.app.goo.gl/VXHGrai93hqJU3er9)
- [dev push worker logs](https://cloudlogging.app.goo.gl/xhWv88U4bH7v7UNd9)
- [prod inty backend logs](https://cloudlogging.app.goo.gl/9fr7rxgrwbas68En9)
- [dev inty backend logs](https://cloudlogging.app.goo.gl/aaPiWvxr7syuAFuX7)
- [LangSmith IntelliMate-dev project](https://smith.langchain.com/o/1463b2d0-5d84-4f0c-b31e-0a158d823e01)
- [LangSmith inty-backend-prod tracing project](https://smith.langchain.com/o/824a4bb5-ca84-4fa2-969e-7a50cd267999/projects/p/2808d56c-e07f-4293-8bec-1cc62d9f4975)
- [Sentry plan overview](https://inty-inc.sentry.io/settings/billing/overview/): 生产环境追踪等 Observability 需求

## 非 .md 文件与子目录概述

- **配置文件**：
  - `config.yaml.dev` / `config.yaml.prod`：部署环境配置（构建期注入进入镜像；具体机制见 `RELEASE.md`）
  - `config.yaml.local`：本地运行配置参考
  - `config.yaml.test`：CI/本地测试配置（工作流会 `cp devops/config.yaml.test config.yaml`）
- **nginx/**：反向代理配置与校验脚本
  - `nginx/nginx.conf`：Nginx 主配置
  - `nginx/conf.d/sxwl.ai.conf`：站点配置
  - `nginx/validate.sh`：配置校验
- **docker/**：运维侧的 Docker 相关材料（如有）

## Notes

同样的提示词，Cursor 搞定了，Copilot 搞不定：
* Copilot 搞不定，引入新的错误：https://github.com/NascentCore/inty/pull/2246
* Cursor 搞定，未引入新的错误：https://github.com/NascentCore/inty/pull/2249

## 参考资料

[Google GenAI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing#modality-based-pricing)
