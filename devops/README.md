# DevOps - 运维（目录索引）

本 README 仅作为 `devops/` 目录的索引与文件概述；具体操作流程请查看相应专题文档。

## 链接

- [prod push worker logs](https://cloudlogging.app.goo.gl/VXHGrai93hqJU3er9)
- [dev push worker logs](https://cloudlogging.app.goo.gl/xhWv88U4bH7v7UNd9)

## 常用文档入口

- 发布流程：`RELEASE.md`
- GCP/线上环境信息：`GCP.md`
- Nginx 配置与更新：`nginx/README.md`
- Google Play 运营操作：`GOOGLE_PLAY.md`
- Android App 运维说明：`ANDROID_APP.md`
- Web 域名/证书/部署：`WEB_APP.md`
- 密钥与加密（SOPS）：`SOPS.md`
- 目录内工具脚本：`validate_configs.py`

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
