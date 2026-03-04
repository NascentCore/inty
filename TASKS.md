# Tasks（明确的任务）

- [x] 设置一个独立的运营平台链接`ops.inty.cc`来替代 `app.inty.cc/evaluation`；目的：1. 分离部署、运维平台可以即时部署 2. 降低风险，避免干扰
  - [x] 更新 DNS ops.inty.cc dev.ops.inty.cc
    
    <img width="800" height="764" alt="image" src="https://github.com/user-attachments/assets/fb728bd4-72c8-414e-aead-6a57b554c7d5" />
  - [x] 更新 nginx 配置来支持新域名
  - [x] 创建独立部署脚本和代码改动：https://github.com/NascentCore/inty/pull/2373
  - [x] 创建独立部署[github 工作流](/.github/workflows/build_and_deploy_ops.yml)
  - [x] 主后端移除 ops 过渡层：`app/api/v1/router.py` 不再挂载 evaluation/festival_memory，删除 re-export 模块 `app/api/v1/endpoints/evaluation.py` 与 `app/api/v1/endpoints/festival_memory.py`，`backend/inty` 不再提供 `/evaluation`。
- [ ] Optimize official assistant's prompts
  - [x] Added a separate build system messages API for official assistant
  - [ ] Integrate the new system messages building API in the agent workflow
  - [ ] Revise the prompt to make the official assistant more helpful in answering user's question on app features
