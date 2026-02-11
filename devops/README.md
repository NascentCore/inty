# DevOps - 运维（目录索引）

## 链接

- [prod push worker logs](https://cloudlogging.app.goo.gl/VXHGrai93hqJU3er9)
- [dev push worker logs](https://cloudlogging.app.goo.gl/xhWv88U4bH7v7UNd9)
- [prod inty backend logs](https://cloudlogging.app.goo.gl/9fr7rxgrwbas68En9)
- [dev inty backend logs](https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9)
- [LangSmith IntelliMate-dev project](https://smith.langchain.com/o/1463b2d0-5d84-4f0c-b31e-0a158d823e01)
- [LangSmith inty-backend-prod tracing project](https://smith.langchain.com/o/824a4bb5-ca84-4fa2-969e-7a50cd267999/projects/p/2808d56c-e07f-4293-8bec-1cc62d9f4975)

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

## 参考资料

[Google GenAI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing#modality-based-pricing)
